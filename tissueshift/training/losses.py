"""
Multi-task loss for TissueShift.

Combines losses from all six prediction families with configurable
weights per training stage.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from tissueshift.config import TrainingConfig


class TissueShiftLoss(nn.Module):
    """
    Composite loss for TissueShift multi-task training.

    Components:
      - Subtype classification (CE + label smoothing)
      - Drift prediction (CE for class, MSE for magnitude)
      - Progression stage (ordinal CE)
      - Molecular reconstruction (MSE)
      - Microenvironment (BCE)
      - Survival (negative log-likelihood, discrete-time)
      - KL divergence (VAE regularisation)
      - Region classification (CE, auxiliary)
    """

    def __init__(self, cfg: TrainingConfig):
        super().__init__()
        self.cfg = cfg

        # Classification losses with label smoothing
        self.subtype_ce = nn.CrossEntropyLoss(label_smoothing=0.05)
        self.drift_ce = nn.CrossEntropyLoss()
        self.stage_ce = nn.CrossEntropyLoss(label_smoothing=0.05)
        self.region_ce = nn.CrossEntropyLoss(ignore_index=-1)

        # Regression / reconstruction
        self.mse = nn.MSELoss()
        self.bce = nn.BCELoss()

    def forward(
        self,
        outputs: Dict[str, torch.Tensor],
        targets: Dict[str, torch.Tensor],
        stage: int = 4,
    ) -> Dict[str, torch.Tensor]:
        """
        Compute composite loss.

        Parameters
        ----------
        outputs : dict from TissueShiftModel.forward()
        targets : dict with ground-truth labels
        stage : training stage (1–6), controls which losses are active

        Returns
        -------
        dict with 'total' and individual loss components.
        """
        losses: Dict[str, torch.Tensor] = {}
        device = next(iter(outputs.values())).device if outputs else torch.device("cpu")
        zero = torch.tensor(0.0, device=device)

        # ---- Subtype loss ----
        if "subtype_pam50_logits" in outputs and "pam50_idx" in targets:
            target = targets["pam50_idx"].to(device)
            if target.max() >= 0:  # valid labels
                losses["subtype"] = self.subtype_ce(
                    outputs["subtype_pam50_logits"], target
                ) * self.cfg.loss_subtype_w

        # ---- Drift loss ----
        if "drift_logits" in outputs and "drift_class" in targets:
            losses["drift"] = self.drift_ce(
                outputs["drift_logits"], targets["drift_class"].to(device)
            ) * self.cfg.loss_drift_w

        if "drift_magnitude" in outputs and "drift_magnitude_target" in targets:
            losses["drift_mag"] = self.mse(
                outputs["drift_magnitude"],
                targets["drift_magnitude_target"].to(device),
            ) * self.cfg.loss_drift_w * 0.5

        # ---- Progression stage loss ----
        if "progression_stage_logits" in outputs and "stage_idx" in targets:
            losses["stage"] = self.stage_ce(
                outputs["progression_stage_logits"], targets["stage_idx"].to(device)
            ) * self.cfg.loss_stage_w

        # ---- Molecular reconstruction loss ----
        if "bridge_predicted_expression" in outputs and "expression_target" in targets:
            losses["mol_recon"] = self.mse(
                outputs["bridge_predicted_expression"],
                targets["expression_target"].to(device),
            ) * self.cfg.loss_mol_recon_w

        # ---- Microenvironment loss ----
        if "microenv_remodelling_score" in outputs and "microenv_target" in targets:
            losses["microenv"] = self.bce(
                outputs["microenv_remodelling_score"],
                targets["microenv_target"].to(device),
            ) * self.cfg.loss_microenv_w

        # ---- Survival loss (discrete-time NLL) ----
        if "survival_hazard_probs" in outputs and "survival_target" in targets:
            losses["survival"] = self._discrete_survival_loss(
                outputs["survival_hazard_probs"],
                targets["survival_target"].to(device),
                targets.get("survival_mask", None),
            ) * self.cfg.loss_survival_w

        # ---- KL divergence (VAE) ----
        if "mu" in outputs and "logvar" in outputs:
            mu = outputs["mu"]
            logvar = outputs["logvar"]
            kl = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
            losses["kl"] = kl * self.cfg.loss_kl_w

        # ---- Region classification (auxiliary) ----
        if "region_logits" in outputs and "region_labels" in targets:
            B, N, C = outputs["region_logits"].shape
            logits_flat = outputs["region_logits"].reshape(B * N, C)
            labels_flat = targets["region_labels"].to(device).reshape(B * N)
            losses["region"] = self.region_ce(logits_flat, labels_flat) * 0.3

        # ---- Transition next-state loss ----
        if "transition_next_tissue_state" in outputs and "next_tissue_state" in targets:
            losses["transition"] = self.mse(
                outputs["transition_next_tissue_state"],
                targets["next_tissue_state"].to(device),
            ) * 0.5

        # ---- Total ----
        total = sum(losses.values()) if losses else zero
        losses["total"] = total

        return losses

    @staticmethod
    def _discrete_survival_loss(
        hazard_probs: torch.Tensor,
        targets: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Discrete-time survival NLL (Nnet-survival).

        targets : (B, T) — 1 if event occurred in interval, 0 otherwise
        mask : (B, T) — 1 if observed up to this interval
        """
        eps = 1e-7
        if mask is None:
            mask = torch.ones_like(targets)
        mask = mask.to(hazard_probs.device)
        targets = targets.to(hazard_probs.device)

        # Log-likelihood
        log_h = torch.log(hazard_probs + eps)
        log_1_minus_h = torch.log(1 - hazard_probs + eps)

        ll = targets * log_h + (1 - targets) * log_1_minus_h
        ll = ll * mask
        return -ll.sum() / mask.sum().clamp(min=1)
