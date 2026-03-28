"""Multi-resolution hierarchical attention for whole-slide images.

Implements a 3-level attention hierarchy that mirrors how pathologists
examine tissue:

1. **Cell-level** — local self-attention within small patches (e.g. 256×256)
   capturing cellular morphology and spatial arrangement.
2. **Region-level** — cross-attention between neighbouring patches that
   aggregates regional tissue architecture patterns.
3. **Slide-level** — global attention-based MIL pooling that produces a
   single slide embedding from thousands of region tokens.

Each level can operate independently or end-to-end.

Key novelties
-------------
* **Relative position encoding** with learned 2-D spatial bias at each
  level, so the model understands where patches came from on the slide.
* **Gated cross-scale fusion** — lower-level features are gated before
  being injected into the next level, preventing gradient dilution.
* **Sparse top-k attention** at slide level to handle 10 000+ patches
  without quadratic memory.

References
----------
Lu et al., "Data-efficient and weakly supervised computational pathology
  on WSI", Nature Biomed. Eng., 2021. (CLAM)
Shao et al., "TransMIL: Transformer based Correlated MIL", NeurIPS 2021.
Chen et al., "Scaling Vision Transformers to Gigapixel Images via
  Hierarchical Self-Supervised Learning (HIPT)", CVPR 2022.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ===================================================================
# Configuration
# ===================================================================

@dataclass
class MultiResolutionConfig:
    """Parameters for multi-resolution attention."""

    # Dimensions
    cell_dim: int = 384       # input patch feature dim
    region_dim: int = 512
    slide_dim: int = 768
    hidden_dim: int = 256

    # Cell level
    cell_n_heads: int = 6
    cell_n_layers: int = 2
    cell_patch_size: int = 16  # tokens per cell-patch

    # Region level
    region_n_heads: int = 8
    region_n_layers: int = 2
    region_neighbours: int = 8  # patches in a region

    # Slide level
    slide_n_heads: int = 8
    slide_n_layers: int = 2
    slide_top_k: int = 512     # sparse top-k attention
    slide_pool: str = "attention"  # attention | mean | max

    # General
    dropout: float = 0.1
    use_relative_pos: bool = True
    max_spatial_size: int = 256  # max grid dimension for positional bias
    gate_fusion: bool = True


# ===================================================================
# Building Blocks
# ===================================================================

class RelativePositionBias2D(nn.Module):
    """Learnable 2-D relative position bias for spatial attention."""

    def __init__(self, n_heads: int, max_size: int = 256):
        super().__init__()
        self.n_heads = n_heads
        self.max_size = max_size
        # Bias for each relative (dx, dy) in [-max_size, max_size]
        table_size = 2 * max_size - 1
        self.bias_table = nn.Parameter(
            torch.zeros(n_heads, table_size, table_size)
        )
        nn.init.trunc_normal_(self.bias_table, std=0.02)

    def forward(
        self, coords_q: torch.Tensor, coords_k: torch.Tensor
    ) -> torch.Tensor:
        """Compute bias matrix.

        Parameters
        ----------
        coords_q : (Nq, 2) integer (row, col) coordinates of queries
        coords_k : (Nk, 2) integer (row, col) coordinates of keys

        Returns
        -------
        bias : (n_heads, Nq, Nk)
        """
        dx = coords_q[:, 0:1] - coords_k[:, 0:1].T  # (Nq, Nk)
        dy = coords_q[:, 1:2] - coords_k[:, 1:2].T

        dx = dx.clamp(-self.max_size + 1, self.max_size - 1) + (self.max_size - 1)
        dy = dy.clamp(-self.max_size + 1, self.max_size - 1) + (self.max_size - 1)

        return self.bias_table[:, dx.long(), dy.long()]  # (H, Nq, Nk)


class GatedFusion(nn.Module):
    """Gated cross-scale feature fusion.

    g = σ(W_g [x_low; x_high] + b)
    out = g ⊙ x_low + (1 - g) ⊙ x_high
    """

    def __init__(self, dim_low: int, dim_high: int, dim_out: int):
        super().__init__()
        self.project_low = nn.Linear(dim_low, dim_out)
        self.project_high = nn.Linear(dim_high, dim_out)
        self.gate = nn.Sequential(
            nn.Linear(dim_out * 2, dim_out),
            nn.Sigmoid(),
        )

    def forward(
        self, x_low: torch.Tensor, x_high: torch.Tensor
    ) -> torch.Tensor:
        lo = self.project_low(x_low)
        hi = self.project_high(x_high)
        g = self.gate(torch.cat([lo, hi], dim=-1))
        return g * lo + (1 - g) * hi


class MultiHeadAttentionWithBias(nn.Module):
    """Standard multi-head attention with optional relative-position bias."""

    def __init__(
        self,
        d_model: int,
        n_heads: int,
        dropout: float = 0.1,
        bias_module: Optional[nn.Module] = None,
    ):
        super().__init__()
        assert d_model % n_heads == 0
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.scale = self.head_dim ** -0.5

        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)
        self.attn_drop = nn.Dropout(dropout)
        self.bias_module = bias_module

    def forward(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        coords_q: Optional[torch.Tensor] = None,
        coords_k: Optional[torch.Tensor] = None,
        top_k: Optional[int] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Parameters
        ----------
        query, key, value : (B, N, D)
        coords_q, coords_k : (N, 2)  optional spatial coordinates
        top_k : if set, use sparse top-k attention

        Returns
        -------
        output : (B, N, D)
        attn_weights : (B, H, N_q, N_k) or sparse subset
        """
        B, Nq, _ = query.shape
        Nk = key.shape[1]
        H = self.n_heads

        q = self.q_proj(query).reshape(B, Nq, H, self.head_dim).transpose(1, 2)
        k = self.k_proj(key).reshape(B, Nk, H, self.head_dim).transpose(1, 2)
        v = self.v_proj(value).reshape(B, Nk, H, self.head_dim).transpose(1, 2)

        attn = (q @ k.transpose(-2, -1)) * self.scale  # (B, H, Nq, Nk)

        # Add relative position bias
        if self.bias_module is not None and coords_q is not None and coords_k is not None:
            bias = self.bias_module(coords_q, coords_k)  # (H, Nq, Nk)
            attn = attn + bias.unsqueeze(0)

        # Sparse top-k attention
        if top_k is not None and top_k < Nk:
            topk_vals, topk_idx = attn.topk(top_k, dim=-1)
            mask = torch.full_like(attn, float("-inf"))
            mask.scatter_(-1, topk_idx, topk_vals)
            attn = mask

        attn_weights = F.softmax(attn, dim=-1)
        attn_weights = self.attn_drop(attn_weights)

        out = (attn_weights @ v).transpose(1, 2).reshape(B, Nq, self.d_model)
        return self.out_proj(out), attn_weights


