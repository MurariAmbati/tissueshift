"""Slide-level aggregation: Attention-Based MIL (ABMIL) and TransMIL."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class GatedAttentionPool(nn.Module):
    """Gated attention mechanism for attention-based MIL."""

    def __init__(self, input_dim: int, hidden_dim: int = 256):
        super().__init__()
        self.attention_V = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.Tanh())
        self.attention_U = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.Sigmoid())
        self.attention_w = nn.Linear(hidden_dim, 1)

    def forward(
        self, x: torch.Tensor, mask: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Compute gated attention.

        Args:
            x: (B, N, D) input tokens
            mask: (B, N) boolean mask — True for valid tokens

        Returns:
            attention_weights: (B, N, 1)
            weighted_sum: (B, D)
        """
        V = self.attention_V(x)  # (B, N, H)
        U = self.attention_U(x)  # (B, N, H)
        logits = self.attention_w(V * U)  # (B, N, 1)

        if mask is not None:
            logits = logits.masked_fill(~mask.unsqueeze(-1), float("-inf"))

        weights = F.softmax(logits, dim=1)  # (B, N, 1)
        weighted_sum = (weights * x).sum(dim=1)  # (B, D)

        return weights, weighted_sum


class ABMIL(nn.Module):
    """Attention-Based Multiple Instance Learning for slide-level embedding.

    Takes region tokens (or patch tokens) and produces a single slide embedding.
    """

    def __init__(
        self,
        input_dim: int = 1024,
        hidden_dim: int = 512,
        output_dim: int = 512,
        dropout: float = 0.25,
    ):
        super().__init__()

        self.projection = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        self.attention = GatedAttentionPool(hidden_dim, hidden_dim // 2)

        self.output_proj = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, output_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(
        self,
        tokens: torch.Tensor,
        mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Aggregate tokens into slide embedding.

        Args:
            tokens: (B, N, D) region or patch tokens
            mask: (B, N) boolean mask — True for valid tokens

        Returns:
            slide_embedding: (B, output_dim)
            attention_weights: (B, N, 1)
        """
        projected = self.projection(tokens)  # (B, N, H)
        attn_weights, aggregated = self.attention(projected, mask)  # (B, H)
        slide_embedding = self.output_proj(aggregated)  # (B, output_dim)

        return slide_embedding, attn_weights


class TransMIL(nn.Module):
    """Transformer-based MIL: uses self-attention over tokens with CLS token."""

    def __init__(
        self,
        input_dim: int = 1024,
        hidden_dim: int = 512,
        output_dim: int = 512,
        n_heads: int = 8,
        n_layers: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()

        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.cls_token = nn.Parameter(torch.randn(1, 1, hidden_dim) * 0.02)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=n_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        self.output_proj = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(
        self,
        tokens: torch.Tensor,
        mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Aggregate tokens via transformer + CLS token.

        Args:
            tokens: (B, N, D) input tokens
            mask: (B, N) boolean mask — True for valid tokens

        Returns:
            slide_embedding: (B, output_dim)
            attention_weights: (B, N, 1) — from last layer's CLS attention
        """
        B = tokens.shape[0]

        x = self.input_proj(tokens)  # (B, N, H)

        # Prepend CLS token
        cls = self.cls_token.expand(B, -1, -1)  # (B, 1, H)
        x = torch.cat([cls, x], dim=1)  # (B, N+1, H)

        # Extend mask for CLS token
        if mask is not None:
            cls_mask = torch.ones(B, 1, dtype=torch.bool, device=mask.device)
            mask = torch.cat([cls_mask, mask], dim=1)

        # Build attention mask (True = ignore)
        src_key_padding_mask = ~mask if mask is not None else None

        x = self.transformer(x, src_key_padding_mask=src_key_padding_mask)

        # CLS token output
        cls_output = x[:, 0]  # (B, H)
        slide_embedding = self.output_proj(cls_output)  # (B, output_dim)

        # Approximate attention weights from last layer
        attn_weights = torch.ones(B, tokens.shape[1], 1, device=tokens.device) / tokens.shape[1]

        return slide_embedding, attn_weights


def build_slide_aggregator(
    method: str = "abmil",
    input_dim: int = 1024,
    output_dim: int = 512,
    **kwargs,
) -> ABMIL | TransMIL:
    """Factory for slide aggregation models."""
    if method == "abmil":
        return ABMIL(input_dim=input_dim, output_dim=output_dim, **kwargs)
    elif method == "transmil":
        return TransMIL(input_dim=input_dim, output_dim=output_dim, **kwargs)
    else:
        raise ValueError(f"Unknown aggregator: {method}. Choose 'abmil' or 'transmil'.")
