"""Causal inference engine for treatment effect estimation.

Goes beyond correlative prediction to ask *causal* questions:

* **What would happen if** this patient received chemotherapy?
* **How much does** HER2-targeted therapy change the transition prob?
* **Which patients benefit most** from a given intervention?

Provides four complementary estimators:

1. **Inverse Probability Weighting (IPW)** — re-weights observed
   outcomes by the propensity score to remove confounding.
2. **Doubly-Robust (DR) / AIPW** — combines outcome regression with
   IPW; consistent if *either* model is correct.
3. **Conditional Average Treatment Effect (CATE)** — heterogeneous
   effect estimation via T-learner, S-learner, or DR-learner.
4. **Counterfactual Trajectory Simulation** — integrates with the
   Neural ODE dynamics to simulate "what-if" disease trajectories
   under hypothetical treatment regimens.

All estimators operate on the learned tissue-state manifold, enabling
causal reasoning at the latent biological level rather than on raw
features.

References
----------
Rubin, "Estimating causal effects of treatments", JASA 1974.
Robins et al., "Estimation of regression coefficients ...", JASA 1994.
Künzel et al., "Metalearners for CATE estimation", PNAS 2019.
Bica et al., "Estimating counterfactual treatment outcomes over time", NeurIPS 2020.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ===================================================================
# Configuration
# ===================================================================

@dataclass
class CausalConfig:
    """Parameters for the causal inference engine."""

    # Treatment definitions
    treatment_names: Tuple[str, ...] = (
        "endocrine_therapy",
        "chemotherapy",
        "anti_her2",
        "cdk4_6_inhibitor",
        "immunotherapy",
    )

    # Propensity model
    propensity_hidden_dim: int = 128
    propensity_num_layers: int = 3
    propensity_dropout: float = 0.2
    propensity_clip: float = 0.01  # clip P(T|X) away from 0/1

    # Outcome model
    outcome_hidden_dim: int = 256
    outcome_num_layers: int = 3

    # CATE estimation
    cate_method: str = "dr_learner"  # t_learner | s_learner | dr_learner

    # Sensitivity analysis
    sensitivity_gamma_range: Tuple[float, ...] = (1.0, 1.5, 2.0, 3.0)


# ===================================================================
# Propensity Score Model
# ===================================================================

class PropensityNetwork(nn.Module):
    """Estimates P(T=1 | X) — the probability of receiving treatment
    given the tissue state (confounders).

    Used to remove **selection bias**: sicker patients are more likely
    to receive aggressive therapy, so naïve comparisons are biased.
    """

    def __init__(self, input_dim: int, num_treatments: int, cfg: CausalConfig):
        super().__init__()
        layers: list[nn.Module] = []
        in_d = input_dim
        for _ in range(cfg.propensity_num_layers - 1):
            layers += [
                nn.Linear(in_d, cfg.propensity_hidden_dim),
                nn.SiLU(),
                nn.LayerNorm(cfg.propensity_hidden_dim),
                nn.Dropout(cfg.propensity_dropout),
            ]
            in_d = cfg.propensity_hidden_dim
        layers.append(nn.Linear(in_d, num_treatments))
        self.net = nn.Sequential(*layers)
        self.clip = cfg.propensity_clip

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Returns P(T=1|X) for each treatment, clipped to (clip, 1-clip)."""
        logits = self.net(x)
        probs = torch.sigmoid(logits)
        return probs.clamp(self.clip, 1.0 - self.clip)


# ===================================================================
# Outcome Models
# ===================================================================

