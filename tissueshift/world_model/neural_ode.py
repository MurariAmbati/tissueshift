"""Neural ODE-based continuous-time disease dynamics.

Models breast cancer progression as a continuous dynamical system in the
latent tissue-state manifold.  Instead of discrete stage transitions the
tissue state evolves via a learned ODE:

    dz/dt = f_θ(z, t)

where *z* is the 128-dim tissue state and *f_θ* is a neural network.
The model supports:

* **Continuous trajectory prediction** — predict tissue state at any
  future timepoint (not only fixed intervals).
* **Irregularly-sampled longitudinal data** — handles patients with
  different biopsy schedules.
* **Phase-portrait analysis** — identify attractor basins (stable
  subtypes), saddle points (transition states), and separatrices.
* **Velocity field visualisation** — colour-coded flow on the UMAP
  manifold.

Implementation uses `torchdiffeq` when available, with a lightweight
Euler/RK4 fallback for environments that cannot install it.

References
----------
Chen et al., "Neural Ordinary Differential Equations", NeurIPS 2018.
Rubanova et al., "Latent ODEs for Irregularly-Sampled Time Series", NeurIPS 2019.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try to import torchdiffeq; fall back to manual integrators
# ---------------------------------------------------------------------------
try:
    from torchdiffeq import odeint, odeint_adjoint

    _HAS_TORCHDIFFEQ = True
except ImportError:
    _HAS_TORCHDIFFEQ = False
    logger.info("torchdiffeq not found — using built-in RK4 integrator.")


# ===================================================================
# Configuration
# ===================================================================

@dataclass
class NeuralODEConfig:
    """Parameters for the continuous dynamics module."""

    latent_dim: int = 128
    hidden_dim: int = 256
    num_layers: int = 3
    time_embed_dim: int = 32
    activation: str = "softplus"  # softplus | silu | tanh
    solver: str = "dopri5"  # dopri5 | rk4 | euler
    rtol: float = 1e-5
    atol: float = 1e-5
    use_adjoint: bool = True  # memory-efficient backprop
    max_num_steps: int = 1000
    regularise_kinetic: bool = True  # penalise ||f(z,t)||²
    kinetic_weight: float = 0.01
    augment_dim: int = 0  # augmented neural ODE (extra dims)
    stiffness_detection: bool = False


# ===================================================================
# Time embedding
# ===================================================================

class ContinuousTimeEmbedding(nn.Module):
    """Sinusoidal + learnable embedding for continuous time values.

    Encodes arbitrary real-valued timestamps (in days) into a dense
    vector suitable for conditioning the ODE dynamics function.
    """

    def __init__(self, dim: int = 32, max_period: float = 3650.0):
        super().__init__()
        self.dim = dim
        half = dim // 2
        # Log-spaced frequencies
        freq = torch.exp(
            -math.log(max_period) * torch.arange(half, dtype=torch.float32) / half
        )
        self.register_buffer("freq", freq)
        self.proj = nn.Linear(dim, dim)

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        """Embed time.  *t* can be scalar or (B,)."""
        if t.dim() == 0:
            t = t.unsqueeze(0)
        # (B, half)
        args = t.unsqueeze(-1) * self.freq.unsqueeze(0)
        emb = torch.cat([torch.sin(args), torch.cos(args)], dim=-1)  # (B, dim)
        return self.proj(emb)


# ===================================================================
# ODE dynamics function
# ===================================================================

class _ODEFunc(nn.Module):
    """Learned vector field f_θ(z, t) defining dz/dt.

    The network is time-conditioned: a time embedding is concatenated
    to the state before each hidden layer.  Using *softplus* activation
    ensures Lipschitz continuity which aids solver stability.
    """

    def __init__(self, cfg: NeuralODEConfig):
        super().__init__()
        self.cfg = cfg
        state_dim = cfg.latent_dim + cfg.augment_dim
        self.time_embed = ContinuousTimeEmbedding(cfg.time_embed_dim)

        act_cls = {
            "softplus": nn.Softplus,
            "silu": nn.SiLU,
            "tanh": nn.Tanh,
        }.get(cfg.activation, nn.Softplus)

        layers: list[nn.Module] = []
        in_dim = state_dim + cfg.time_embed_dim
        for i in range(cfg.num_layers):
            out_dim = cfg.hidden_dim if i < cfg.num_layers - 1 else state_dim
            layers.append(nn.Linear(in_dim, out_dim))
            if i < cfg.num_layers - 1:
                layers.append(act_cls())
                layers.append(nn.LayerNorm(out_dim))
            in_dim = out_dim + cfg.time_embed_dim  # re-inject time at each layer

        # Store layers individually so we can re-inject time
        self.linears = nn.ModuleList(
            [l for l in layers if isinstance(l, nn.Linear)]
        )
        self.norms = nn.ModuleList(
            [l for l in layers if isinstance(l, nn.LayerNorm)]
        )
        self.act = act_cls()

        self._nfe = 0  # number of function evaluations (for diagnostics)

    def forward(self, t: torch.Tensor, z: torch.Tensor) -> torch.Tensor:
        """Compute dz/dt.

        Parameters
        ----------
        t : scalar tensor — current time
        z : (B, state_dim) — current state
        """
        self._nfe += 1
        t_emb = self.time_embed(t.expand(z.shape[0]))  # (B, time_embed_dim)

        h = z
        norm_idx = 0
        for i, lin in enumerate(self.linears):
            h_in = torch.cat([h, t_emb], dim=-1)
            h = lin(h_in)
            if i < len(self.linears) - 1:
                h = self.norms[norm_idx](h)
                norm_idx += 1
                h = self.act(h)
        return h

    @property
    def nfe(self) -> int:
        return self._nfe

    def reset_nfe(self) -> None:
        self._nfe = 0


# ===================================================================
# Built-in integrators (fallback)
# ===================================================================

def _euler_step(
    func: nn.Module, z: torch.Tensor, t: torch.Tensor, dt: torch.Tensor
) -> torch.Tensor:
    return z + dt * func(t, z)


def _rk4_step(
    func: nn.Module, z: torch.Tensor, t: torch.Tensor, dt: torch.Tensor
) -> torch.Tensor:
    k1 = func(t, z)
    k2 = func(t + 0.5 * dt, z + 0.5 * dt * k1)
    k3 = func(t + 0.5 * dt, z + 0.5 * dt * k2)
    k4 = func(t + dt, z + dt * k3)
    return z + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)


def _builtin_odeint(
    func: nn.Module,
    z0: torch.Tensor,
    t_span: torch.Tensor,
    method: str = "rk4",
) -> torch.Tensor:
    """Integrate over *t_span* using fixed-step RK4 or Euler.

    Returns (T, B, D) tensor of states at each time in *t_span*.
    """
    step_fn = _rk4_step if method == "rk4" else _euler_step
    states = [z0]
    z = z0
    for i in range(len(t_span) - 1):
        dt = t_span[i + 1] - t_span[i]
        # Sub-step for stability when dt is large
        n_sub = max(1, int(torch.abs(dt).item() / 1.0))
        sub_dt = dt / n_sub
        for s in range(n_sub):
            t_cur = t_span[i] + s * sub_dt
            z = step_fn(func, z, t_cur, sub_dt)
        states.append(z)
    return torch.stack(states, dim=0)  # (T, B, D)


# ===================================================================
# Main module
# ===================================================================

class NeuralODEDynamics(nn.Module):
    """Continuous-time tissue-state dynamics via Neural ODE.

    Given an initial tissue state *z₀* and a set of target timepoints,
    this module integrates the learned vector field to produce predicted
    states at each timepoint.

    Usage
    -----
    >>> dynamics = NeuralODEDynamics(NeuralODEConfig())
    >>> z_traj = dynamics(z0, t_eval=torch.tensor([0., 90., 365., 730.]))
    >>> z_traj.shape  # (4, B, 128)
    """

    def __init__(self, cfg: NeuralODEConfig):
        super().__init__()
        self.cfg = cfg
        self.odefunc = _ODEFunc(cfg)

        # Optional state augmentation (ANODEs)
        if cfg.augment_dim > 0:
            self.augment_proj = nn.Linear(cfg.latent_dim, cfg.latent_dim + cfg.augment_dim)
            self.deaugment_proj = nn.Linear(cfg.latent_dim + cfg.augment_dim, cfg.latent_dim)
        else:
            self.augment_proj = None
            self.deaugment_proj = None

    def forward(
        self,
        z0: torch.Tensor,
        t_eval: torch.Tensor,
    ) -> torch.Tensor:
        """Integrate from *z0* to each time in *t_eval*.

        Parameters
        ----------
        z0 : (B, latent_dim)
        t_eval : (T,) — sorted timepoints (days). First element is
            typically 0 (the observation time).

        Returns
        -------
        z_traj : (T, B, latent_dim) — predicted states
        """
        # Augment
        if self.augment_proj is not None:
            z0 = self.augment_proj(z0)

        self.odefunc.reset_nfe()

        if _HAS_TORCHDIFFEQ:
            integrate = odeint_adjoint if self.cfg.use_adjoint else odeint
            z_traj = integrate(
                self.odefunc,
                z0,
                t_eval,
                method=self.cfg.solver if self.cfg.solver != "euler" else "euler",
                rtol=self.cfg.rtol,
                atol=self.cfg.atol,
                options={"max_num_steps": self.cfg.max_num_steps},
            )
        else:
            method = "rk4" if self.cfg.solver in ("dopri5", "rk4") else "euler"
            z_traj = _builtin_odeint(self.odefunc, z0, t_eval, method=method)

        # De-augment
        if self.deaugment_proj is not None:
            T, B, D = z_traj.shape
            z_traj = self.deaugment_proj(z_traj.reshape(T * B, D)).reshape(T, B, -1)

        return z_traj

    def kinetic_energy(
        self, z0: torch.Tensor, t_eval: torch.Tensor
    ) -> torch.Tensor:
        """Compute ∫||f(z,t)||² dt as a regulariser.

        Approximated via trapezoidal rule at *t_eval* points.
        """
        z_traj = self.forward(z0, t_eval)
        energies = []
        for i in range(len(t_eval)):
            dz = self.odefunc(t_eval[i], z_traj[i])
            energies.append((dz ** 2).sum(dim=-1))  # (B,)
        energies = torch.stack(energies, dim=0)  # (T, B)
        # Trapezoidal integration
        dt = t_eval[1:] - t_eval[:-1]
        integ = 0.5 * (energies[:-1] + energies[1:]) * dt.unsqueeze(-1)
        return integ.sum(dim=0).mean()  # scalar

    @property
    def nfe(self) -> int:
        """Number of function evaluations in last solve."""
        return self.odefunc.nfe


# ===================================================================
# Phase portrait analysis
# ===================================================================

class PhasePortraitAnalyser:
    """Analyse the learned vector field for attractor structure.

    Identifies:
    * **Fixed points** — tissue states where dz/dt ≈ 0 (stable subtypes).
    * **Velocity magnitude** — speed of evolution at any point.
    * **Jacobian spectrum** — local stability via eigenvalues.
    * **Basins of attraction** — which initial states converge to which
      fixed points.
    """

    def __init__(self, dynamics: NeuralODEDynamics, device: str = "cpu"):
        self.dynamics = dynamics.to(device)
        self.device = device

    @torch.no_grad()
    def velocity_field(
        self,
        grid_points: torch.Tensor,
        t: float = 0.0,
    ) -> torch.Tensor:
        """Compute dz/dt at each point in *grid_points*.

        Parameters
        ----------
        grid_points : (N, latent_dim)
        t : evaluation time

        Returns
        -------
        velocities : (N, latent_dim)
        """
        grid_points = grid_points.to(self.device)
        t_tensor = torch.tensor(t, device=self.device)
        return self.dynamics.odefunc(t_tensor, grid_points)

    @torch.no_grad()
    def velocity_magnitude(
        self, grid_points: torch.Tensor, t: float = 0.0
    ) -> torch.Tensor:
        """||dz/dt|| at each point."""
        v = self.velocity_field(grid_points, t)
        return v.norm(dim=-1)

    @torch.no_grad()
    def find_fixed_points(
        self,
        initial_guesses: torch.Tensor,
        n_iters: int = 500,
        lr: float = 0.01,
        tol: float = 1e-6,
        t: float = 0.0,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Find fixed points by minimising ||f(z,t)||².

        Parameters
        ----------
        initial_guesses : (K, latent_dim)

        Returns
        -------
        fixed_points : (K, latent_dim)
        residuals : (K,) — ||f(z*,t)|| for each point
        """
        z = initial_guesses.clone().to(self.device).requires_grad_(True)
        t_tensor = torch.tensor(t, device=self.device)
        opt = torch.optim.Adam([z], lr=lr)

        for _ in range(n_iters):
            opt.zero_grad()
            dz = self.dynamics.odefunc(t_tensor, z)
            loss = (dz ** 2).sum(dim=-1).mean()
            loss.backward()
            opt.step()

            if loss.item() < tol:
                break

        with torch.no_grad():
            dz_final = self.dynamics.odefunc(t_tensor, z)
            residuals = dz_final.norm(dim=-1)

        return z.detach(), residuals.detach()

    def jacobian_at(
        self, z: torch.Tensor, t: float = 0.0
    ) -> torch.Tensor:
        """Compute the Jacobian ∂f/∂z at a single point.

        Parameters
        ----------
        z : (latent_dim,) — single point

        Returns
        -------
        J : (latent_dim, latent_dim)
        """
        z = z.to(self.device).requires_grad_(True)
        t_tensor = torch.tensor(t, device=self.device)

        def func(z_in: torch.Tensor) -> torch.Tensor:
            return self.dynamics.odefunc(t_tensor, z_in.unsqueeze(0)).squeeze(0)

        J = torch.autograd.functional.jacobian(func, z)
        return J

    def stability_at(
        self, z: torch.Tensor, t: float = 0.0
    ) -> Dict[str, Any]:
        """Characterise local stability via Jacobian eigenvalues.

        Returns
        -------
        dict with:
            eigenvalues : complex (D,)
            max_real : float — largest real part
            is_stable : bool — True if all real parts < 0
            spectral_radius : float
        """
        J = self.jacobian_at(z, t)
        eigvals = torch.linalg.eigvals(J)
        real_parts = eigvals.real
        return {
            "eigenvalues": eigvals.cpu().numpy(),
            "max_real": real_parts.max().item(),
            "is_stable": bool((real_parts < 0).all()),
            "spectral_radius": eigvals.abs().max().item(),
        }

    @torch.no_grad()
    def basin_assignment(
        self,
        initial_points: torch.Tensor,
        fixed_points: torch.Tensor,
        integration_time: float = 3650.0,
        n_steps: int = 100,
    ) -> torch.Tensor:
        """Assign each point to its nearest fixed-point attractor.

        Integrates each point forward in time and finds the closest
        fixed point to the final state.

        Returns
        -------
        assignments : (N,) — index into *fixed_points*
        """
        t_eval = torch.linspace(0, integration_time, n_steps, device=self.device)
        z_traj = self.dynamics(initial_points.to(self.device), t_eval)
        z_final = z_traj[-1]  # (N, D)
        # Pairwise distances to fixed points
        dists = torch.cdist(z_final, fixed_points.to(self.device))  # (N, K)
        return dists.argmin(dim=-1).cpu()


