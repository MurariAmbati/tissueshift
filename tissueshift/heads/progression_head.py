"""
Progression-stage classification head.

Estimates where the biopsy sits on the continuum:
  pre-invasive → invasive → locally advanced →
  metastatic-adapted → ambiguous intermediate.
"""

from __future__ import annotations

from typing import Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


class ProgressionHead(nn.Module):
    """
    Progression outputs:
      stage_logits : (B, 5)
      stage_probs : (B, 5)
      stage_ordinal : (B, 1) — continuous progression score [0, 1]
    """

    STAGES = (
        "pre_invasive",
        "invasive",
        "locally_advanced",
        "metastatic_adapted",
        "ambiguous_intermediate",
    )

    def __init__(self, latent_dim: int = 128, hidden_dim: int = 256, num_stages: int = 5, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.stage_head = nn.Linear(hidden_dim, num_stages)
        self.ordinal_head = nn.Linear(hidden_dim, 1)

    def forward(self, tissue_state: torch.Tensor) -> Dict[str, torch.Tensor]:
        h = self.net(tissue_state)

        stage_logits = self.stage_head(h)
        stage_probs = F.softmax(stage_logits, dim=-1)
        stage_ordinal = torch.sigmoid(self.ordinal_head(h))

        return {
            "stage_logits": stage_logits,
            "stage_probs": stage_probs,
            "stage_ordinal": stage_ordinal,
        }