class OutcomeNetwork(nn.Module):
    """Predicts potential outcomes E[Y | X, T].

    Separate heads per treatment arm allow different outcome surfaces,
    important when treatment effects are heterogeneous.
    """

    def __init__(
        self,
        input_dim: int,
        num_treatments: int,
        output_dim: int = 1,
        cfg: CausalConfig = CausalConfig(),
    ):
        super().__init__()
        self.num_treatments = num_treatments
        self.output_dim = output_dim

        # Shared representation
        self.shared = nn.Sequential(
            nn.Linear(input_dim + num_treatments, cfg.outcome_hidden_dim),
            nn.SiLU(),
            nn.LayerNorm(cfg.outcome_hidden_dim),
        )

        # Per-treatment heads (T-learner style within a single network)
        self.heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(cfg.outcome_hidden_dim, cfg.outcome_hidden_dim // 2),
                nn.SiLU(),
                nn.Linear(cfg.outcome_hidden_dim // 2, output_dim),
            )
            for _ in range(num_treatments)
        ])

    def forward(
        self,
        x: torch.Tensor,
        treatment: torch.Tensor,
    ) -> torch.Tensor:
        """Predict outcome under the given treatment.

        Parameters
        ----------
        x : (B, input_dim) — tissue state / covariates
        treatment : (B, num_treatments) — binary treatment indicators

        Returns
        -------
        y_hat : (B, output_dim)
        """
        h = self.shared(torch.cat([x, treatment], dim=-1))
        # Weighted sum of treatment-specific outputs
        y = torch.zeros(x.shape[0], self.output_dim, device=x.device)
        for t in range(self.num_treatments):
            mask = treatment[:, t].unsqueeze(-1)  # (B, 1)
            y = y + mask * self.heads[t](h)
        return y

    def predict_potential_outcomes(
        self, x: torch.Tensor
    ) -> torch.Tensor:
        """Predict Y(t) for ALL treatment arms.

        Returns
        -------
        potential : (B, num_treatments, output_dim)
        """
        results = []
        for t in range(self.num_treatments):
            t_vec = torch.zeros(x.shape[0], self.num_treatments, device=x.device)
            t_vec[:, t] = 1.0
            y_t = self.forward(x, t_vec)
            results.append(y_t)
        return torch.stack(results, dim=1)


# ===================================================================
# Causal Estimators
# ===================================================================

class IPWEstimator:
    """Inverse Probability Weighting estimator for ATE.

    ATE = (1/n) Σ [ T·Y/e(X) − (1−T)·Y/(1−e(X)) ]

    where e(X) = P(T=1|X) is the propensity score.
    """

    @staticmethod
    def estimate_ate(
        outcomes: np.ndarray,
        treatments: np.ndarray,
        propensity_scores: np.ndarray,
        clip: float = 0.01,
    ) -> Dict[str, float]:
        """Estimate Average Treatment Effect via IPW.

        Parameters
        ----------
        outcomes : (N,) — observed outcomes
        treatments : (N,) — binary treatment (0/1)
        propensity_scores : (N,) — P(T=1|X)

        Returns
        -------
        Dict with ate, ate_treated, ate_control, std
        """
        ps = np.clip(propensity_scores, clip, 1 - clip)
        t = treatments.astype(float)
        y = outcomes.astype(float)

        # IPW estimator
        y1_ipw = (t * y / ps).mean()
        y0_ipw = ((1 - t) * y / (1 - ps)).mean()
        ate = y1_ipw - y0_ipw

        # Standard error via influence function
        phi = t * y / ps - (1 - t) * y / (1 - ps) - ate
        se = float(np.std(phi) / np.sqrt(len(y)))

        return {
            "ate": float(ate),
            "ate_se": se,
            "e_y1": float(y1_ipw),
            "e_y0": float(y0_ipw),
        }