# ===================================================================
# Longitudinal likelihood (for training with irregularly-sampled data)
# ===================================================================

class LongitudinalODELoss(nn.Module):
    """Loss for irregularly-sampled longitudinal observations.

    Given a patient trajectory {(tᵢ, zᵢ)} with arbitrary timestamps,
    computes the negative log-likelihood by integrating from t₀ and
    comparing predicted z(tᵢ) with observed zᵢ at each timepoint.

    Also includes optional kinetic regularisation and KL divergence
    for the variational initial state.
    """

    def __init__(
        self,
        dynamics: NeuralODEDynamics,
        reconstruction_weight: float = 1.0,
        kinetic_weight: float = 0.01,
        kl_weight: float = 0.001,
    ):
        super().__init__()
        self.dynamics = dynamics
        self.recon_w = reconstruction_weight
        self.kinetic_w = kinetic_weight
        self.kl_w = kl_weight

    def forward(
        self,
        z_observed: torch.Tensor,
        t_observed: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        mu: Optional[torch.Tensor] = None,
        logvar: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """Compute longitudinal loss.

        Parameters
        ----------
        z_observed : (B, T, D) — observed tissue states at each timepoint
        t_observed : (T,) — timepoints (shared across batch, sorted)
        mask : (B, T) — binary mask for observed timepoints (1 = observed)
        mu, logvar : (B, D) — variational parameters for initial state

        Returns
        -------
        Dict with: total, reconstruction, kinetic, kl
        """
        B, T, D = z_observed.shape
        z0 = z_observed[:, 0]

        # Integrate
        z_pred = self.dynamics(z0, t_observed)  # (T, B, D)
        z_pred = z_pred.permute(1, 0, 2)  # (B, T, D)

        # Reconstruction
        diff = (z_pred - z_observed) ** 2  # (B, T, D)
        if mask is not None:
            diff = diff * mask.unsqueeze(-1)
            n_obs = mask.sum() * D
        else:
            n_obs = B * T * D
        recon_loss = diff.sum() / max(n_obs, 1)

        # Kinetic regularisation
        kin_loss = torch.tensor(0.0, device=z0.device)
        if self.kinetic_w > 0:
            kin_loss = self.dynamics.kinetic_energy(z0, t_observed)

        # KL divergence for variational initial state
        kl_loss = torch.tensor(0.0, device=z0.device)
        if mu is not None and logvar is not None:
            kl_loss = -0.5 * (1 + logvar - mu.pow(2) - logvar.exp()).sum(dim=-1).mean()

        total = (
            self.recon_w * recon_loss
            + self.kinetic_w * kin_loss
            + self.kl_w * kl_loss
        )

        return {
            "total": total,
            "reconstruction": recon_loss,
            "kinetic": kin_loss,
            "kl": kl_loss,
        }


# ===================================================================
# Trajectory sampler (for clinical predictions)
# ===================================================================

class TrajectorySampler:
    """Sample plausible future trajectories for a patient.

    Uses Monte Carlo dropout or variational initial states to generate
    an ensemble of trajectories, providing uncertainty estimates over
    time.
    """

    def __init__(
        self,
        dynamics: NeuralODEDynamics,
        tissue_state_model: Optional[nn.Module] = None,
        device: str = "cpu",
    ):
        self.dynamics = dynamics.to(device)
        self.tissue_model = tissue_state_model
        self.device = device

    @torch.no_grad()
    def sample_trajectories(
        self,
        z0_mu: torch.Tensor,
        z0_logvar: Optional[torch.Tensor],
        t_eval: torch.Tensor,
        n_samples: int = 50,
    ) -> Dict[str, torch.Tensor]:
        """Sample *n_samples* forward trajectories.

        Parameters
        ----------
        z0_mu : (D,) or (B, D) — mean initial state
        z0_logvar : (D,) or (B, D) — log-variance (for stochastic starts)
        t_eval : (T,) — evaluation times
        n_samples : number of trajectory samples

        Returns
        -------
        Dict with:
            trajectories : (n_samples, T, D)
            mean : (T, D) — mean trajectory
            std : (T, D) — std across samples
            percentile_5 : (T, D)
            percentile_95 : (T, D)
        """
        if z0_mu.dim() == 1:
            z0_mu = z0_mu.unsqueeze(0)
        if z0_logvar is not None and z0_logvar.dim() == 1:
            z0_logvar = z0_logvar.unsqueeze(0)

        z0_mu = z0_mu.to(self.device)
        t_eval = t_eval.to(self.device)

        all_traj = []
        for _ in range(n_samples):
            if z0_logvar is not None:
                z0_logvar_d = z0_logvar.to(self.device)
                std = (0.5 * z0_logvar_d).exp()
                z0 = z0_mu + std * torch.randn_like(std)
            else:
                z0 = z0_mu

            traj = self.dynamics(z0, t_eval)  # (T, 1, D)
            all_traj.append(traj.squeeze(1))  # (T, D)

        trajs = torch.stack(all_traj, dim=0)  # (S, T, D)

        return {
            "trajectories": trajs.cpu(),
            "mean": trajs.mean(dim=0).cpu(),
            "std": trajs.std(dim=0).cpu(),
            "percentile_5": trajs.quantile(0.05, dim=0).cpu(),
            "percentile_95": trajs.quantile(0.95, dim=0).cpu(),
        }

    @torch.no_grad()
    def expected_subtype_evolution(
        self,
        z0_mu: torch.Tensor,
        z0_logvar: Optional[torch.Tensor],
        t_eval: torch.Tensor,
        subtype_head: nn.Module,
        n_samples: int = 50,
    ) -> Dict[str, np.ndarray]:
        """Predict how subtype probabilities evolve over time.

        Returns
        -------
        Dict with:
            times : (T,) numpy
            mean_probs : (T, C) mean subtype probabilities
            std_probs : (T, C) std of probabilities
            entropy : (T,) mean predictive entropy over time
        """
        result = self.sample_trajectories(z0_mu, z0_logvar, t_eval, n_samples)
        trajs = result["trajectories"].to(self.device)  # (S, T, D)
        S, T, D = trajs.shape

        all_probs = []
        subtype_head = subtype_head.to(self.device).eval()
        for s in range(S):
            out = subtype_head(trajs[s])  # expects (T, D)
            probs = out.get("pam50_probs", out.get("lattice_probs"))
            all_probs.append(probs.cpu())

        probs_stack = torch.stack(all_probs, dim=0)  # (S, T, C)

        mean_p = probs_stack.mean(dim=0).numpy()  # (T, C)
        std_p = probs_stack.std(dim=0).numpy()

        # Predictive entropy
        eps = 1e-10
        entropy = -(mean_p * np.log(mean_p + eps)).sum(axis=-1)  # (T,)

        return {
            "times": t_eval.cpu().numpy(),
            "mean_probs": mean_p,
            "std_probs": std_p,
            "entropy": entropy,
        }
