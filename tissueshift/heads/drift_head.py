"""
Subtype drift prediction head.

Predicts whether the tissue state will remain stable, drift within
lineage, or switch toward a different subtype neighbourhood.
"""

from __future__ import annotations

from typing import Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


class DriftHead(nn.Module):
    """
    Drift prediction outputs:
      drift_class : (B, 3)  — stable / within-lineage-drift / cross-subtype shift
      drift_probs : (B, 3)
      drift_magnitude : (B, 1) — predicted magnitude of tissue-state change
      target_subtype_probs : (B, 7) — where the drift is heading
    """

    DRIFT_CLASSES = ("stable", "within_lineage_drift", "cross_subtype_shift")

    def __init__(self, latent_dim: int = 128, hidden_dim: int = 256, num_subtypes: int = 7, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.drift_class_head = nn.Linear(hidden_dim, 3)
        self.drift_magnitude_head = nn.Linear(hidden_dim, 1)
        self.target_subtype_head = nn.Linear(hidden_dim, num_subtypes)

    def forward(self, tissue_state: torch.Tensor) -> Dict[str, torch.Tensor]:
        h = self.net(tissue_state)

        drift_logits = self.drift_class_head(h)
        drift_probs = F.softmax(drift_logits, dim=-1)
        drift_magnitude = F.softplus(self.drift_magnitude_head(h))
        target_probs = F.softmax(self.target_subtype_head(h), dim=-1)

        return {
            "drift_logits": drift_logits,
            "drift_probs": drift_probs,
            "drift_magnitude": drift_magnitude,
            "target_subtype_probs": target_probs,
        }
