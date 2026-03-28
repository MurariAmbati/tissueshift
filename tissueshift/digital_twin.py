"""Patient digital twin — personalised disease simulation.

A **digital twin** is a computational replica of an individual patient's
tumour biology.  It combines:

1. The patient's observed tissue state (from the VAE manifold)
2. Their molecular profile and spatial features
3. The learned Neural ODE dynamics
4. Treatment effect modifiers

to create a *personalised simulator* that can:

* **Forecast** how the tumour will evolve over months/years
* **Simulate interventions** — what happens under treatment A vs B?
* **Estimate risk windows** — when does subtype shift become likely?
* **Optimise treatment timing** — when should treatment switch?
* **Generate virtual biopsies** — predict what the tumour would look
  like at a future timepoint

This module is the bridge between the research model and clinical
decision support.

References
----------
Björnsson et al., "Digital twins to personalize medicine", Genome Medicine 2019.
Lal et al., "Using Digital Twins for Treatment Optimization", PNAS 2022.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


# ===================================================================
# Configuration
# ===================================================================

@dataclass
class DigitalTwinConfig:
    """Configuration for the digital twin simulator."""

    default_horizon_days: int = 1825  # 5 years
    simulation_resolution_days: int = 30  # monthly snapshots
    num_monte_carlo_trajectories: int = 100
    risk_threshold_entropy: float = 1.5  # entropy above this = elevated risk
    risk_threshold_drift: float = 0.7  # drift prob above this = subtype shift
    treatment_switch_evaluation_interval_days: int = 90
    virtual_biopsy_interval_days: int = 180


# ===================================================================
# Patient Profile
# ===================================================================

@dataclass
class PatientProfile:
    """Encapsulates all known information about a patient."""

    patient_id: str
    age: float = 0.0
    sex: str = "F"

    # Diagnosis
    diagnosis_date: Optional[str] = None
    primary_subtype: Optional[str] = None
    stage_at_diagnosis: Optional[str] = None
    grade: Optional[int] = None

    # Molecular profile
    er_status: Optional[str] = None  # positive | negative
    pr_status: Optional[str] = None
    her2_status: Optional[str] = None
    ki67_percent: Optional[float] = None
    brca_status: Optional[str] = None  # brca1 | brca2 | wild_type

    # Genomic features
    pik3ca_mutated: bool = False
    tp53_mutated: bool = False

    # Treatment history
    treatments: List[Dict[str, Any]] = field(default_factory=list)
    """List of {drug, start_date, end_date, response}."""

    # Longitudinal observations
    observations: List[Dict[str, Any]] = field(default_factory=list)
    """List of {date, tissue_state, subtype_probs, ...}."""

    # Tissue state (from model)
    current_tissue_state: Optional[np.ndarray] = None
    current_tissue_state_logvar: Optional[np.ndarray] = None

    def days_since_diagnosis(self, ref_date: Optional[str] = None) -> float:
        """Compute days from diagnosis to reference date."""
        if self.diagnosis_date is None:
            return 0.0
        try:
            d0 = datetime.strptime(self.diagnosis_date, "%Y-%m-%d")
            if ref_date:
                d1 = datetime.strptime(ref_date, "%Y-%m-%d")
            else:
                d1 = datetime.now()
            return (d1 - d0).days
        except (ValueError, TypeError):
            return 0.0

    def active_treatments(self, date: Optional[str] = None) -> List[str]:
        """Return names of active treatments at the given date."""
        active = []
        for tx in self.treatments:
            try:
                start = datetime.strptime(tx.get("start_date", ""), "%Y-%m-%d")
                end_str = tx.get("end_date", "")
                end = datetime.strptime(end_str, "%Y-%m-%d") if end_str else datetime.now()
                ref = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
                if start <= ref <= end:
                    active.append(tx.get("drug", "unknown"))
            except (ValueError, TypeError):
                continue
        return active

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to dict."""
        d = {
            "patient_id": self.patient_id,
            "age": self.age,
            "primary_subtype": self.primary_subtype,
            "stage": self.stage_at_diagnosis,
            "er_status": self.er_status,
            "pr_status": self.pr_status,
            "her2_status": self.her2_status,
            "ki67_percent": self.ki67_percent,
            "n_observations": len(self.observations),
            "n_treatments": len(self.treatments),
        }
        if self.current_tissue_state is not None:
            d["tissue_state_available"] = True
        return d


