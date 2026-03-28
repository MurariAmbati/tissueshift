"""
Morphology-to-Molecule Bridge.

Predicts which pathways, markers, and latent programmes are being
expressed based on what the pathologist sees, then maps tissue
regions back to those molecular programmes.

This is the fourth part of TissueShift: the bridge between tissue
morphology and molecular identity.
"""

from __future__ import annotations

from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class MorphologyMoleculeBridge(nn.Module):
    """
    Bi-directional bridge between morphology and molecular space.

    pathology_emb → predicted molecular programme
    molecular_emb → predicted morphological features

    Also localises: given patch embeddings, predicts per-patch
    pathway activity for spatial explanation.

    Outputs
    -------
    predicted_pathways : (B, num_pathways) — pathway activity from morphology
    predicted_expression : (B, mol_dim) — expression profile from morphology
    patch_pathway_scores : (B, N, num_pathways) — per-tile pathway activity
    reconstruction_loss_ready : (B, mol_dim) — for self-supervised training
    """

    def __init__(
        self,
        tissue_dim: int = 128,
        pathology_dim: int = 512,
        molecular_dim: int = 512,
        num_pathways: int = 50,
        hidden_dim: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()

        # Tissue state → molecular programme
        self.tissue_to_mol = nn.Sequential(
            nn.Linear(tissue_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, molecular_dim),
        )

        # Tissue state → pathway activity
        self.tissue_to_pathway = nn.Sequential(
            nn.Linear(tissue_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, num_pathways),
        )

        # Per-patch pathway localisation
        self.patch_to_pathway = nn.Sequential(
            nn.Linear(pathology_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, num_pathways),
        )

        # Reverse: molecular → predicted morphology features
        self.mol_to_morph = nn.Sequential(
            nn.Linear(molecular_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, pathology_dim),
        )

    def forward(
        self,
        tissue_state: torch.Tensor,
        patch_embeddings: Optional[torch.Tensor] = None,
        molecular_embedding: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        out: Dict[str, torch.Tensor] = {}

        # Morphology → molecule prediction
        out["predicted_expression"] = self.tissue_to_mol(tissue_state)
        out["predicted_pathways"] = self.tissue_to_pathway(tissue_state)

        # Per-patch pathway localisation
        if patch_embeddings is not None:
            out["patch_pathway_scores"] = self.patch_to_pathway(patch_embeddings)

        # Reverse bridge
        if molecular_embedding is not None:
            out["predicted_morphology"] = self.mol_to_morph(molecular_embedding)

        return out
