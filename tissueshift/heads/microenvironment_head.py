"""
Microenvironment remodelling score head.

Estimates whether the stroma, immune context, and tissue
architecture look consistent with a more permissive progression
state — i.e. whether the microenvironment is primed for invasion,
immune evasion, or metastatic seeding.
"""

from __future__ import annotations

from typing import Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


class MicroenvironmentHead(nn.Module):
    """
    Outputs
    -------
    remodelling_score : (B, 1)  — overall [0, 1] permissiveness
    component_scores : (B, 6)   — per-component breakdown:
       stromal_activation, immune_exclusion, ecm_remodelling,
       angiogenic_potential, invasive_permissiveness, metabolic_shift
    """

    COMPONENTS = (
        "stromal_activation",
        "immune_exclusion",
        "ecm_remodelling",
        "angiogenic_potential",
        "invasive_permissiveness",
        "metabolic_shift",
    )

    def __init__(self, latent_dim: int = 128, hidden_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
        )
        self.overall_head = nn.Linear(hidden_dim // 2, 1)
        self.component_head = nn.Linear(hidden_dim // 2, len(self.COMPONENTS))

    def forward(self, tissue_state: torch.Tensor) -> Dict[str, torch.Tensor]:
        h = self.net(tissue_state)
        return {
            "remodelling_score": torch.sigmoid(self.overall_head(h)),
            "component_scores": torch.sigmoid(self.component_head(h)),
        }