# ===================================================================
# Core Digital Twin
# ===================================================================

class DigitalTwin:
    """Patient-specific computational replica for disease simulation.

    Combines the patient profile with the TissueShift model ensemble
    to produce personalised forecasts and treatment simulations.
    """

    def __init__(
        self,
        profile: PatientProfile,
        dynamics_model: nn.Module,
        subtype_head: nn.Module,
        survival_head: Optional[nn.Module] = None,
        treatment_modifier: Optional[nn.Module] = None,
        cfg: DigitalTwinConfig = DigitalTwinConfig(),
        device: str = "cpu",
    ):
        self.profile = profile
        self.dynamics = dynamics_model.to(device).eval()
        self.subtype_head = subtype_head.to(device).eval()
        self.survival_head = survival_head.to(device).eval() if survival_head else None
        self.treatment_mod = treatment_modifier.to(device).eval() if treatment_modifier else None
        self.cfg = cfg
        self.device = device

        # Simulation cache
        self._trajectory_cache: Optional[Dict[str, Any]] = None

    @property
    def tissue_state(self) -> Optional[torch.Tensor]:
        if self.profile.current_tissue_state is not None:
            return torch.tensor(
                self.profile.current_tissue_state,
                dtype=torch.float32,
                device=self.device,
            )
        return None

    @property
    def tissue_state_logvar(self) -> Optional[torch.Tensor]:
        if self.profile.current_tissue_state_logvar is not None:
            return torch.tensor(
                self.profile.current_tissue_state_logvar,
                dtype=torch.float32,
                device=self.device,
            )
        return None

    # ---------------------------------------------------------------
    # Trajectory forecasting
    # ---------------------------------------------------------------

    @torch.no_grad()
    def forecast(
        self,
        horizon_days: Optional[int] = None,
        resolution_days: Optional[int] = None,
        n_trajectories: Optional[int] = None,
        treatment_vec: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        """Simulate future disease trajectories.

        Returns
        -------
        Dict with:
            times_days : (T,) numpy — evaluation timepoints
            trajectories : (S, T, D) tensor — sampled latent trajectories
            mean_trajectory : (T, D) — mean
            subtype_evolution : (T, C) — mean subtype probs over time
            subtype_entropy : (T,) — predictive entropy
            risk_windows : list of {start_day, end_day, risk_type, severity}
        """
        z0 = self.tissue_state
        if z0 is None:
            raise ValueError("No tissue state available for this patient.")

        H = horizon_days or self.cfg.default_horizon_days
        R = resolution_days or self.cfg.simulation_resolution_days
        S = n_trajectories or self.cfg.num_monte_carlo_trajectories

        t_eval = torch.linspace(0, H, H // R + 1, device=self.device)

        # Sample from variational posterior
        z0_logvar = self.tissue_state_logvar
        all_traj = []
        for _ in range(S):
            if z0_logvar is not None:
                std = (0.5 * z0_logvar).exp()
                z_start = z0.unsqueeze(0) + std.unsqueeze(0) * torch.randn_like(std.unsqueeze(0))
            else:
                z_start = z0.unsqueeze(0)

            # Apply treatment modifier
            if self.treatment_mod is not None and treatment_vec is not None:
                tv = treatment_vec.to(self.device).unsqueeze(0)
                shift = self.treatment_mod(torch.cat([z_start, tv], dim=-1))
                z_start = z_start + shift

            traj = self.dynamics(z_start, t_eval)  # (T, 1, D)
            all_traj.append(traj.squeeze(1))

        trajs = torch.stack(all_traj, dim=0)  # (S, T, D)
        mean_traj = trajs.mean(dim=0)

        # Subtype evolution
        subtype_probs_all = []
        for s in range(S):
            out = self.subtype_head(trajs[s])
            pk = "pam50_probs" if "pam50_probs" in out else next(
                k for k in out if "probs" in k
            )
            subtype_probs_all.append(out[pk].cpu())

        sp_stack = torch.stack(subtype_probs_all, dim=0)  # (S, T, C)
        mean_sp = sp_stack.mean(dim=0).numpy()
        eps = 1e-10
        entropy = -(mean_sp * np.log(mean_sp + eps)).sum(axis=-1)

        # Detect risk windows
        risk_windows = self._detect_risk_windows(t_eval.cpu().numpy(), mean_sp, entropy)

        result = {
            "times_days": t_eval.cpu().numpy(),
            "trajectories": trajs.cpu(),
            "mean_trajectory": mean_traj.cpu(),
            "subtype_evolution": mean_sp,
            "subtype_entropy": entropy,
            "risk_windows": risk_windows,
        }

        # Survival if available
        if self.survival_head is not None:
            surv_out = self.survival_head(mean_traj)
            result["survival_curve"] = surv_out.get("survival_curve", surv_out.get("hazard_probs")).cpu().numpy()
            if "risk_score" in surv_out:
                result["risk_score_evolution"] = surv_out["risk_score"].cpu().numpy()

        self._trajectory_cache = result
        return result

    def _detect_risk_windows(
        self,
        times: np.ndarray,
        subtype_probs: np.ndarray,
        entropy: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """Identify periods of elevated risk from the forecast."""
        windows: list[Dict[str, Any]] = []
        in_window = False
        window_start = 0

        for i, t in enumerate(times):
            # High entropy → uncertain subtype → transition risk
            high_risk = entropy[i] > self.cfg.risk_threshold_entropy

            # Check for dominant subtype change
            if i > 0:
                prev_dom = subtype_probs[i - 1].argmax()
                curr_dom = subtype_probs[i].argmax()
                if prev_dom != curr_dom:
                    windows.append({
                        "start_day": float(times[max(0, i - 1)]),
                        "end_day": float(t),
                        "risk_type": "subtype_shift",
                        "severity": "high",
                        "detail": f"Dominant subtype changed from class {prev_dom} to {curr_dom}",
                    })

            if high_risk and not in_window:
                window_start = t
                in_window = True
            elif not high_risk and in_window:
                windows.append({
                    "start_day": float(window_start),
                    "end_day": float(t),
                    "risk_type": "elevated_uncertainty",
                    "severity": "moderate",
                })
                in_window = False

        return windows

    # ---------------------------------------------------------------
    # Treatment comparison
    # ---------------------------------------------------------------

    @torch.no_grad()
    def compare_treatments(
        self,
        treatment_options: Dict[str, torch.Tensor],
        horizon_days: Optional[int] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Compare disease trajectories under different treatments.

        Parameters
        ----------
        treatment_options : mapping of treatment_name → binary vector

        Returns
        -------
        Nested dict: treatment_name → forecast results
        """
        results: Dict[str, Dict[str, Any]] = {}
        results["no_treatment"] = self.forecast(
            horizon_days=horizon_days, treatment_vec=None
        )

        for name, t_vec in treatment_options.items():
            results[name] = self.forecast(
                horizon_days=horizon_days, treatment_vec=t_vec
            )

        return results

    # ---------------------------------------------------------------
    # Treatment switching optimisation
    # ---------------------------------------------------------------

    @torch.no_grad()
    def optimal_switch_time(
        self,
        current_treatment: torch.Tensor,
        candidate_treatment: torch.Tensor,
        horizon_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Find the optimal time to switch from current to candidate treatment.

        Evaluates switching at each evaluation interval and picks the
        time that minimises risk (maximum survival probability or
        minimum entropy).

        Returns
        -------
        Dict with: optimal_day, benefit_curve, current_forecast, switched_forecast
        """
        H = horizon_days or self.cfg.default_horizon_days
        interval = self.cfg.treatment_switch_evaluation_interval_days
        switch_times = list(range(0, H, interval))

        current_fc = self.forecast(horizon_days=H, treatment_vec=current_treatment)
        benefits = []

        for sw_day in switch_times:
            # Simulate: current treatment until sw_day, then candidate
            t_eval = torch.linspace(0, H, H // 30 + 1, device=self.device)

            z0 = self.tissue_state.unsqueeze(0)
            if self.treatment_mod is not None:
                # Phase 1: current treatment
                t1 = t_eval[t_eval <= sw_day]
                if len(t1) > 1:
                    tv = current_treatment.to(self.device).unsqueeze(0)
                    shift = self.treatment_mod(torch.cat([z0, tv], dim=-1))
                    z_phase1 = self.dynamics(z0 + shift, t1)
                    z_switch = z_phase1[-1].unsqueeze(0)
                else:
                    z_switch = z0

                # Phase 2: candidate treatment
                t2 = t_eval[t_eval >= sw_day]
                if len(t2) > 1:
                    tv2 = candidate_treatment.to(self.device).unsqueeze(0)
                    shift2 = self.treatment_mod(torch.cat([z_switch, tv2], dim=-1))
                    z_phase2 = self.dynamics(z_switch + shift2, t2 - sw_day)
                    final_state = z_phase2[-1]
                else:
                    final_state = z_switch.squeeze(0)
            else:
                final_state = self.tissue_state

            # Score: lower entropy = better
            out = self.subtype_head(final_state)
            pk = "pam50_probs" if "pam50_probs" in out else next(k for k in out if "probs" in k)
            probs = out[pk].cpu().numpy().flatten()
            ent = -(probs * np.log(probs + 1e-10)).sum()
            benefits.append({"switch_day": sw_day, "final_entropy": float(ent)})

        # Find optimal switch time
        best = min(benefits, key=lambda x: x["final_entropy"])

        return {
            "optimal_day": best["switch_day"],
            "benefit_curve": benefits,
            "current_forecast": current_fc,
        }

    # ---------------------------------------------------------------
    # Virtual biopsy
    # ---------------------------------------------------------------

    @torch.no_grad()
    def virtual_biopsy(
        self, target_day: float, treatment_vec: Optional[torch.Tensor] = None
    ) -> Dict[str, Any]:
        """Generate a virtual biopsy at a future timepoint.

        Predicts what the tumour's molecular/phenotypic state would
        look like if biopsied at *target_day*.
        """
        fc = self.forecast(
            horizon_days=int(target_day) + 30,
            treatment_vec=treatment_vec,
            n_trajectories=50,
        )

        # Find closest timepoint
        times = fc["times_days"]
        idx = int(np.argmin(np.abs(times - target_day)))

        z_at_time = fc["mean_trajectory"][idx]  # (D,)
        subtype_probs = fc["subtype_evolution"][idx]

        result: Dict[str, Any] = {
            "target_day": float(target_day),
            "actual_day": float(times[idx]),
            "tissue_state": z_at_time.numpy(),
            "subtype_probabilities": subtype_probs.tolist(),
            "dominant_subtype": int(subtype_probs.argmax()),
            "subtype_confidence": float(subtype_probs.max()),
            "entropy": float(fc["subtype_entropy"][idx]),
        }

        # Survival estimate if available
        if "survival_curve" in fc:
            result["survival_curve_at_biopsy"] = fc["survival_curve"][idx].tolist()
        if "risk_score_evolution" in fc:
            result["risk_score"] = float(fc["risk_score_evolution"][idx])

        return result

    # ---------------------------------------------------------------
    # Summary / report
    # ---------------------------------------------------------------

    def clinical_summary(self) -> Dict[str, Any]:
        """Generate a clinical summary of the digital twin's findings.

        Returns
        -------
        Structured dict suitable for display in the clinical dashboard.
        """
        summary: Dict[str, Any] = {
            "patient": self.profile.to_dict(),
        }

        if self._trajectory_cache is not None:
            fc = self._trajectory_cache
            T = fc["subtype_evolution"].shape[0]

            # Current state
            summary["current"] = {
                "dominant_subtype": int(fc["subtype_evolution"][0].argmax()),
                "subtype_confidence": float(fc["subtype_evolution"][0].max()),
                "entropy": float(fc["subtype_entropy"][0]),
            }

            # 1-year outlook
            idx_1y = min(int(365 / (self.cfg.simulation_resolution_days or 30)), T - 1)
            summary["outlook_1year"] = {
                "dominant_subtype": int(fc["subtype_evolution"][idx_1y].argmax()),
                "subtype_shift_likely": bool(
                    fc["subtype_evolution"][idx_1y].argmax()
                    != fc["subtype_evolution"][0].argmax()
                ),
                "entropy": float(fc["subtype_entropy"][idx_1y]),
            }

            # Risk windows
            summary["risk_windows"] = fc.get("risk_windows", [])

            # Key time-to-events
            high_risk_times = [
                t for t, e in zip(fc["times_days"], fc["subtype_entropy"])
                if e > self.cfg.risk_threshold_entropy
            ]
            if high_risk_times:
                summary["first_high_risk_day"] = float(high_risk_times[0])

        return summary


# ===================================================================
# Cohort Digital Twin Manager
# ===================================================================

class CohortTwinManager:
    """Manage digital twins for an entire cohort.

    Supports batch simulation, stratification, and cohort-level
    statistical summaries.
    """

    def __init__(self, device: str = "cpu"):
        self.twins: Dict[str, DigitalTwin] = {}
        self.device = device

    def register(self, twin: DigitalTwin) -> None:
        self.twins[twin.profile.patient_id] = twin

    def __len__(self) -> int:
        return len(self.twins)

    def forecast_all(
        self, horizon_days: int = 1825, **kwargs: Any
    ) -> Dict[str, Dict[str, Any]]:
        """Run forecast for all twins.

        Returns
        -------
        Dict mapping patient_id → forecast results
        """
        results: Dict[str, Dict[str, Any]] = {}
        for pid, twin in self.twins.items():
            try:
                results[pid] = twin.forecast(horizon_days=horizon_days, **kwargs)
            except Exception as e:
                logger.warning("Failed forecast for %s: %s", pid, e)
        return results

    def stratify_by_risk(
        self, forecasts: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, List[str]]:
        """Stratify patients into risk groups based on forecasts.

        Returns
        -------
        Dict with "low_risk", "moderate_risk", "high_risk" → list of patient_ids
        """
        if forecasts is None:
            forecasts = self.forecast_all()

        groups: Dict[str, List[str]] = {
            "low_risk": [],
            "moderate_risk": [],
            "high_risk": [],
        }

        for pid, fc in forecasts.items():
            max_ent = float(fc["subtype_entropy"].max())
            risk_windows = fc.get("risk_windows", [])
            n_shift = sum(1 for w in risk_windows if w["risk_type"] == "subtype_shift")

            if n_shift > 0 or max_ent > 2.0:
                groups["high_risk"].append(pid)
            elif max_ent > 1.2:
                groups["moderate_risk"].append(pid)
            else:
                groups["low_risk"].append(pid)

        return groups

    def summary_statistics(
        self, forecasts: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Cohort-level summary statistics."""
        if forecasts is None:
            forecasts = self.forecast_all()

        entropies_1y = []
        for fc in forecasts.values():
            T = fc["subtype_entropy"].shape[0]
            idx_1y = min(12, T - 1)  # 12 months
            entropies_1y.append(float(fc["subtype_entropy"][idx_1y]))

        groups = self.stratify_by_risk(forecasts)

        return {
            "n_patients": len(forecasts),
            "mean_entropy_1year": float(np.mean(entropies_1y)) if entropies_1y else 0.0,
            "std_entropy_1year": float(np.std(entropies_1y)) if entropies_1y else 0.0,
            "n_high_risk": len(groups["high_risk"]),
            "n_moderate_risk": len(groups["moderate_risk"]),
            "n_low_risk": len(groups["low_risk"]),
        }
