"""Prediction heads for all six benchmark tracks."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class SubtypeHead(nn.Module):
    """PAM50 subtype classification (Track 1: SubtypeCall).

    Predicts 5-class PAM50 subtype from tissue state.
    Evaluation: macro-F1, Cohen's kappa, balanced accuracy.
    """

    def __init__(self, state_dim: int = 512, n_subtypes: int = 5, dropout: float = 0.1):
        super().__init__()
        self.head = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, n_subtypes),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.head(state)


class DriftHead(nn.Module):
    """Subtype drift prediction (Track 2: SubtypeDrift).

    Predicts probability of subtype change between time points.
    Input: concatenation of two tissue states (t1 ⊕ t2).
    """

    def __init__(self, state_dim: int = 512, n_subtypes: int = 5, dropout: float = 0.1):
        super().__init__()
        # Drift binary classifier (will subtype change?)
        self.drift_classifier = nn.Sequential(
            nn.Linear(state_dim * 2, 256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, 1),
        )
        # If drifting, what's the target subtype?
        self.target_subtype = nn.Sequential(
            nn.Linear(state_dim * 2, 256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, n_subtypes),
        )

    def forward(
        self, state_t1: torch.Tensor, state_t2: torch.Tensor
    ) -> dict[str, torch.Tensor]:
        paired = torch.cat([state_t1, state_t2], dim=-1)
        return {
            "drift_logit": self.drift_classifier(paired).squeeze(-1),
            "target_subtype_logits": self.target_subtype(paired),
        }


class ProgressionHead(nn.Module):
    """Histological progression stage (Track 3: ProgressionStage).

    Predicts: Normal → ADH → DCIS → IDC → Metastatic.
    Ordinal regression via cumulative logits (CORN).
    """

    STAGES = ["Normal", "ADH", "DCIS", "IDC", "Metastatic"]

    def __init__(self, state_dim: int = 512, n_stages: int = 5, dropout: float = 0.1):
        super().__init__()
        self.n_stages = n_stages
        # Shared feature extractor
        self.features = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        # Ordinal regression: n_stages - 1 cumulative thresholds
        self.thresholds = nn.Linear(256, n_stages - 1)

    def forward(self, state: torch.Tensor) -> dict[str, torch.Tensor]:
        h = self.features(state)
        cumulative_logits = self.thresholds(h)  # (B, n_stages-1)
        # P(Y > k) = sigmoid(logit_k)
        cumulative_probs = torch.sigmoid(cumulative_logits)
        # P(Y = k) = P(Y > k-1) - P(Y > k)
        probs = torch.zeros(
            state.shape[0], self.n_stages, device=state.device
        )
        probs[:, 0] = 1 - cumulative_probs[:, 0]
        for k in range(1, self.n_stages - 1):
            probs[:, k] = cumulative_probs[:, k - 1] - cumulative_probs[:, k]
        probs[:, -1] = cumulative_probs[:, -1]

        return {
            "cumulative_logits": cumulative_logits,
            "stage_probs": probs,
            "stage_pred": probs.argmax(dim=-1),
        }


class SurvivalHead(nn.Module):
    """Overall survival prediction (Track 5: Survival).

    Discrete-time survival model (Nnet-survival / LogisticHazard).
    Predicts hazard at each time interval.
    """

    def __init__(
        self,
        state_dim: int = 512,
        n_intervals: int = 10,
        dropout: float = 0.25,
    ):
        super().__init__()
        self.n_intervals = n_intervals
        self.net = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, n_intervals),
        )

    def forward(self, state: torch.Tensor) -> dict[str, torch.Tensor]:
        hazard_logits = self.net(state)  # (B, T)
        hazard = torch.sigmoid(hazard_logits)
        # Survival function: S(t) = prod_{k<=t} (1 - h_k)
        survival = torch.cumprod(1 - hazard, dim=-1)
        return {
            "hazard_logits": hazard_logits,
            "hazard": hazard,
            "survival": survival,
        }


class Morph2MolHead(nn.Module):
    """Morphology-to-molecule prediction (Track 4: Morph2Mol).

    Predicts molecular features from pathology-only tissue state.
    Measures cross-modal prediction ability.
    """

    def __init__(
        self,
        state_dim: int = 512,
        n_genes: int = 250,
        n_pathways: int = 50,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.gene_predictor = nn.Sequential(
            nn.Linear(state_dim, 512),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(512, n_genes),
        )
        self.pathway_predictor = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, n_pathways),
        )

    def forward(self, state: torch.Tensor) -> dict[str, torch.Tensor]:
        return {
            "gene_pred": self.gene_predictor(state),
            "pathway_pred": self.pathway_predictor(state),
        }


class MicroenvironmentHead(nn.Module):
    """Microenvironment composition prediction (Track 6: SpatialPhenotype).

    Predicts TIL density, stromal fraction, immune infiltrate composition.
    """

    def __init__(self, state_dim: int = 512, dropout: float = 0.1):
        super().__init__()
        # TIL density (regression)
        self.til_density = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, 1),
            nn.Sigmoid(),  # fraction 0-1
        )
        # Stromal fraction (regression)
        self.stromal_fraction = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )
        # Immune composition (8 immune cell types, softmax)
        self.immune_composition = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, 8),
        )

    def forward(self, state: torch.Tensor) -> dict[str, torch.Tensor]:
        return {
            "til_density": self.til_density(state).squeeze(-1),
            "stromal_fraction": self.stromal_fraction(state).squeeze(-1),
            "immune_composition": F.softmax(
                self.immune_composition(state), dim=-1
            ),
        }


class TissueShiftHeads(nn.Module):
    """All prediction heads bundled together."""

    def __init__(self, state_dim: int = 512):
        super().__init__()
        self.subtype = SubtypeHead(state_dim)
        self.drift = DriftHead(state_dim)
        self.progression = ProgressionHead(state_dim)
        self.survival = SurvivalHead(state_dim)
        self.morph2mol = Morph2MolHead(state_dim)
        self.microenv = MicroenvironmentHead(state_dim)