class DoublyRobustEstimator:
    """Augmented IPW (AIPW / Doubly-Robust) estimator.

    DR = (1/n) Σ [ μ₁(X) − μ₀(X)
                   + T·(Y−μ₁(X))/e(X)
                   − (1−T)·(Y−μ₀(X))/(1−e(X)) ]

    Consistent if *either* the propensity model or the outcome model
    is correctly specified.
    """

    @staticmethod
    def estimate_ate(
        outcomes: np.ndarray,
        treatments: np.ndarray,
        propensity_scores: np.ndarray,
        mu_1: np.ndarray,
        mu_0: np.ndarray,
        clip: float = 0.01,
    ) -> Dict[str, float]:
        """Estimate ATE via doubly-robust estimator.

        Parameters
        ----------
        mu_1 : (N,) — predicted outcome under treatment
        mu_0 : (N,) — predicted outcome under control
        """
        ps = np.clip(propensity_scores, clip, 1 - clip)
        t = treatments.astype(float)
        y = outcomes.astype(float)

        dr_1 = mu_1 + t * (y - mu_1) / ps
        dr_0 = mu_0 + (1 - t) * (y - mu_0) / (1 - ps)

        ate = float((dr_1 - dr_0).mean())
        phi = dr_1 - dr_0 - ate
        se = float(np.std(phi) / np.sqrt(len(y)))

        return {
            "ate": ate,
            "ate_se": se,
            "e_y1_dr": float(dr_1.mean()),
            "e_y0_dr": float(dr_0.mean()),
        }


