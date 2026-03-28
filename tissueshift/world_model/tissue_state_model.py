"""
Shared latent tissue-state manifold.

Fuses pathology, molecular, and spatial embeddings into a single
latent tissue-state representation with interpretable axes:

  lineage_identity        — ER/PR/HER2 lineage programme
  proliferative_pressure  — Ki-67, cell-cycle gene activity
  her2_signaling          — HER2-pathway amplification
  basal_mesenchymal       — basal / EMT tendency
  immune_activation       — TIL density, immune checkpoint
  stromal_permissiveness  — CAF activity, ECM remodelling
  clonal_instability      — CIN / genomic instability proxy
  uncertainty             — epistemic confidence

The manifold is optionally variational (VAE) so that uncertainty
is part of the latent code, not an afterthought.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from tissueshift.config import TissueStateConfig

logger = logging.getLogger(__name__)


class CrossModalAttention(nn.Module):
    """Bi-directional cross-attention between two embedding streams."""

    def __init__(self, dim: int, num_heads: int = 4, dropout: float = 0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(dim, num_heads, dropout=dropout, batch_first=True)
        self.norm = nn.LayerNorm(dim)
        self.ffn = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim * 2, dim),
            nn.Dropout(dropout),
        )
        self.norm2 = nn.LayerNorm(dim)

    def forward(self, query: torch.Tensor, key_value: torch.Tensor) -> torch.Tensor:
        """
        query : (B, 1, D) or (B, T, D)
        key_value : (B, S, D)
        Returns : (B, T, D)
        """
        out, _ = self.attn(query, key_value, key_value)
        out = self.norm(out + query)
        out = self.norm2(out + self.ffn(out))
        return out


class TissueStateModel(nn.Module):
    """
    Shared latent tissue-state model.

    Takes embeddings from pathology, molecular, and spatial encoders
    and produces a fused tissue-state vector on an interpretable manifold.

    The model uses:
      1. Projection of each modality to a common dimension.
      2. Cross-modal attention for modality fusion.
      3. Variational bottleneck for continuous manifold + uncertainty.
      4. Interpretable axis heads that decompose the latent code.
    """

    def __init__(self, cfg: TissueStateConfig, input_dims: Optional[Dict[str, int]] = None):
        super().__init__()
        self.cfg = cfg

        # Default input dims from typical encoder outputs
        dims = input_dims or {
            "pathology": 512,
            "molecular": 512,
            "spatial": 256,
        }

        hidden = cfg.fusion_hidden_dim

        # Per-modality projection to common dim
        self.projections = nn.ModuleDict({
            name: nn.Sequential(
                nn.Linear(d, hidden),
                nn.LayerNorm(hidden),
                nn.GELU(),
            )
            for name, d in dims.items()
        })

        # Modality-type embeddings (learned)
        self.modality_embed = nn.Embedding(len(dims), hidden)

        # Cross-modal attention layers
        self.cross_attn_layers = nn.ModuleList([
            CrossModalAttention(hidden, num_heads=4, dropout=cfg.dropout)
            for _ in range(cfg.fusion_num_layers)
        ])

        # Self-attention over fused tokens
        self_attn_layer = nn.TransformerEncoderLayer(
            d_model=hidden,
            nhead=4,
            dim_feedforward=hidden * 2,
            dropout=cfg.dropout,
            batch_first=True,
            activation="gelu",
        )
        self.self_attn = nn.TransformerEncoder(self_attn_layer, num_layers=2)

        # ---------- Variational bottleneck ----------
        self.use_variational = cfg.use_variational
        self.mu_head = nn.Linear(hidden, cfg.latent_dim)
        self.logvar_head = nn.Linear(hidden, cfg.latent_dim)

        # ---------- Interpretable axis decomposition ----------
        self.axis_heads = nn.ModuleDict({
            name: nn.Linear(cfg.latent_dim, 1)
            for name in cfg.axis_names
        })

        # Final tissue-state projection
        self.state_proj = nn.Sequential(
            nn.Linear(cfg.latent_dim, cfg.latent_dim),
            nn.LayerNorm(cfg.latent_dim),
            nn.GELU(),
        )

    def _reparameterise(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        if self.training and self.use_variational:
            std = (0.5 * logvar).exp()
            eps = torch.randn_like(std)
            return mu + eps * std
        return mu

    def forward(
        self,
        pathology_emb: Optional[torch.Tensor] = None,
        molecular_emb: Optional[torch.Tensor] = None,
        spatial_emb: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Fuse available modality embeddings into tissue state.

        Any subset of modalities can be provided (missing = ignored).

        Returns
        -------
        tissue_state : (B, latent_dim)     — fused latent code
        mu : (B, latent_dim)               — mean (for VAE loss)
        logvar : (B, latent_dim)           — log-variance
        axes : dict of (B, 1) per axis     — interpretable decomposition
        modality_tokens : (B, M, hidden)   — fused per-modality tokens
        """
        device = next(self.parameters()).device
        tokens = []
        mod_idx = 0
        modality_names = list(self.projections.keys())

        embs = {"pathology": pathology_emb, "molecular": molecular_emb, "spatial": spatial_emb}

        for name in modality_names:
            emb = embs.get(name)
            if emb is not None:
                emb = emb.to(device)
                if emb.dim() == 1:
                    emb = emb.unsqueeze(0)
                if emb.dim() == 2:
                    emb = emb.unsqueeze(1)  # (B, 1, D)

                proj = self.projections[name](emb)  # (B, T, hidden)
                # Add modality-type embedding
                type_emb = self.modality_embed(
                    torch.tensor([modality_names.index(name)], device=device)
                ).unsqueeze(0)  # (1, 1, hidden)
                proj = proj + type_emb
                tokens.append(proj)
            mod_idx += 1

        if not tokens:
            B = 1
            z = torch.zeros(B, self.cfg.latent_dim, device=device)
            return {
                "tissue_state": z,
                "mu": z,
                "logvar": z,
                "axes": {name: torch.zeros(B, 1, device=device) for name in self.cfg.axis_names},
                "modality_tokens": torch.zeros(B, 1, self.cfg.fusion_hidden_dim, device=device),
            }

        # Concatenate modality tokens
        fused = torch.cat(tokens, dim=1)  # (B, M, hidden)

        # Cross-modal attention (each token attends to all others)
        for cross_layer in self.cross_attn_layers:
            fused = cross_layer(fused, fused)

        # Self-attention
        fused = self.self_attn(fused)  # (B, M, hidden)

        # Pool to single vector (mean)
        pooled = fused.mean(dim=1)  # (B, hidden)

        # Variational bottleneck
        mu = self.mu_head(pooled)
        logvar = self.logvar_head(pooled)
        z = self._reparameterise(mu, logvar)
        tissue_state = self.state_proj(z)

        # Interpretable axes
        axes = {name: head(tissue_state) for name, head in self.axis_heads.items()}

        return {
            "tissue_state": tissue_state,
            "mu": mu,
            "logvar": logvar,
            "axes": axes,
            "modality_tokens": fused,
        }
