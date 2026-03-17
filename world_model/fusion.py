"""Cross-attention fusion module: merges pathology (z_path), molecular (z_mol),
and spatial (z_spat) into a unified tissue state vector."""

from __future__ import annotations

import torch
import torch.nn as nn


class CrossAttentionFusion(nn.Module):
    """Fuse multimodal embeddings via 8-query cross-attention.

    Learnable fusion queries attend over a set of modality embeddings
    (pathology, molecular, spatial) and produce a fixed-size tissue
    state vector.
    """

    def __init__(
        self,
        path_dim: int = 512,
        mol_dim: int = 256,
        spat_dim: int = 128,
        hidden_dim: int = 512,
        n_queries: int = 8,
        n_heads: int = 8,
        n_layers: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim

        # Project each modality to hidden_dim
        self.path_proj = nn.Linear(path_dim, hidden_dim)
        self.mol_proj = nn.Linear(mol_dim, hidden_dim)
        self.spat_proj = nn.Linear(spat_dim, hidden_dim)

        # Modality type embeddings
        self.modality_embedding = nn.Embedding(3, hidden_dim)  # path=0, mol=1, spat=2

        # Learnable fusion queries
        self.fusion_queries = nn.Parameter(torch.randn(1, n_queries, hidden_dim) * 0.02)

        # Cross-attention layers
        self.cross_attn_layers = nn.ModuleList([
            nn.TransformerDecoderLayer(
                d_model=hidden_dim,
                nhead=n_heads,
                dim_feedforward=hidden_dim * 4,
                dropout=dropout,
                activation="gelu",
                batch_first=True,
                norm_first=True,
            )
            for _ in range(n_layers)
        ])

        # Output projection: pool queries → single vector
        self.output_pool = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(
        self,
        z_path: torch.Tensor,
        z_mol: torch.Tensor,
        z_spat: torch.Tensor,
    ) -> torch.Tensor:
        """Fuse modalities into tissue state.

        Args:
            z_path: (B, path_dim) pathology embedding
            z_mol: (B, mol_dim) molecular embedding
            z_spat: (B, spat_dim) spatial embedding

        Returns:
            z_fused: (B, hidden_dim) tissue state vector
        """
        B = z_path.shape[0]
        device = z_path.device

        # Project all modalities
        h_path = self.path_proj(z_path).unsqueeze(1)  # (B, 1, H)
        h_mol = self.mol_proj(z_mol).unsqueeze(1)     # (B, 1, H)
        h_spat = self.spat_proj(z_spat).unsqueeze(1)  # (B, 1, H)

        # Add modality type embeddings
        mod_ids = torch.arange(3, device=device)
        mod_emb = self.modality_embedding(mod_ids)  # (3, H)
        h_path = h_path + mod_emb[0]
        h_mol = h_mol + mod_emb[1]
        h_spat = h_spat + mod_emb[2]

        # Concatenate modality tokens as memory
        memory = torch.cat([h_path, h_mol, h_spat], dim=1)  # (B, 3, H)

        # Expand fusion queries for batch
        queries = self.fusion_queries.expand(B, -1, -1)  # (B, Q, H)

        # Cross-attention: queries attend to modality tokens
        for layer in self.cross_attn_layers:
            queries = layer(queries, memory)  # (B, Q, H)

        # Pool queries via mean
        z_fused = queries.mean(dim=1)  # (B, H)
        z_fused = self.output_pool(z_fused)  # (B, H)

        return z_fused


class ModalityDropoutFusion(CrossAttentionFusion):
    """Cross-attention fusion with modality dropout during training.

    Randomly drops modalities to make the world model robust to
    missing data (e.g., no proteomics, no spatial data).
    """

    def __init__(self, *args, modality_drop_prob: float = 0.15, **kwargs):
        super().__init__(*args, **kwargs)
        self.modality_drop_prob = modality_drop_prob

    def forward(
        self,
        z_path: torch.Tensor,
        z_mol: torch.Tensor,
        z_spat: torch.Tensor,
    ) -> torch.Tensor:
        if self.training:
            # Randomly zero modalities (never drop pathology and molecular simultaneously)
            if torch.rand(1).item() < self.modality_drop_prob:
                z_spat = torch.zeros_like(z_spat)
            if torch.rand(1).item() < self.modality_drop_prob:
                z_mol = torch.zeros_like(z_mol)

        return super().forward(z_path, z_mol, z_spat)
