"""
TissueShift — Full model assembly.

Wires encoders → tissue-state manifold → prediction heads
into one nn.Module for end-to-end training and inference.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import torch
import torch.nn as nn

from tissueshift.config import TissueShiftConfig
from tissueshift.encoders.pathology_encoder import PathologyEncoder
from tissueshift.encoders.molecular_encoder import MolecularEncoder
from tissueshift.encoders.spatial_encoder import SpatialEncoder
from tissueshift.world_model.tissue_state_model import TissueStateModel
from tissueshift.world_model.transition_model import SubtypeLatticeTransition
from tissueshift.heads.subtype_head import SubtypeHead
from tissueshift.heads.drift_head import DriftHead
from tissueshift.heads.progression_head import ProgressionHead
from tissueshift.heads.morphology_bridge import MorphologyMoleculeBridge
from tissueshift.heads.microenvironment_head import MicroenvironmentHead
from tissueshift.heads.survival_head import SurvivalHead

logger = logging.getLogger(__name__)


class TissueShiftModel(nn.Module):
    """
    TissueShift — Open Temporal Tissue-State Model.

    Four-part system:
      1. Current Tissue State Engine
      2. Subtype Drift Engine
      3. Progression Stage Engine
      4. Morphology-to-Molecule Bridge

    Plus: microenvironment scoring and survival prediction.
    """

    def __init__(self, cfg: TissueShiftConfig):
        super().__init__()
        self.cfg = cfg

        # ---- Encoders ----
        self.pathology_encoder = PathologyEncoder(cfg.pathology_encoder)
        self.molecular_encoder = MolecularEncoder(cfg.molecular_encoder)
        self.spatial_encoder = SpatialEncoder(cfg.spatial_encoder)

        # ---- World Model ----
        self.tissue_state_model = TissueStateModel(
            cfg.tissue_state,
            input_dims={
                "pathology": cfg.pathology_encoder.region_embed_dim,
                "molecular": cfg.molecular_encoder.fused_dim,
                "spatial": cfg.spatial_encoder.output_dim,
            },
        )
        self.transition_model = SubtypeLatticeTransition(
            cfg.transition,
            tissue_dim=cfg.tissue_state.latent_dim,
        )

        # ---- Prediction Heads ----
        latent = cfg.tissue_state.latent_dim
        hidden = cfg.heads.hidden_dim

        self.subtype_head = SubtypeHead(latent, hidden, cfg.heads.dropout)
        self.drift_head = DriftHead(latent, hidden, cfg.heads.subtype_classes, cfg.heads.dropout)
        self.progression_head = ProgressionHead(latent, hidden, cfg.heads.progression_stages, cfg.heads.dropout)
        self.morphology_bridge = MorphologyMoleculeBridge(
            tissue_dim=latent,
            pathology_dim=cfg.pathology_encoder.patch_embed_dim,
            molecular_dim=cfg.molecular_encoder.fused_dim,
            num_pathways=cfg.molecular_encoder.num_pathways,
            hidden_dim=hidden,
            dropout=cfg.heads.dropout,
        )
        self.microenv_head = MicroenvironmentHead(latent, hidden, cfg.heads.dropout)
        self.survival_head = SurvivalHead(
            latent, hidden, cfg.heads.survival_num_intervals, cfg.heads.dropout,
        )

    # ------------------------------------------------------------------
    # Forward
    # ------------------------------------------------------------------
    def forward(
        self,
        tiles: Optional[torch.Tensor] = None,
        tile_mask: Optional[torch.Tensor] = None,
        rna: Optional[torch.Tensor] = None,
        proteomics: Optional[torch.Tensor] = None,
        pathway_scores: Optional[torch.Tensor] = None,
        cnv: Optional[torch.Tensor] = None,
        marker_states: Optional[Dict[str, str]] = None,
        cell_graph: Optional[Dict[str, torch.Tensor]] = None,
        days_forward: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        """
        Full forward pass — any subset of inputs may be provided.

        Returns a dict with all prediction outputs.
        """
        device = next(self.parameters()).device
        outputs: Dict[str, Any] = {}

        # ---- Encode pathology ----
        path_emb = None
        patch_emb = None
        if tiles is not None:
            tiles = tiles.to(device)
            path_out = self.pathology_encoder(tiles, tile_mask)
            path_emb = path_out["slide_embedding"]
            patch_emb = path_out["patch_embeddings"]
            outputs["region_logits"] = path_out["region_logits"]
            outputs["pathology_attention"] = path_out["attention"]

        # ---- Encode molecular ----
        mol_emb = None
        if any(x is not None for x in [rna, proteomics, pathway_scores, cnv, marker_states]):
            mol_out = self.molecular_encoder(
                rna=rna, proteomics=proteomics,
                pathway_scores=pathway_scores, cnv=cnv,
                marker_states=marker_states,
            )
            mol_emb = mol_out["molecular_embedding"]
            if "gene_tokens" in mol_out:
                outputs["gene_tokens"] = mol_out["gene_tokens"]

        # ---- Encode spatial ----
        spatial_emb = None
        if cell_graph is not None:
            spatial_out = self.spatial_encoder.forward_from_dict(cell_graph)
            spatial_emb = spatial_out["spatial_embedding"]
            outputs["spatial_attention"] = spatial_out["attention_weights"]
            outputs["node_embeddings"] = spatial_out["node_embeddings"]

        # ---- Tissue State ----
        state_out = self.tissue_state_model(
            pathology_emb=path_emb,
            molecular_emb=mol_emb,
            spatial_emb=spatial_emb,
        )
        tissue_state = state_out["tissue_state"]
        outputs["tissue_state"] = tissue_state
        outputs["mu"] = state_out["mu"]
        outputs["logvar"] = state_out["logvar"]
        outputs["axes"] = state_out["axes"]

        # ---- Transition Model ----
        trans_out = self.transition_model(tissue_state, days_forward)
        outputs.update({f"transition_{k}": v for k, v in trans_out.items()})

        # ---- Prediction Heads ----
        # 1. Subtype
        subtype_out = self.subtype_head(tissue_state)
        outputs.update({f"subtype_{k}": v for k, v in subtype_out.items()})

        # 2. Drift
        drift_out = self.drift_head(tissue_state)
        outputs.update({f"drift_{k}": v for k, v in drift_out.items()})

        # 3. Progression
        prog_out = self.progression_head(tissue_state)
        outputs.update({f"progression_{k}": v for k, v in prog_out.items()})

        # 4. Morphology-to-Molecule Bridge
        bridge_out = self.morphology_bridge(
            tissue_state, patch_emb, mol_emb,
        )
        outputs.update({f"bridge_{k}": v for k, v in bridge_out.items()})

        # 5. Microenvironment
        micro_out = self.microenv_head(tissue_state)
        outputs.update({f"microenv_{k}": v for k, v in micro_out.items()})

        # 6. Survival
        surv_out = self.survival_head(tissue_state)
        outputs.update({f"survival_{k}": v for k, v in surv_out.items()})

        return outputs

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def predict_tissue_state(self, **kwargs) -> Dict[str, torch.Tensor]:
        """Run forward and return only tissue state + axes."""
        with torch.no_grad():
            out = self.forward(**kwargs)
        return {
            "tissue_state": out["tissue_state"],
            "axes": out["axes"],
            "mu": out["mu"],
        }

    def predict_progression(self, **kwargs) -> Dict[str, torch.Tensor]:
        """Run forward and return progression + drift + subtype."""
        with torch.no_grad():
            out = self.forward(**kwargs)
        return {
            k: v for k, v in out.items()
            if k.startswith(("subtype_", "drift_", "progression_", "transition_"))
        }

    def count_parameters(self) -> Dict[str, int]:
        """Count trainable parameters per component."""
        components = {
            "pathology_encoder": self.pathology_encoder,
            "molecular_encoder": self.molecular_encoder,
            "spatial_encoder": self.spatial_encoder,
            "tissue_state_model": self.tissue_state_model,
            "transition_model": self.transition_model,
            "subtype_head": self.subtype_head,
            "drift_head": self.drift_head,
            "progression_head": self.progression_head,
            "morphology_bridge": self.morphology_bridge,
            "microenv_head": self.microenv_head,
            "survival_head": self.survival_head,
        }
        counts = {}
        for name, module in components.items():
            counts[name] = sum(p.numel() for p in module.parameters() if p.requires_grad)
        counts["total"] = sum(counts.values())
        return counts
