"""
Time-to-event / survival prediction head.

Discrete-time survival model (Nnet-survival style) that predicts
hazards over fixed time intervals. Compatible with scikit-survival
evaluation metrics.
"""

from __future__ import annotations

from typing import Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


class SurvivalHead(nn.Module):
    """
    Discrete-time survival head.

    Outputs
    -------
    hazard_logits : (B, num_intervals)
    hazard_probs : (B, num_intervals)  — per-interval hazard
    survival_curve : (B, num_intervals) — cumulative survival
    risk_score : (B, 1) — single risk scalar (mean hazard)
    """

    def __init__(
        self,
        latent_dim: int = 128,
        hidden_dim: int = 256,
        num_intervals: int = 20,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.num_intervals = num_intervals
        self.net = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
        )
        self.hazard_head = nn.Linear(hidden_dim // 2, num_intervals)

    def forward(self, tissue_state: torch.Tensor) -> Dict[str, torch.Tensor]:
        h = self.net(tissue_state)
        hazard_logits = self.hazard_head(h)
        hazard_probs = torch.sigmoid(hazard_logits)

        # Cumulative survival: S(t) = prod(1 - h(i)) for i <= t
        survival = torch.cumprod(1.0 - hazard_probs, dim=-1)

        # Single risk score
        risk = hazard_probs.mean(dim=-1, keepdim=True)

        return {
            "hazard_logits": hazard_logits,
            "hazard_probs": hazard_probs,
            "survival_curve": survival,
            "risk_score": risk,
        }
