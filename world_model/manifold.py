"""Manifold learning: contrastive + VICReg regularization for tissue state space."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class ManifoldProjector(nn.Module):
    """Projects tissue state into manifold embedding space.

    Used for contrastive/VICReg training to learn a structured
    tissue state manifold where subtypes form coherent regions.
    """

    def __init__(
        self,
        input_dim: int = 512,
        proj_dim: int = 256,
        hidden_dim: int = 512,
    ):
        super().__init__()
        # Projector head (detached during downstream inference)
        self.projector = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, proj_dim),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """Project tissue state for manifold loss.

        Args:
            z: (B, input_dim) tissue state vector

        Returns:
            p: (B, proj_dim) manifold projection
        """
        return self.projector(z)


class VICRegLoss(nn.Module):
    """Variance-Invariance-Covariance Regularization (VICReg).

    Ensures the manifold has:
    - Variance: each dimension has sufficient spread (no collapse)
    - Invariance: augmented views of same sample stay close
    - Covariance: embedding dimensions are decorrelated
    """

    def __init__(
        self,
        sim_weight: float = 25.0,
        var_weight: float = 25.0,
        cov_weight: float = 1.0,
        var_eps: float = 1e-4,
        target_std: float = 1.0,
    ):
        super().__init__()
        self.sim_weight = sim_weight
        self.var_weight = var_weight
        self.cov_weight = cov_weight
        self.var_eps = var_eps
        self.target_std = target_std

    def forward(self, z1: torch.Tensor, z2: torch.Tensor) -> dict[str, torch.Tensor]:
        """Compute VICReg loss between two views.

        Args:
            z1, z2: (B, D) projected embeddings from two augmented views

        Returns:
            Dictionary with total loss and individual terms
        """
        # Invariance: MSE between paired views
        sim_loss = F.mse_loss(z1, z2)

        # Variance: hinge loss to keep std above target
        std_z1 = torch.sqrt(z1.var(dim=0) + self.var_eps)
        std_z2 = torch.sqrt(z2.var(dim=0) + self.var_eps)
        var_loss = (
            F.relu(self.target_std - std_z1).mean()
            + F.relu(self.target_std - std_z2).mean()
        )

        # Covariance: off-diagonal of covariance matrix
        z1_centered = z1 - z1.mean(dim=0)
        z2_centered = z2 - z2.mean(dim=0)
        N = z1.shape[0]
        D = z1.shape[1]

        cov_z1 = (z1_centered.T @ z1_centered) / (N - 1)
        cov_z2 = (z2_centered.T @ z2_centered) / (N - 1)

        # Zero diagonal and compute mean squared off-diagonal
        cov_loss = (
            _off_diagonal(cov_z1).pow(2).sum() / D
            + _off_diagonal(cov_z2).pow(2).sum() / D
        )

        total = (
            self.sim_weight * sim_loss
            + self.var_weight * var_loss
            + self.cov_weight * cov_loss
        )

        return {
            "loss": total,
            "invariance": sim_loss,
            "variance": var_loss,
            "covariance": cov_loss,
        }


class SubtypeContrastiveLoss(nn.Module):
    """Supervised contrastive loss with subtype labels.

    Pulls same-subtype samples together, pushes different subtypes apart,
    with soft margins for subtypes that are biologically similar.
    """

    # Biological similarity between PAM50 subtypes (dissimilarity = distance)
    SUBTYPE_DISTANCES = {
        ("LumA", "LumB"): 0.3,   # luminal neighbors
        ("LumB", "Her2"): 0.6,
        ("Her2", "Basal"): 0.8,
        ("LumA", "Normal"): 0.5,
        ("LumB", "Basal"): 0.9,
        ("LumA", "Her2"): 0.7,
        ("LumA", "Basal"): 1.0,
        ("LumB", "Normal"): 0.6,
        ("Her2", "Normal"): 0.7,
        ("Basal", "Normal"): 0.8,
    }

    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature

    def forward(
        self, features: torch.Tensor, labels: torch.Tensor
    ) -> torch.Tensor:
        """Supervised contrastive loss.

        Args:
            features: (B, D) L2-normalized features
            labels: (B,) integer subtype labels

        Returns:
            Scalar contrastive loss
        """
        features = F.normalize(features, dim=1)
        B = features.shape[0]

        # Similarity matrix
        sim = features @ features.T / self.temperature  # (B, B)

        # Positive mask: same label pairs
        labels_eq = labels.unsqueeze(0) == labels.unsqueeze(1)  # (B, B)
        # Remove self-pairs
        self_mask = ~torch.eye(B, dtype=torch.bool, device=labels.device)
        pos_mask = labels_eq & self_mask

        # Log-sum-exp for stability
        logits_max = sim.max(dim=1, keepdim=True).values
        logits = sim - logits_max.detach()

        # Exclude self
        exp_logits = torch.exp(logits) * self_mask.float()
        log_prob = logits - torch.log(exp_logits.sum(dim=1, keepdim=True) + 1e-8)

        # Mean of positives
        n_positives = pos_mask.sum(dim=1).clamp(min=1)
        loss = -(pos_mask.float() * log_prob).sum(dim=1) / n_positives

        return loss.mean()


def _off_diagonal(x: torch.Tensor) -> torch.Tensor:
    """Extract off-diagonal elements of a square matrix."""
    n = x.shape[0]
    return x.flatten()[:-1].view(n - 1, n + 1)[:, 1:].flatten()
