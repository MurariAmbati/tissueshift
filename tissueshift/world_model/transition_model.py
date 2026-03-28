"""
Subtype lattice transition model.

Operates on a subtype lattice (not a flat class list) so the tumour
can move through nearby states rather than teleporting between rigid
labels.

The lattice encodes biologically motivated adjacencies:
  - Luminal A ↔ Luminal B (luminal stabilisation / drift)
  - Luminal B ↔ Luminal B HER2+ (HER2 co-amplification)
  - Luminal B ↔ HER2-enriched (HER2-enrichment pressure)
  - Luminal B ↔ Basal-like (luminal–basal conversion)
  - HER2-enriched ↔ Basal-like (aggressive convergence)
  - Luminal A ↔ Normal-like (low-proliferative drift)
  - Basal-like ↔ Claudin-low (mesenchymal hardening)
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from tissueshift.config import TransitionModelConfig

logger = logging.getLogger(__name__)


class TimeEncoding(nn.Module):
    """Continuous time encoding for arbitrary day offsets."""

    def __init__(self, dim: int, max_days: int = 3650):
        super().__init__()
        self.max_days = max_days
        freqs = torch.exp(torch.arange(0, dim, 2).float() * -(math.log(10000.0) / dim))
        self.register_buffer("freqs", freqs)
        self.proj = nn.Linear(dim, dim)

    def forward(self, days: torch.Tensor) -> torch.Tensor:
        """
        days : (B,) — number of days.
        Returns : (B, dim)
        """
        # Normalise
        t = days.float().unsqueeze(-1) / self.max_days  # (B, 1)
        angles = t * self.freqs  # (B, dim//2)
        enc = torch.cat([angles.sin(), angles.cos()], dim=-1)
        return self.proj(enc)


class SubtypeLatticeTransition(nn.Module):
    """
    Subtype lattice transition model.

    Given a current tissue-state vector and optional time offset,
    predicts:
      - transition probabilities over lattice edges
      - drift direction (which subtype neighbourhood the tissue is
        moving toward)
      - stability score (likelihood of remaining in current state)
      - next-state tissue vector (predicted future tissue state)

    The lattice structure constrains transitions to biologically
    plausible paths.
    """

    def __init__(self, cfg: TransitionModelConfig, tissue_dim: int = 128):
        super().__init__()
        self.cfg = cfg
        self.tissue_dim = tissue_dim

        # Subtype node embeddings
        self.num_nodes = len(cfg.subtype_nodes)
        self.node_embed = nn.Embedding(self.num_nodes, cfg.transition_hidden_dim)
        self.node_names = list(cfg.subtype_nodes)
        self.node_to_idx = {n: i for i, n in enumerate(self.node_names)}

        # Build adjacency matrix from allowed transitions
        self.register_buffer("adj", self._build_adjacency())

        # Time encoding
        self.use_time = cfg.use_time_encoding
        self.time_enc = TimeEncoding(cfg.transition_hidden_dim, cfg.max_time_horizon_days) if self.use_time else None

        # Input: tissue_state → transition hidden
        self.state_proj = nn.Sequential(
            nn.Linear(tissue_dim, cfg.transition_hidden_dim),
            nn.LayerNorm(cfg.transition_hidden_dim),
            nn.GELU(),
        )

        # Transition MLP
        in_dim = cfg.transition_hidden_dim * 2  # state + node
        if self.use_time:
            in_dim += cfg.transition_hidden_dim
        layers = []
        for i in range(cfg.num_transition_layers):
            out_dim = cfg.transition_hidden_dim if i < cfg.num_transition_layers - 1 else cfg.transition_hidden_dim
            layers.extend([
                nn.Linear(in_dim if i == 0 else cfg.transition_hidden_dim, out_dim),
                nn.LayerNorm(out_dim),
                nn.GELU(),
                nn.Dropout(0.1),
            ])
        self.transition_mlp = nn.Sequential(*layers)

        # Heads
        self.edge_logit_head = nn.Linear(cfg.transition_hidden_dim, self.num_nodes)
        self.stability_head = nn.Linear(cfg.transition_hidden_dim, 1)
        self.next_state_head = nn.Linear(cfg.transition_hidden_dim, tissue_dim)

        # Drift direction head (predicts manifold movement vector)
        self.drift_head = nn.Linear(cfg.transition_hidden_dim, tissue_dim)

    def _build_adjacency(self) -> torch.Tensor:
        """Build symmetric adjacency matrix from config."""
        adj = torch.eye(self.num_nodes)  # self-loops (stay in state)
        for src, dst in self.cfg.allowed_transitions:
            i = self.node_to_idx.get(src)
            j = self.node_to_idx.get(dst)
            if i is not None and j is not None:
                adj[i, j] = 1.0
                adj[j, i] = 1.0
        return adj

    def get_current_subtype_logits(self, tissue_state: torch.Tensor) -> torch.Tensor:
        """
        Classify current tissue state into subtype nodes.
        
        tissue_state : (B, tissue_dim)
        Returns : (B, num_nodes) — logits over subtype lattice nodes.
        """
        h = self.state_proj(tissue_state)  # (B, hidden)
        # Similarity to each node embedding
        node_embs = self.node_embed.weight  # (num_nodes, hidden)
        logits = torch.mm(h, node_embs.T)  # (B, num_nodes)
        return logits

    def forward(
        self,
        tissue_state: torch.Tensor,
        days_forward: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Predict transition dynamics from current tissue state.

        Parameters
        ----------
        tissue_state : (B, tissue_dim)
        days_forward : (B,) — optional time horizon in days.

        Returns
        -------
        current_subtype_logits : (B, num_nodes)
        transition_probs : (B, num_nodes) — masked by adjacency
        stability_score : (B, 1) — probability of staying stable
        drift_vector : (B, tissue_dim) — predicted manifold movement
        next_tissue_state : (B, tissue_dim) — predicted future state
        """
        B = tissue_state.size(0)
        device = tissue_state.device

        # Current subtype classification
        current_logits = self.get_current_subtype_logits(tissue_state)
        current_probs = F.softmax(current_logits, dim=-1)  # (B, num_nodes)

        # State projection
        h_state = self.state_proj(tissue_state)  # (B, hidden)

        # Weighted node embedding (soft current subtype)
        node_embs = self.node_embed.weight  # (num_nodes, hidden)
        h_node = torch.mm(current_probs, node_embs)  # (B, hidden)

        # Build transition input
        h_input = torch.cat([h_state, h_node], dim=-1)  # (B, 2*hidden)

        if self.use_time and days_forward is not None:
            h_time = self.time_enc(days_forward.to(device))
            h_input = torch.cat([h_input, h_time], dim=-1)
        elif self.use_time:
            # Default: predict 1-year ahead
            default_days = torch.full((B,), 365.0, device=device)
            h_time = self.time_enc(default_days)
            h_input = torch.cat([h_input, h_time], dim=-1)

        # Transition MLP
        h_trans = self.transition_mlp(h_input)  # (B, hidden)

        # Edge transition logits
        raw_logits = self.edge_logit_head(h_trans)  # (B, num_nodes)

        # Mask by adjacency: weighted average over current subtype's adjacency
        adj = self.adj.to(device)  # (num_nodes, num_nodes)
        # Soft adjacency mask: which nodes are reachable from current soft state
        reachable = torch.mm(current_probs, adj)  # (B, num_nodes)
        masked_logits = raw_logits + (reachable.clamp(min=1e-6).log())
        transition_probs = F.softmax(masked_logits, dim=-1)

        # Stability
        stability = torch.sigmoid(self.stability_head(h_trans))

        # Drift vector
        drift = self.drift_head(h_trans)

        # Next state
        next_state = self.next_state_head(h_trans) + tissue_state  # residual

        return {
            "current_subtype_logits": current_logits,
            "current_subtype_probs": current_probs,
            "transition_probs": transition_probs,
            "stability_score": stability,
            "drift_vector": drift,
            "next_tissue_state": next_state,
        }