class CATEEstimator:
    """Conditional Average Treatment Effect (CATE) estimation.

    Supports three meta-learner strategies:

    * **T-learner**: fit separate models μ₀(X), μ₁(X), CATE = μ₁ − μ₀
    * **S-learner**: single model μ(X, T), CATE = μ(X,1) − μ(X,0)
    * **DR-learner**: augment pseudo-outcomes with DR scores
    """

    def __init__(self, cfg: CausalConfig = CausalConfig()):
        self.method = cfg.cate_method

    def estimate_cate(
        self,
        tissue_states: np.ndarray,
        treatments: np.ndarray,
        outcomes: np.ndarray,
        propensity_scores: Optional[np.ndarray] = None,
        mu_1: Optional[np.ndarray] = None,
        mu_0: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Estimate individual-level treatment effects.

        Parameters
        ----------
        tissue_states : (N, D) — latent tissue states
        treatments : (N,) — binary treatment indicator
        outcomes : (N,) — observed outcomes

        Returns
        -------
        cate : (N,) — estimated individual treatment effects
        """
        if self.method == "t_learner":
            return self._t_learner(tissue_states, treatments, outcomes)
        elif self.method == "s_learner":
            return self._s_learner(tissue_states, treatments, outcomes)
        elif self.method == "dr_learner":
            return self._dr_learner(
                tissue_states, treatments, outcomes,
                propensity_scores, mu_1, mu_0,
            )
        raise ValueError(f"Unknown CATE method: {self.method}")

    def _t_learner(
        self, X: np.ndarray, T: np.ndarray, Y: np.ndarray
    ) -> np.ndarray:
        """T-learner: separate models for treated/control."""
        from sklearn.ensemble import GradientBoostingRegressor

        mask1 = T == 1
        mask0 = T == 0

        model1 = GradientBoostingRegressor(n_estimators=100, max_depth=4)
        model0 = GradientBoostingRegressor(n_estimators=100, max_depth=4)

        model1.fit(X[mask1], Y[mask1])
        model0.fit(X[mask0], Y[mask0])

        return model1.predict(X) - model0.predict(X)

    def _s_learner(
        self, X: np.ndarray, T: np.ndarray, Y: np.ndarray
    ) -> np.ndarray:
        """S-learner: single model with treatment as feature."""
        from sklearn.ensemble import GradientBoostingRegressor

        X_aug = np.column_stack([X, T])
        model = GradientBoostingRegressor(n_estimators=100, max_depth=4)
        model.fit(X_aug, Y)

        X_1 = np.column_stack([X, np.ones(len(X))])
        X_0 = np.column_stack([X, np.zeros(len(X))])
        return model.predict(X_1) - model.predict(X_0)

    def _dr_learner(
        self,
        X: np.ndarray,
        T: np.ndarray,
        Y: np.ndarray,
        ps: Optional[np.ndarray],
        mu_1: Optional[np.ndarray],
        mu_0: Optional[np.ndarray],
    ) -> np.ndarray:
        """DR-learner: fit CATE on doubly-robust pseudo-outcomes."""
        from sklearn.ensemble import GradientBoostingRegressor

        if ps is None or mu_1 is None or mu_0 is None:
            logger.warning("DR-learner requires propensity and outcome models; falling back to T-learner.")
            return self._t_learner(X, T, Y)

        ps_clip = np.clip(ps, 0.01, 0.99)
        # Construct DR pseudo-outcomes
        pseudo = (
            mu_1 - mu_0
            + T * (Y - mu_1) / ps_clip
            - (1 - T) * (Y - mu_0) / (1 - ps_clip)
        )

        model = GradientBoostingRegressor(n_estimators=200, max_depth=5)
        model.fit(X, pseudo)
        return model.predict(X)


# ===================================================================
# Sensitivity Analysis (Rosenbaum Bounds)
# ===================================================================

class RosenbaumSensitivity:
    """Rosenbaum bounds for un-measured confounding.

    Asks: "How strong would an unmeasured confounder have to be to
    explain away the observed treatment effect?"

    Γ = 1 means no hidden bias; Γ = 2 means a confounder that doubles
    the odds of treatment.
    """

    @staticmethod
    def compute_bounds(
        outcomes: np.ndarray,
        treatments: np.ndarray,
        gamma_values: Sequence = (1.0, 1.5, 2.0, 3.0),
    ) -> List[Dict[str, Any]]:
        """Compute Rosenbaum bounds for a range of Γ values.

        Parameters
        ----------
        outcomes : (N,) — observed binary outcomes
        treatments : (N,) — binary treatment (0/1)
        gamma_values : sequence of Γ values to test

        Returns
        -------
        list of dicts with {gamma, p_upper, p_lower, conclusion}
        """
        from scipy import stats

        treated = outcomes[treatments == 1]
        control = outcomes[treatments == 0]
        n_t, n_c = len(treated), len(control)

        results = []
        for gamma in gamma_values:
            # Wilcoxon rank-sum test with sensitivity parameter
            U_obs, _ = stats.mannwhitneyu(treated, control, alternative="two-sided")

            # Under Γ sensitivity, the p-value bounds shift
            mu = n_t * n_c / 2
            sigma = np.sqrt(n_t * n_c * (n_t + n_c + 1) / 12)

            # Upper and lower p-values
            z_upper = (U_obs - mu * gamma / (1 + gamma)) / (sigma * np.sqrt(gamma / (1 + gamma)))
            z_lower = (U_obs - mu / (1 + gamma)) / (sigma * np.sqrt(gamma / (1 + gamma)))

            p_upper = float(2 * stats.norm.sf(abs(z_upper)))
            p_lower = float(2 * stats.norm.sf(abs(z_lower)))

            results.append({
                "gamma": gamma,
                "p_upper": p_upper,
                "p_lower": p_lower,
                "robust": p_upper < 0.05,
            })

        return results


# ===================================================================
# Counterfactual Trajectory Simulation
# ===================================================================

class CounterfactualSimulator:
    """Simulate counter-factual disease trajectories.

    Given a patient's current tissue state, simulates "what-if"
    evolution under different treatment regimens using the Neural ODE
    dynamics model + a treatment effect modifier.

    This enables clinicians to visualise:
    * Expected trajectory *with* treatment
    * Expected trajectory *without* treatment
    * Trajectory under an alternative treatment
    """

    def __init__(
        self,
        dynamics_model: nn.Module,
        treatment_modifier: Optional[nn.Module] = None,
        device: str = "cpu",
    ):
        self.dynamics = dynamics_model.to(device)
        self.modifier = treatment_modifier
        self.device = device

    @torch.no_grad()
    def simulate(
        self,
        z0: torch.Tensor,
        t_eval: torch.Tensor,
        treatment_vec: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Simulate a trajectory with an optional treatment modifier.

        Parameters
        ----------
        z0 : (D,) or (1, D) — initial tissue state
        t_eval : (T,) — evaluation timepoints (days)
        treatment_vec : (num_treatments,) — binary treatment indicator

        Returns
        -------
        trajectory : (T, D)
        """
        if z0.dim() == 1:
            z0 = z0.unsqueeze(0)
        z0 = z0.to(self.device)
        t_eval = t_eval.to(self.device)

        # Apply treatment modifier to alter initial state
        if self.modifier is not None and treatment_vec is not None:
            tv = treatment_vec.to(self.device).unsqueeze(0)
            z0 = z0 + self.modifier(torch.cat([z0, tv], dim=-1))

        traj = self.dynamics(z0, t_eval)  # (T, 1, D)
        return traj.squeeze(1)  # (T, D)

    @torch.no_grad()
    def compare_treatments(
        self,
        z0: torch.Tensor,
        t_eval: torch.Tensor,
        treatment_options: Dict[str, torch.Tensor],
    ) -> Dict[str, torch.Tensor]:
        """Compare trajectories under multiple treatment arms.

        Parameters
        ----------
        treatment_options : mapping of treatment_name → treatment_vec

        Returns
        -------
        Dict mapping treatment_name → (T, D) trajectory
        """
        result = {}
        # Baseline (no treatment)
        result["no_treatment"] = self.simulate(z0, t_eval, treatment_vec=None)

        for name, t_vec in treatment_options.items():
            result[name] = self.simulate(z0, t_eval, treatment_vec=t_vec)

        return result

    @torch.no_grad()
    def individual_treatment_effect(
        self,
        z0: torch.Tensor,
        t_eval: torch.Tensor,
        treatment_vec: torch.Tensor,
        subtype_head: Optional[nn.Module] = None,
    ) -> Dict[str, Any]:
        """Compute ITE = Y(1) − Y(0) at all timepoints.

        Returns latent-space ITE, and optionally subtype probability
        shifts as a clinically meaningful summary.
        """
        traj_treated = self.simulate(z0, t_eval, treatment_vec=treatment_vec)
        traj_control = self.simulate(z0, t_eval, treatment_vec=None)

        ite_latent = traj_treated - traj_control  # (T, D)
        result: Dict[str, Any] = {
            "times": t_eval.cpu().numpy(),
            "trajectory_treated": traj_treated.cpu(),
            "trajectory_control": traj_control.cpu(),
            "ite_latent_norm": ite_latent.norm(dim=-1).cpu().numpy(),
        }

        if subtype_head is not None:
            subtype_head = subtype_head.to(self.device).eval()
            out_t = subtype_head(traj_treated)
            out_c = subtype_head(traj_control)
            prob_key = "pam50_probs" if "pam50_probs" in out_t else "lattice_probs"
            result["subtype_probs_treated"] = out_t[prob_key].cpu().numpy()
            result["subtype_probs_control"] = out_c[prob_key].cpu().numpy()
            result["subtype_prob_shift"] = (
                out_t[prob_key] - out_c[prob_key]
            ).cpu().numpy()

        return result


# ===================================================================
# Treatment Effect Modifier Network
# ===================================================================

class TreatmentEffectModifier(nn.Module):
    """Maps (tissue_state, treatment) → latent shift.

    This is a **dose-response curve** in latent space: how does each
    treatment combination perturb the tissue state trajectory?
    """

    def __init__(
        self,
        latent_dim: int = 128,
        num_treatments: int = 5,
        hidden_dim: int = 128,
    ):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(latent_dim + num_treatments, hidden_dim),
            nn.SiLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, latent_dim),
            nn.Tanh(),  # Bounded shift
        )
        self.scale = nn.Parameter(torch.tensor(0.1))  # Learnable scale

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x = cat(tissue_state, treatment_vec). Returns Δz."""
        return self.net(x) * self.scale