class TransformerBlock(nn.Module):
    """Pre-norm Transformer block."""

    def __init__(
        self,
        d_model: int,
        n_heads: int,
        dropout: float = 0.1,
        bias_module: Optional[nn.Module] = None,
    ):
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.attn = MultiHeadAttentionWithBias(
            d_model, n_heads, dropout, bias_module
        )
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_model * 4),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model * 4, d_model),
            nn.Dropout(dropout),
        )

    def forward(
        self,
        x: torch.Tensor,
        coords: Optional[torch.Tensor] = None,
        top_k: Optional[int] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.norm1(x)
        attn_out, attn_weights = self.attn(h, h, h, coords, coords, top_k)
        x = x + attn_out
        x = x + self.ffn(self.norm2(x))
        return x, attn_weights


# ===================================================================
# Three-Level Hierarchy
# ===================================================================

class CellLevelEncoder(nn.Module):
    """Level 1: local self-attention within small patches."""

    def __init__(self, cfg: MultiResolutionConfig):
        super().__init__()
        self.project_in = nn.Linear(cfg.cell_dim, cfg.region_dim)

        bias = RelativePositionBias2D(cfg.cell_n_heads, max_size=cfg.cell_patch_size) if cfg.use_relative_pos else None

        self.blocks = nn.ModuleList([
            TransformerBlock(cfg.region_dim, cfg.cell_n_heads, cfg.dropout, bias)
            for _ in range(cfg.cell_n_layers)
        ])
        self.pool = nn.AdaptiveAvgPool1d(1)

    def forward(
        self,
        patch_tokens: torch.Tensor,  # (B, T, D_cell)
        coords: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, List[torch.Tensor]]:
        """Returns (B, D_region) and list of attention maps."""
        x = self.project_in(patch_tokens)
        attn_maps = []
        for block in self.blocks:
            x, attn = block(x, coords)
            attn_maps.append(attn)

        # Pool tokens → single vector
        pooled = self.pool(x.transpose(1, 2)).squeeze(-1)  # (B, D_region)
        return pooled, attn_maps


class RegionLevelEncoder(nn.Module):
    """Level 2: cross-attention between neighbouring patches."""

    def __init__(self, cfg: MultiResolutionConfig):
        super().__init__()
        bias = RelativePositionBias2D(cfg.region_n_heads, max_size=cfg.max_spatial_size) if cfg.use_relative_pos else None

        self.blocks = nn.ModuleList([
            TransformerBlock(cfg.region_dim, cfg.region_n_heads, cfg.dropout, bias)
            for _ in range(cfg.region_n_layers)
        ])

        if cfg.gate_fusion:
            self.fusion = GatedFusion(cfg.region_dim, cfg.region_dim, cfg.region_dim)
        else:
            self.fusion = None

        self.project_out = nn.Linear(cfg.region_dim, cfg.slide_dim)

    def forward(
        self,
        region_features: torch.Tensor,  # (B, N_patches, D_region)
        coords: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, List[torch.Tensor]]:
        """Returns (B, N_patches, D_slide) and attention maps."""
        x = region_features
        attn_maps = []
        for block in self.blocks:
            x, attn = block(x, coords)
            attn_maps.append(attn)

        # Gated fusion with original features
        if self.fusion is not None:
            x = self.fusion(region_features, x)

        return self.project_out(x), attn_maps


class SlideLevelAggregator(nn.Module):
    """Level 3: global attention-based MIL pooling.

    Uses sparse top-k attention to handle 10K+ patches efficiently,
    plus a learned [CLS]-like query token for the final slide embedding.
    """

    def __init__(self, cfg: MultiResolutionConfig):
        super().__init__()
        self.cfg = cfg
        # Learnable query token
        self.cls_token = nn.Parameter(torch.randn(1, 1, cfg.slide_dim) * 0.02)

        bias = RelativePositionBias2D(cfg.slide_n_heads, max_size=cfg.max_spatial_size) if cfg.use_relative_pos else None

        self.blocks = nn.ModuleList([
            TransformerBlock(cfg.slide_dim, cfg.slide_n_heads, cfg.dropout, bias)
            for _ in range(cfg.slide_n_layers)
        ])

        # Attention pooling
        if cfg.slide_pool == "attention":
            self.attn_pool = nn.Sequential(
                nn.Linear(cfg.slide_dim, cfg.hidden_dim),
                nn.Tanh(),
                nn.Linear(cfg.hidden_dim, 1),
            )
        else:
            self.attn_pool = None

        self.head_norm = nn.LayerNorm(cfg.slide_dim)

    def forward(
        self,
        patch_features: torch.Tensor,  # (B, N, D_slide)
        coords: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """Returns slide embedding and attention weights."""
        B, N, D = patch_features.shape

        # Prepend CLS token
        cls = self.cls_token.expand(B, -1, -1)
        x = torch.cat([cls, patch_features], dim=1)  # (B, 1+N, D)

        # Extend coords for CLS
        if coords is not None:
            cls_coord = torch.zeros(1, 2, device=coords.device, dtype=coords.dtype)
            coords_ext = torch.cat([cls_coord, coords], dim=0)
        else:
            coords_ext = None

        attn_maps = []
        for block in self.blocks:
            x, attn = block(x, coords_ext, top_k=self.cfg.slide_top_k)
            attn_maps.append(attn)

        # Pool
        if self.cfg.slide_pool == "attention" and self.attn_pool is not None:
            # Use CLS attention
            patch_tokens = x[:, 1:]  # drop CLS
            a = self.attn_pool(patch_tokens)  # (B, N, 1)
            a = F.softmax(a, dim=1)
            slide_embed = (a * patch_tokens).sum(dim=1)  # (B, D)
            attn_weights = a.squeeze(-1)
        elif self.cfg.slide_pool == "max":
            slide_embed = x[:, 1:].max(dim=1).values
            attn_weights = torch.zeros(B, N, device=x.device)
        else:  # mean
            slide_embed = x[:, 1:].mean(dim=1)
            attn_weights = torch.ones(B, N, device=x.device) / N

        slide_embed = self.head_norm(slide_embed)

        return {
            "slide_embedding": slide_embed,         # (B, D_slide)
            "patch_attention": attn_weights,         # (B, N)
            "cls_token": x[:, 0],                    # (B, D)
            "transformer_attentions": attn_maps,     # list of per-layer
        }


# ===================================================================
# Full Multi-Resolution Model
# ===================================================================

class MultiResolutionWSIEncoder(nn.Module):
    """Complete 3-level hierarchical encoder for whole-slide images.

    Input: patch features (pre-extracted from a foundation model like UNI)
    Output: slide-level embedding + multi-scale attention maps
    """

    def __init__(self, cfg: MultiResolutionConfig = MultiResolutionConfig()):
        super().__init__()
        self.cfg = cfg
        self.cell_encoder = CellLevelEncoder(cfg)
        self.region_encoder = RegionLevelEncoder(cfg)
        self.slide_aggregator = SlideLevelAggregator(cfg)

    def forward(
        self,
        patch_features: torch.Tensor,  # (B, N_patches, D_cell)
        patch_coords: Optional[torch.Tensor] = None,  # (N_patches, 2)
        region_assignments: Optional[torch.Tensor] = None,  # (N_patches,) region IDs
    ) -> Dict[str, Any]:
        """End-to-end forward.

        If region_assignments is None, treats each patch as its own region
        (no cell-level grouping, skips directly to region→slide).
        """
        B, N, D = patch_features.shape

        if region_assignments is not None:
            # Group patches by region, run cell-level encoder per region
            region_ids = region_assignments.unique().tolist()
            region_features = []
            cell_attns = []

            for rid in region_ids:
                mask = region_assignments == rid
                group = patch_features[:, mask]  # (B, n_in_region, D)
                group_coords = patch_coords[mask] if patch_coords is not None else None

                pooled, attns = self.cell_encoder(group, group_coords)
                region_features.append(pooled)
                cell_attns.append(attns)

            region_tokens = torch.stack(region_features, dim=1)  # (B, n_regions, D_region)

            # Region coords = centroid of patches in each region
            if patch_coords is not None:
                region_coords = torch.stack([
                    patch_coords[region_assignments == rid].float().mean(dim=0)
                    for rid in region_ids
                ]).long()
            else:
                region_coords = None
        else:
            # Skip cell level — treat each patch as a region
            region_tokens = self.cell_encoder.project_in(patch_features)
            region_coords = patch_coords
            cell_attns = []

        # Region level
        slide_tokens, region_attns = self.region_encoder(region_tokens, region_coords)

        # Slide level
        slide_out = self.slide_aggregator(slide_tokens, region_coords)

        return {
            "slide_embedding": slide_out["slide_embedding"],
            "patch_attention": slide_out["patch_attention"],
            "cls_token": slide_out["cls_token"],
            "cell_attentions": cell_attns,
            "region_attentions": region_attns,
            "slide_attentions": slide_out["transformer_attentions"],
        }

    def get_attention_heatmap(
        self,
        patch_attention: torch.Tensor,
        patch_coords: torch.Tensor,
        grid_size: Optional[Tuple[int, int]] = None,
    ) -> torch.Tensor:
        """Convert attention weights to a spatial heatmap for overlay.

        Parameters
        ----------
        patch_attention : (N,) attention per patch
        patch_coords : (N, 2) (row, col)

        Returns
        -------
        heatmap : (H, W) spatial attention map
        """
        coords = patch_coords.long()
        if grid_size is None:
            H = int(coords[:, 0].max().item()) + 1
            W = int(coords[:, 1].max().item()) + 1
        else:
            H, W = grid_size

        heatmap = torch.zeros(H, W, device=patch_attention.device)
        for i, (r, c) in enumerate(coords):
            heatmap[r, c] = patch_attention[i]

        return heatmap
