"""Molecular encoders: expression, pathway, and proteomic embedding networks."""

from __future__ import annotations

import torch
import torch.nn as nn


class ExpressionEncoder(nn.Module):
    """Encode gene expression features (PAM50 + extended panel) into embedding.

    Architecture: 2-layer MLP with residual connection, LayerNorm, GELU.
    """

    def __init__(
        self,
        input_dim: int = 250,
        hidden_dim: int = 256,
        output_dim: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.residual_block = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.output_proj = nn.Linear(hidden_dim, output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Encode expression features.

        Args:
            x: (B, input_dim) gene expression values

        Returns:
            z_expr: (B, output_dim) expression embedding
        """
        h = self.input_proj(x)
        h = h + self.residual_block(h)
        return self.output_proj(h)


class PathwayEncoder(nn.Module):
    """Encode pathway activity scores into embedding."""

    def __init__(
        self,
        input_dim: int = 50,
        output_dim: int = 128,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, output_dim),
            nn.LayerNorm(output_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Encode pathway scores.

        Args:
            x: (B, input_dim) pathway activity scores

        Returns:
            z_pathway: (B, output_dim) pathway embedding
        """
        return self.net(x)


class ProteomicEncoder(nn.Module):
    """Encode proteomic abundance data into embedding.

    Handles missing modality via learnable mask token.
    """

    def __init__(
        self,
        input_dim: int = 200,
        hidden_dim: int = 256,
        output_dim: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.mask_token = nn.Parameter(torch.randn(output_dim) * 0.02)

        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
            nn.LayerNorm(output_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(
        self, x: torch.Tensor | None, available: torch.Tensor | None = None
    ) -> torch.Tensor:
        """Encode proteomic data, handling missing modality.

        Args:
            x: (B, input_dim) protein abundances, or None
            available: (B,) boolean — True if proteomic data available for this sample

        Returns:
            z_prot: (B, output_dim) proteomic embedding
        """
        if x is None:
            # All samples missing — return mask tokens
            B = available.shape[0] if available is not None else 1
            return self.mask_token.unsqueeze(0).expand(B, -1)

        encoded = self.net(x)  # (B, output_dim)

        if available is not None:
            # Replace missing samples with mask token
            mask = ~available.unsqueeze(-1)  # (B, 1)
            encoded = torch.where(mask, self.mask_token.unsqueeze(0), encoded)

        return encoded


class MolecularEncoder(nn.Module):
    """Combined molecular encoder: expression + pathway + proteomics.

    Concatenates sub-encodings and projects to final molecular embedding.
    Supports modality dropout during training.
    """

    def __init__(
        self,
        expression_dim: int = 250,
        pathway_dim: int = 50,
        proteomic_dim: int = 200,
        expr_embed_dim: int = 256,
        pathway_embed_dim: int = 128,
        prot_embed_dim: int = 256,
        output_dim: int = 256,
        modality_dropout: float = 0.5,
        dropout: float = 0.1,
    ):
        super().__init__()

        self.expression_encoder = ExpressionEncoder(
            expression_dim, expr_embed_dim, expr_embed_dim, dropout
        )
        self.pathway_encoder = PathwayEncoder(pathway_dim, pathway_embed_dim, dropout)
        self.proteomic_encoder = ProteomicEncoder(
            proteomic_dim, prot_embed_dim, prot_embed_dim, dropout
        )

        total_dim = expr_embed_dim + pathway_embed_dim + prot_embed_dim
        self.fusion_proj = nn.Sequential(
            nn.Linear(total_dim, output_dim),
            nn.LayerNorm(output_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        self.modality_dropout = modality_dropout
        self.modality_present_proj = nn.Linear(3, output_dim)  # 3 modality flags

    def forward(
        self,
        expression: torch.Tensor | None = None,
        pathway_scores: torch.Tensor | None = None,
        protein: torch.Tensor | None = None,
        protein_available: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Encode all molecular modalities.

        Args:
            expression: (B, expr_dim) gene expression
            pathway_scores: (B, pathway_dim) pathway activity scores
            protein: (B, prot_dim) proteomic data
            protein_available: (B,) boolean — True if proteomics available

        Returns:
            z_mol: (B, output_dim) molecular embedding
        """
        B = (
            expression.shape[0]
            if expression is not None
            else (protein.shape[0] if protein is not None else 1)
        )
        device = (
            expression.device
            if expression is not None
            else (protein.device if protein is not None else torch.device("cpu"))
        )

        # Modality dropout during training
        if self.training and self.modality_dropout > 0:
            if protein is not None and torch.rand(1).item() < self.modality_dropout:
                protein_available = torch.zeros(B, dtype=torch.bool, device=device)

        # Encode each modality
        if expression is not None:
            z_expr = self.expression_encoder(expression)
        else:
            z_expr = torch.zeros(B, self.expression_encoder.output_proj.out_features, device=device)

        if pathway_scores is not None:
            z_path = self.pathway_encoder(pathway_scores)
        else:
            z_path = torch.zeros(B, self.pathway_encoder.net[0].out_features, device=device)

        z_prot = self.proteomic_encoder(protein, protein_available)

        # Concatenate and project
        z_cat = torch.cat([z_expr, z_path, z_prot], dim=-1)
        z_mol = self.fusion_proj(z_cat)

        # Add modality-presence signal
        modality_flags = torch.stack([
            torch.ones(B, device=device) if expression is not None else torch.zeros(B, device=device),
            torch.ones(B, device=device) if pathway_scores is not None else torch.zeros(B, device=device),
            protein_available.float() if protein_available is not None else torch.zeros(B, device=device),
        ], dim=-1)  # (B, 3)
        z_mol = z_mol + self.modality_present_proj(modality_flags)

        return z_mol
