"""Subtype transition lattice: models temporal subtype emergence and transitions."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


# PAM50 subtype ordering (biological progression lattice)
SUBTYPES = ["LumA", "LumB", "Her2", "Basal", "Normal"]

# Allowed transitions in the biological lattice
# Edges encode known clinical progression patterns
TRANSITION_EDGES = [
    ("Normal", "LumA"),
    ("LumA", "LumB"),
    ("LumB", "Her2"),
    ("Her2", "Basal"),
    ("LumA", "Her2"),  # direct luminal→HER2 switch
    ("Normal", "LumB"),
    # Reverse transitions (de-differentiation, rare but observed)
    ("LumB", "LumA"),
]


class SubtypeTransitionModel(nn.Module):
    """Models probabilistic transitions between subtypes on a directed lattice.

    Uses the tissue state to predict:
    1. Current subtype probabilities
    2. Most likely next subtype (transition prediction)
    3. Transition probability matrix
    """

    def __init__(
        self,
        state_dim: int = 512,
        n_subtypes: int = 5,
        hidden_dim: int = 256,
    ):
        super().__init__()
        self.n_subtypes = n_subtypes

        # Current subtype classifier
        self.subtype_head = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, n_subtypes),
        )

        # Transition matrix predictor
        # Predicts a row of the transition matrix conditioned on tissue state
        self.transition_head = nn.Sequential(
            nn.Linear(state_dim + n_subtypes, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, n_subtypes),
        )

        # Build adjacency mask for valid transitions
        self._build_adjacency()

    def _build_adjacency(self):
        """Build binary adjacency matrix from allowed transitions."""
        adj = torch.zeros(self.n_subtypes, self.n_subtypes)
        # Self-loops (stay in same subtype)
        for i in range(self.n_subtypes):
            adj[i, i] = 1.0

        for src, dst in TRANSITION_EDGES:
            if src in SUBTYPES and dst in SUBTYPES:
                i, j = SUBTYPES.index(src), SUBTYPES.index(dst)
                adj[i, j] = 1.0

        self.register_buffer("adjacency", adj)

    def forward(
        self, tissue_state: torch.Tensor
    ) -> dict[str, torch.Tensor]:
        """Predict subtypes and transitions.

        Args:
            tissue_state: (B, state_dim) tissue state vector

        Returns:
            Dictionary with:
                subtype_logits: (B, n_subtypes)
                subtype_probs: (B, n_subtypes)
                transition_logits: (B, n_subtypes) — next-subtype logits
                transition_probs: (B, n_subtypes) — next-subtype probabilities
        """
        # Current subtype
        subtype_logits = self.subtype_head(tissue_state)
        subtype_probs = F.softmax(subtype_logits, dim=-1)

        # Transition prediction conditioned on state + current subtype
        trans_input = torch.cat([tissue_state, subtype_probs], dim=-1)
        transition_logits = self.transition_head(trans_input)

        # Mask invalid transitions based on predicted current subtype
        # Weight adjacency by current subtype distribution
        valid_mask = torch.matmul(subtype_probs, self.adjacency)  # (B, n_subtypes)
        transition_logits = transition_logits + torch.log(valid_mask.clamp(min=1e-8))
        transition_probs = F.softmax(transition_logits, dim=-1)

        return {
            "subtype_logits": subtype_logits,
            "subtype_probs": subtype_probs,
            "transition_logits": transition_logits,
            "transition_probs": transition_probs,
        }


class TemporalTransitionLoss(nn.Module):
    """Loss for temporal subtype transitions in longitudinal data.

    When paired samples (t1, t2) exist, enforces that predicted
    transitions match observed subtype changes.
    """

    def __init__(self, lattice_weight: float = 0.1):
        super().__init__()
        self.ce = nn.CrossEntropyLoss()
        self.lattice_weight = lattice_weight

    def forward(
        self,
        transition_logits: torch.Tensor,
        target_next_subtype: torch.Tensor,
        subtype_logits: torch.Tensor,
        current_subtype: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        """Compute transition loss.

        Args:
            transition_logits: (B, n_subtypes) predicted next subtype
            target_next_subtype: (B,) ground-truth next subtype
            subtype_logits: (B, n_subtypes) current subtype prediction
            current_subtype: (B,) ground-truth current subtype

        Returns:
            Dictionary with total loss and components
        """
        # Current subtype CE
        current_loss = self.ce(subtype_logits, current_subtype)

        # Transition CE (only for pairs with known next subtype)
        valid = target_next_subtype >= 0
        if valid.any():
            trans_loss = self.ce(
                transition_logits[valid], target_next_subtype[valid]
            )
        else:
            trans_loss = torch.tensor(0.0, device=transition_logits.device)

        total = current_loss + self.lattice_weight * trans_loss

        return {
            "loss": total,
            "current_subtype_loss": current_loss,
            "transition_loss": trans_loss,
        }
