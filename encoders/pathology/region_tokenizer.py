"""Region tokenizer: groups patches by region type and aggregates to region tokens."""

from __future__ import annotations

import math

import torch
import torch.nn as nn


class RegionTokenizer(nn.Module):
    """Groups patches by region label and produces region-level tokens.

    Each region (tumor, stroma, immune, etc.) gets a single token by
    aggregating its constituent patch features via attention pooling.
    Positional information is encoded from spatial coordinates.
    """

    def __init__(
        self,
        feature_dim: int = 1024,
        n_region_types: int = 7,
        pos_encoding: str = "sinusoidal",
        max_coords: int = 100000,
    ):
        super().__init__()
        self.feature_dim = feature_dim
        self.n_region_types = n_region_types

        # Per-region attention pooling
        self.region_attention = nn.ModuleList([
            nn.Sequential(
                nn.Linear(feature_dim, 128),
                nn.Tanh(),
                nn.Linear(128, 1),
            )
            for _ in range(n_region_types)
        ])

        # Region type embedding
        self.region_type_embedding = nn.Embedding(n_region_types, feature_dim)

        # Positional encoding
        self.pos_encoding_type = pos_encoding
        if pos_encoding == "sinusoidal":
            self.pos_proj = nn.Linear(feature_dim, feature_dim)
        elif pos_encoding == "learnable":
            self.pos_embed_x = nn.Embedding(1024, feature_dim // 2)
            self.pos_embed_y = nn.Embedding(1024, feature_dim // 2)

        # Layer norm for output tokens
        self.layer_norm = nn.LayerNorm(feature_dim)

    def _sinusoidal_pos_encoding(self, coords: torch.Tensor) -> torch.Tensor:
        """Generate sinusoidal positional encoding from (x, y) coordinates."""
        batch_has_dim = coords.dim() == 3
        if not batch_has_dim:
            coords = coords.unsqueeze(0)

        B, N, _ = coords.shape
        d = self.feature_dim

        # Normalize coordinates to [0, 1]
        coords_norm = coords.float()
        max_val = coords_norm.abs().max() + 1
        coords_norm = coords_norm / max_val

        # Generate sinusoidal encoding
        pe = torch.zeros(B, N, d, device=coords.device)
        div_term = torch.exp(
            torch.arange(0, d // 2, device=coords.device).float()
            * (-math.log(10000.0) / (d // 2))
        )

        # X coordinates
        pe[:, :, 0::4] = torch.sin(coords_norm[:, :, 0:1] * div_term[: d // 4])
        pe[:, :, 1::4] = torch.cos(coords_norm[:, :, 0:1] * div_term[: d // 4])
        # Y coordinates
        pe[:, :, 2::4] = torch.sin(coords_norm[:, :, 1:2] * div_term[: d // 4])
        pe[:, :, 3::4] = torch.cos(coords_norm[:, :, 1:2] * div_term[: d // 4])

        if not batch_has_dim:
            pe = pe.squeeze(0)

        return pe

    def forward(
        self,
        patch_features: torch.Tensor,
        patch_coords: torch.Tensor,
        region_labels: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Produce region tokens from patches.

        Args:
            patch_features: (B, N, D) patch feature vectors
            patch_coords: (B, N, 2) spatial coordinates
            region_labels: (B, N) integer region label per patch

        Returns:
            region_tokens: (B, R, D) region-level tokens where R = n_region_types
            region_mask: (B, R) boolean mask — True if region has ≥1 patch
        """
        B, N, D = patch_features.shape
        R = self.n_region_types

        # Add positional encoding
        if self.pos_encoding_type == "sinusoidal":
            pos_enc = self._sinusoidal_pos_encoding(patch_coords)
            patch_features = patch_features + self.pos_proj(pos_enc)

        region_tokens = torch.zeros(B, R, D, device=patch_features.device)
        region_mask = torch.zeros(B, R, dtype=torch.bool, device=patch_features.device)

        for r in range(R):
            for b in range(B):
                # Find patches belonging to this region
                mask = region_labels[b] == r
                if mask.sum() == 0:
                    continue

                region_mask[b, r] = True
                region_patches = patch_features[b, mask]  # (K, D)

                # Attention-weighted aggregation
                attn_logits = self.region_attention[r](region_patches)  # (K, 1)
                attn_weights = torch.softmax(attn_logits, dim=0)  # (K, 1)
                aggregated = (attn_weights * region_patches).sum(dim=0)  # (D,)

                # Add region type embedding
                region_tokens[b, r] = aggregated + self.region_type_embedding.weight[r]

        region_tokens = self.layer_norm(region_tokens)
        return region_tokens, region_mask
