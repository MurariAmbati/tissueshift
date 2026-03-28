"""
Subtype classification head.

Predicts both clinical IHC-style subtype and PAM50 intrinsic
subtype from the tissue-state latent vector. Outputs probability
distributions rather than hard labels to represent mixed / boundary
states.
"""

from __future__ import annotations

from typing import Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


class SubtypeHead(nn.Module):
    """
    Multi-task subtype classifier.

    Outputs
    -------
    pam50_logits : (B, 5) — LumA, LumB, Her2, Basal, Normal
    pam50_probs : (B, 5)
    ihc_logits : (B, 4) — HR+/HER2-, HR+/HER2+, HR-/HER2+, TNBC
    ihc_probs : (B, 4)
    lattice_logits : (B, 7) — full lattice (includes Claudin-low)
    confidence : (B, 1) — max probability as confidence proxy
    """

    PAM50_CLASSES = ("LumA", "LumB", "Her2", "Basal", "Normal")
    IHC_CLASSES = ("HR+/HER2-", "HR+/HER2+", "HR-/HER2+", "TNBC")

    def __init__(self, latent_dim: int = 128, hidden_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.pam50_head = nn.Linear(hidden_dim, 5)
        self.ihc_head = nn.Linear(hidden_dim, 4)
        self.lattice_head = nn.Linear(hidden_dim, 7)

    def forward(self, tissue_state: torch.Tensor) -> Dict[str, torch.Tensor]:
        h = self.shared(tissue_state)

        pam50_logits = self.pam50_head(h)
        ihc_logits = self.ihc_head(h)
        lattice_logits = self.lattice_head(h)

        pam50_probs = F.softmax(pam50_logits, dim=-1)
        ihc_probs = F.softmax(ihc_logits, dim=-1)

        confidence = pam50_probs.max(dim=-1, keepdim=True).values

        return {
            "pam50_logits": pam50_logits,
            "pam50_probs": pam50_probs,
            "ihc_logits": ihc_logits,
            "ihc_probs": ihc_probs,
            "lattice_logits": lattice_logits,
            "confidence": confidence,
        }
