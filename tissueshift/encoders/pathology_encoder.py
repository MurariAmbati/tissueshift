"""
Pathology encoder — patch-level feature extraction + region tokenisation.

Uses a vision backbone (UNI / CTransPath / ImageNet-pretrained ResNet-50)
to embed H&E tiles, then builds region-level tokens for:
  tumor epithelium, stroma, necrosis, immune-rich compartments,
  ductal structures, invasive fronts, lymphovascular patterns.

The output is a slide-level embedding produced via attention pooling
over region-aware patch tokens.
"""

from __future__ import annotations

import logging
import math
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from tissueshift.config import PathologyEncoderConfig

logger = logging.getLogger(__name__)


# ======================================================================
# Attention pooling
# ======================================================================
class GatedAttentionPool(nn.Module):
    """Gated attention MIL pooling (Ilse et al., 2018 variant)."""

    def __init__(self, in_dim: int, hidden_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.attention_V = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.Tanh(),
        )
        self.attention_U = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.Sigmoid(),
        )
        self.attention_w = nn.Linear(hidden_dim, 1)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Parameters
        ----------
        x : (B, N, D)   patch embeddings
        mask : (B, N)    True = valid, False = padding

        Returns
        -------
        pooled : (B, D)
        attention : (B, N)  normalised attention weights
        """
        V = self.attention_V(x)
        U = self.attention_U(x)
        logits = self.attention_w(V * U).squeeze(-1)  # (B, N)

        if mask is not None:
            logits = logits.masked_fill(~mask, float("-inf"))

        attention = F.softmax(logits, dim=-1)  # (B, N)
        attention = self.dropout(attention)
        pooled = torch.bmm(attention.unsqueeze(1), x).squeeze(1)  # (B, D)
        return pooled, attention


# ======================================================================
# Region classifier head
# ======================================================================
class RegionClassifier(nn.Module):
    """Per-patch region type classifier (auxiliary task)."""

    def __init__(self, in_dim: int, num_classes: int, hidden_dim: int = 256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, N, D) → logits: (B, N, C)"""
        return self.net(x)


# ======================================================================
# Backbone wrappers
# ======================================================================
def _build_resnet50(pretrained: bool = True) -> Tuple[nn.Module, int]:
    """ResNet-50 with ImageNet weights, global-avg-pool removed."""
    import torchvision.models as tv
    weights = tv.ResNet50_Weights.DEFAULT if pretrained else None
    model = tv.resnet50(weights=weights)
    feat_dim = model.fc.in_features
    model.fc = nn.Identity()
    return model, feat_dim


def _build_uni_stub(embed_dim: int = 1024) -> Tuple[nn.Module, int]:
    """
    Stub for UNI foundation model.
    
    In production, replace with:
      from uni import UNIModel
      model = UNIModel.from_pretrained(...)
    """
    logger.info("Using UNI stub encoder (replace with real weights for production)")
    model = nn.Sequential(
        nn.Conv2d(3, 64, 7, stride=2, padding=3),
        nn.BatchNorm2d(64),
        nn.ReLU(),
        nn.AdaptiveAvgPool2d(1),
        nn.Flatten(),
        nn.Linear(64, embed_dim),
    )
    return model, embed_dim


def _build_ctranspath_stub(embed_dim: int = 768) -> Tuple[nn.Module, int]:
    """Stub for CTransPath. Replace with real checkpoint in production."""
    logger.info("Using CTransPath stub encoder")
    model = nn.Sequential(
        nn.Conv2d(3, 64, 7, stride=2, padding=3),
        nn.BatchNorm2d(64),
        nn.ReLU(),
        nn.AdaptiveAvgPool2d(1),
        nn.Flatten(),
        nn.Linear(64, embed_dim),
    )
    return model, embed_dim


# ======================================================================
# Main encoder
# ======================================================================
class PathologyEncoder(nn.Module):
    """
    Full pathology encoder pipeline:

    1. Backbone extracts per-tile features.
    2. Region classifier predicts tissue compartment per tile.
    3. Region tokens are formed by attention-pooling tiles
       within each predicted region.
    4. Slide-level embedding via gated attention pooling
       over region tokens.

    Outputs
    -------
    slide_embedding : (B, region_embed_dim)
    patch_embeddings : (B, N, patch_embed_dim)
    region_logits : (B, N, num_regions)  — auxiliary supervision
    attention_weights : (B, N)
    """

    def __init__(self, cfg: PathologyEncoderConfig):
        super().__init__()
        self.cfg = cfg

        # Build backbone
        if cfg.backbone == "uni":
            self.backbone, raw_dim = _build_uni_stub(cfg.patch_embed_dim)
        elif cfg.backbone == "ctranspath":
            self.backbone, raw_dim = _build_ctranspath_stub(cfg.patch_embed_dim)
        else:
            self.backbone, raw_dim = _build_resnet50(cfg.pretrained)

        # Project to patch_embed_dim if necessary
        self.patch_proj = nn.Linear(raw_dim, cfg.patch_embed_dim) if raw_dim != cfg.patch_embed_dim else nn.Identity()

        # Region classifier (auxiliary)
        self.region_clf = RegionClassifier(cfg.patch_embed_dim, cfg.num_region_classes)

        # Region-aware attention pooling
        self.region_pool = GatedAttentionPool(cfg.patch_embed_dim, dropout=cfg.dropout)

        # Final projection to region_embed_dim
        self.slide_proj = nn.Sequential(
            nn.Linear(cfg.patch_embed_dim, cfg.region_embed_dim),
            nn.LayerNorm(cfg.region_embed_dim),
            nn.GELU(),
            nn.Dropout(cfg.dropout),
        )

    def encode_patches(self, tiles: torch.Tensor) -> torch.Tensor:
        """
        Encode raw tiles into patch embeddings.

        Parameters
        ----------
        tiles : (B, N, C, H, W)

        Returns
        -------
        embeddings : (B, N, patch_embed_dim)
        """
        B, N, C, H, W = tiles.shape
        x = tiles.reshape(B * N, C, H, W)

        with torch.no_grad() if not self.training else torch.enable_grad():
            feats = self.backbone(x)  # (B*N, raw_dim)

        feats = self.patch_proj(feats)  # (B*N, patch_embed_dim)
        return feats.reshape(B, N, -1)

    def forward(
        self,
        tiles: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> dict:
        """
        Full forward pass.

        Parameters
        ----------
        tiles : (B, N, C, H, W) — batch of tile stacks
        mask : (B, N) — True for real tiles, False for padding

        Returns
        -------
        dict with keys:
          slide_embedding, patch_embeddings, region_logits, attention
        """
        patch_emb = self.encode_patches(tiles)  # (B, N, D)
        region_logits = self.region_clf(patch_emb)  # (B, N, R)
        pooled, attn = self.region_pool(patch_emb, mask)  # (B, D), (B, N)
        slide_emb = self.slide_proj(pooled)  # (B, region_embed_dim)

        return {
            "slide_embedding": slide_emb,
            "patch_embeddings": patch_emb,
            "region_logits": region_logits,
            "attention": attn,
        }
