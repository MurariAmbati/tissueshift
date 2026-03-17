"""Composite loss functions for multi-task training."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from world_model.manifold import VICRegLoss, SubtypeContrastiveLoss


class NNETSurvivalLoss(nn.Module):
    """Discrete-time survival loss (NNET-survival / LogisticHazard)."""

    def forward(
        self,
        hazard_logits: torch.Tensor,
        event_time_bin: torch.Tensor,
        event_indicator: torch.Tensor,
    ) -> torch.Tensor:
        """Compute negative log-likelihood for discrete hazard model.

        Args:
            hazard_logits: (B, T) logits for hazard at each interval
            event_time_bin: (B,) integer bin index for event/censor time
            event_indicator: (B,) 1=event, 0=censored
        """
        hazard = torch.sigmoid(hazard_logits)
        # Survival to event time: prod(1 - h_k) for k < t
        log_surv = torch.zeros_like(hazard_logits[:, 0])
        T = hazard_logits.shape[1]

        for t in range(T):
            at_risk = event_time_bin >= t
            log_h = F.logsigmoid(hazard_logits[:, t])
            log_1mh = F.logsigmoid(-hazard_logits[:, t])

            # Contribution from events at time t
            is_event_at_t = (event_time_bin == t) & (event_indicator == 1)
            log_surv = log_surv + at_risk.float() * log_1mh
            log_surv = log_surv + is_event_at_t.float() * (log_h - log_1mh)

        return -log_surv.mean()


class OrdinalRegressionLoss(nn.Module):
    """CORN ordinal regression loss for progression stages."""

    def forward(
        self,
        cumulative_logits: torch.Tensor,
        target: torch.Tensor,
    ) -> torch.Tensor:
        """Binary cross-entropy on cumulative logits.

        Args:
            cumulative_logits: (B, K-1) cumulative threshold logits
            target: (B,) ordinal class index (0 to K-1)
        """
        K_minus_1 = cumulative_logits.shape[1]
        # Target: P(Y > k) = 1 if target > k, 0 otherwise
        binary_targets = torch.zeros_like(cumulative_logits)
        for k in range(K_minus_1):
            binary_targets[:, k] = (target > k).float()

        return F.binary_cross_entropy_with_logits(
            cumulative_logits, binary_targets
        )


class TissueShiftLoss(nn.Module):
    """Composite multi-task loss for TissueShift.

    Combines:
    - Subtype classification CE
    - VICReg manifold regularization
    - Contrastive subtype alignment
    - Survival NLL
    - Ordinal progression
    - Morph2Mol regression
    - Microenvironment regression
    """

    def __init__(
        self,
        # Loss weights
        w_subtype: float = 1.0,
        w_vicreg: float = 0.1,
        w_contrastive: float = 0.5,
        w_survival: float = 0.5,
        w_progression: float = 0.3,
        w_morph2mol: float = 0.3,
        w_microenv: float = 0.2,
        w_transition: float = 0.3,
    ):
        super().__init__()
        self.weights = {
            "subtype": w_subtype,
            "vicreg": w_vicreg,
            "contrastive": w_contrastive,
            "survival": w_survival,
            "progression": w_progression,
            "morph2mol": w_morph2mol,
            "microenv": w_microenv,
            "transition": w_transition,
        }

        self.ce = nn.CrossEntropyLoss()
        self.vicreg = VICRegLoss()
        self.contrastive = SubtypeContrastiveLoss()
        self.survival_loss = NNETSurvivalLoss()
        self.ordinal_loss = OrdinalRegressionLoss()
        self.mse = nn.MSELoss()

    def forward(
        self,
        predictions: dict[str, torch.Tensor],
        targets: dict[str, torch.Tensor],
        manifold_proj: torch.Tensor | None = None,
        manifold_proj_aug: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        """Compute composite loss.

        Args:
            predictions: Dict of model outputs from all heads
            targets: Dict of ground-truth tensors
            manifold_proj: (B, D) manifold projection (view 1)
            manifold_proj_aug: (B, D) manifold projection (view 2, augmented)

        Returns:
            Dict with total loss and per-task losses
        """
        losses = {}
        total = torch.tensor(0.0, device=next(iter(predictions.values())).device)

        # 1. Subtype classification
        if "subtype_logits" in predictions and "subtype" in targets:
            l = self.ce(predictions["subtype_logits"], targets["subtype"])
            losses["subtype"] = l
            total = total + self.weights["subtype"] * l

        # 2. VICReg manifold
        if manifold_proj is not None and manifold_proj_aug is not None:
            vicreg_out = self.vicreg(manifold_proj, manifold_proj_aug)
            losses["vicreg"] = vicreg_out["loss"]
            total = total + self.weights["vicreg"] * vicreg_out["loss"]

        # 3. Contrastive
        if manifold_proj is not None and "subtype" in targets:
            l = self.contrastive(manifold_proj, targets["subtype"])
            losses["contrastive"] = l
            total = total + self.weights["contrastive"] * l

        # 4. Survival
        if "hazard_logits" in predictions and "event_time_bin" in targets:
            l = self.survival_loss(
                predictions["hazard_logits"],
                targets["event_time_bin"],
                targets["event_indicator"],
            )
            losses["survival"] = l
            total = total + self.weights["survival"] * l

        # 5. Progression
        if "cumulative_logits" in predictions and "progression_stage" in targets:
            l = self.ordinal_loss(
                predictions["cumulative_logits"],
                targets["progression_stage"],
            )
            losses["progression"] = l
            total = total + self.weights["progression"] * l

        # 6. Morph2Mol
        if "gene_pred" in predictions and "gene_expression" in targets:
            l_gene = self.mse(predictions["gene_pred"], targets["gene_expression"])
            l_pathway = self.mse(
                predictions["pathway_pred"], targets["pathway_scores"]
            ) if "pathway_pred" in predictions and "pathway_scores" in targets else 0.0
            l = l_gene + l_pathway
            losses["morph2mol"] = l
            total = total + self.weights["morph2mol"] * l

        # 7. Microenvironment
        if "til_density" in predictions and "til_density" in targets:
            l = self.mse(predictions["til_density"], targets["til_density"])
            losses["microenv_til"] = l
            total = total + self.weights["microenv"] * l

        # 8. Transition
        if "transition_logits" in predictions and "next_subtype" in targets:
            from world_model.transition import TemporalTransitionLoss
            tl = TemporalTransitionLoss()
            trans_out = tl(
                predictions["transition_logits"],
                targets["next_subtype"],
                predictions.get("subtype_logits", predictions["transition_logits"]),
                targets.get("subtype", targets["next_subtype"]),
            )
            losses["transition"] = trans_out["loss"]
            total = total + self.weights["transition"] * trans_out["loss"]

        losses["total"] = total
        return losses
