"""Shared fixtures for TissueShift test suite."""

import pytest

from tissueshift.config import TissueShiftConfig


@pytest.fixture
def small_config():
    """Create a minimal config for fast CPU testing."""
    cfg = TissueShiftConfig()
    cfg.pathology_encoder.patch_embed_dim = 64
    cfg.pathology_encoder.region_embed_dim = 32
    cfg.molecular_encoder.gene_embed_dim = 32
    cfg.molecular_encoder.pathway_embed_dim = 32
    cfg.molecular_encoder.protein_embed_dim = 32
    cfg.molecular_encoder.cnv_embed_dim = 32
    cfg.molecular_encoder.fused_dim = 64
    cfg.molecular_encoder.num_attention_heads = 4
    cfg.molecular_encoder.num_transformer_layers = 1
    cfg.spatial_encoder.node_feature_dim = 16
    cfg.spatial_encoder.hidden_dim = 32
    cfg.spatial_encoder.output_dim = 32
    cfg.spatial_encoder.num_gnn_layers = 2
    cfg.tissue_state.latent_dim = 32
    cfg.tissue_state.num_latent_axes = 8
    cfg.tissue_state.fusion_hidden_dim = 64
    cfg.tissue_state.fusion_num_layers = 1
    cfg.heads.hidden_dim = 32
    cfg.heads.mol_reconstruction_dim = 64
    cfg.heads.microenv_score_dim = 16
    cfg.heads.survival_num_intervals = 5
    cfg.transition.transition_hidden_dim = 32
    return cfg
