"""TissueState: the central world model combining fusion, manifold, and transition."""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn

from world_model.fusion import CrossAttentionFusion, ModalityDropoutFusion
from world_model.manifold import ManifoldProjector
from world_model.transition import SubtypeTransitionModel


@dataclass
class TissueStateOutput:
    """Output of the TissueState world model."""

    state: torch.Tensor            # (B, state_dim) fused tissue state
    manifold_proj: torch.Tensor    # (B, proj_dim) manifold projection (for losses)
    subtype_logits: torch.Tensor   # (B, n_subtypes) subtype classification
    subtype_probs: torch.Tensor    # (B, n_subtypes)
    transition_logits: torch.Tensor  # (B, n_subtypes) next-subtype logits
    transition_probs: torch.Tensor   # (B, n_subtypes)


class TissueStateWorldModel(nn.Module):
    """Central world model: fuse modalities → tissue state → subtype + transition.

    Architecture:
        z_path (512-d) ──┐
        z_mol  (256-d) ──┤── CrossAttentionFusion ── z_state (512-d)
        z_spat (128-d) ──┘        │
                                  ├──▶ ManifoldProjector (for VICReg/contrastive)
                                  └──▶ SubtypeTransitionModel (classification + lattice)
    """

    def __init__(
        self,
        path_dim: int = 512,
        mol_dim: int = 256,
        spat_dim: int = 128,
        state_dim: int = 512,
        proj_dim: int = 256,
        n_subtypes: int = 5,
        n_fusion_queries: int = 8,
        n_fusion_heads: int = 8,
        n_fusion_layers: int = 2,
        modality_dropout: float = 0.15,
        dropout: float = 0.1,
    ):
        super().__init__()

        # Multimodal fusion
        self.fusion = ModalityDropoutFusion(
            path_dim=path_dim,
            mol_dim=mol_dim,
            spat_dim=spat_dim,
            hidden_dim=state_dim,
            n_queries=n_fusion_queries,
            n_heads=n_fusion_heads,
            n_layers=n_fusion_layers,
            dropout=dropout,
            modality_drop_prob=modality_dropout,
        )

        # Manifold projector (for contrastive/VICReg losses)
        self.manifold = ManifoldProjector(
            input_dim=state_dim,
            proj_dim=proj_dim,
        )

        # Transition model (subtype classification + lattice transitions)
        self.transition = SubtypeTransitionModel(
            state_dim=state_dim,
            n_subtypes=n_subtypes,
        )

    @property
    def state_dim(self) -> int:
        return self.fusion.hidden_dim

    def forward(
        self,
        z_path: torch.Tensor,
        z_mol: torch.Tensor,
        z_spat: torch.Tensor,
    ) -> TissueStateOutput:
        """Full forward pass through world model.

        Args:
            z_path: (B, path_dim) pathology embedding
            z_mol: (B, mol_dim) molecular embedding
            z_spat: (B, spat_dim) spatial embedding

        Returns:
            TissueStateOutput with all predictions
        """
        # Fuse modalities
        state = self.fusion(z_path, z_mol, z_spat)

        # Manifold projection (for loss computation)
        manifold_proj = self.manifold(state)

        # Subtype + transition predictions
        trans_out = self.transition(state)

        return TissueStateOutput(
            state=state,
            manifold_proj=manifold_proj,
            subtype_logits=trans_out["subtype_logits"],
            subtype_probs=trans_out["subtype_probs"],
            transition_logits=trans_out["transition_logits"],
            transition_probs=trans_out["transition_probs"],
        )

    def encode(
        self,
        z_path: torch.Tensor,
        z_mol: torch.Tensor,
        z_spat: torch.Tensor,
    ) -> torch.Tensor:
        """Return only the fused tissue state (no heads)."""
        return self.fusion(z_path, z_mol, z_spat)
