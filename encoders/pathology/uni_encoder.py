"""UNI pathology encoder wrapper for pre-extracted features."""

from __future__ import annotations

import torch
import torch.nn as nn


class UNIEncoder(nn.Module):
    """Wrapper around pre-extracted UNI ViT-L/16 features.

    Takes pre-extracted patch features (N x 1024) and optionally applies
    a learnable adapter (LoRA-style) for domain adaptation.
    """

    def __init__(
        self,
        feature_dim: int = 1024,
        adapter_dim: int | None = None,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.feature_dim = feature_dim

        if adapter_dim is not None:
            # LoRA-style adapter on top of frozen UNI features
            self.adapter = nn.Sequential(
                nn.Linear(feature_dim, adapter_dim),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(adapter_dim, feature_dim),
            )
            # Initialize adapter to near-identity
            nn.init.zeros_(self.adapter[-1].weight)
            nn.init.zeros_(self.adapter[-1].bias)
        else:
            self.adapter = None

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """Process pre-extracted patch features.

        Args:
            features: (batch, n_patches, feature_dim) or (n_patches, feature_dim)

        Returns:
            Processed features with same shape
        """
        if self.adapter is not None:
            return features + self.adapter(features)
        return features
