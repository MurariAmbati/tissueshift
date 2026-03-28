"""Tests for TissueShift model forward passes.

Uses small configs to test that all modules produce expected shapes
without requiring real data or GPU.
"""

import pytest
import torch
from tissueshift.config import TissueShiftConfig



class TestPathologyEncoder:
    def test_forward_shape(self, small_config):
        from tissueshift.encoders.pathology_encoder import PathologyEncoder
        encoder = PathologyEncoder(small_config)
        B, N, D = 2, 10, small_config.pathology_encoder.patch_embed_dim
        tiles = torch.randn(B, N, D)
        out = encoder(tiles)
        assert out.shape == (B, small_config.pathology_encoder.patch_embed_dim)


class TestMolecularEncoder:
    def test_forward_shape(self, small_config):
        from tissueshift.encoders.molecular_encoder import MolecularEncoder
        encoder = MolecularEncoder(small_config)
        B = 2
        batch = {
            "gene_expression": torch.randn(B, small_config.molecular_encoder.gene_vocab_size),
            "pathway_scores": torch.randn(B, small_config.molecular_encoder.num_pathways),
            "cnv_profile": torch.randn(B, 500),
            "marker_status": torch.randn(B, 4),
        }
        out = encoder(batch)
        assert out.shape == (B, small_config.molecular_encoder.fused_dim)


class TestTissueStateModel:
    def test_forward_shape(self, small_config):
        from tissueshift.world_model.tissue_state_model import TissueStateModel
        model = TissueStateModel(small_config)
        B = 2
        modality_embeddings = {
            "pathology": torch.randn(B, small_config.pathology_encoder.patch_embed_dim),
            "molecular": torch.randn(B, small_config.molecular_encoder.fused_dim),
        }
        outputs = model(modality_embeddings)
        assert "z" in outputs
        assert outputs["z"].shape == (B, small_config.tissue_state.latent_dim)
        if small_config.tissue_state.use_variational:
            assert "mu" in outputs
            assert "logvar" in outputs


class TestSubtypeHead:
    def test_forward_shape(self, small_config):
        from tissueshift.heads.subtype_head import SubtypeHead
        head = SubtypeHead(small_config)
        B = 2
        z = torch.randn(B, small_config.tissue_state.latent_dim)
        out = head(z)
        assert "lattice_logits" in out
        assert out["lattice_logits"].shape == (B, small_config.heads.subtype_classes)


class TestDriftHead:
    def test_forward_shape(self, small_config):
        from tissueshift.heads.drift_head import DriftHead
        head = DriftHead(small_config)
        B = 2
        z = torch.randn(B, small_config.tissue_state.latent_dim)
        out = head(z)
        assert "class_logits" in out
        assert out["class_logits"].shape[0] == B


class TestProgressionHead:
    def test_forward_shape(self, small_config):
        from tissueshift.heads.progression_head import ProgressionHead
        head = ProgressionHead(small_config)
        B = 2
        z = torch.randn(B, small_config.tissue_state.latent_dim)
        out = head(z)
        assert "stage_logits" in out
        assert out["stage_logits"].shape == (B, small_config.heads.progression_stages)


class TestSurvivalHead:
    def test_forward_shape(self, small_config):
        from tissueshift.heads.survival_head import SurvivalHead
        head = SurvivalHead(small_config)
        B = 2
        z = torch.randn(B, small_config.tissue_state.latent_dim)
        out = head(z)
        assert "hazards" in out
        assert out["hazards"].shape == (B, small_config.heads.survival_num_intervals)


class TestMicroenvironmentHead:
    def test_forward_shape(self, small_config):
        from tissueshift.heads.microenvironment_head import MicroenvironmentHead
        head = MicroenvironmentHead(small_config)
        B = 2
        z = torch.randn(B, small_config.tissue_state.latent_dim)
        out = head(z)
        assert "overall_score" in out


class TestMorphologyBridge:
    def test_forward_shape(self, small_config):
        from tissueshift.heads.morphology_bridge import MorphologyMoleculeBridge
        head = MorphologyMoleculeBridge(small_config)
        B = 2
        z = torch.randn(B, small_config.tissue_state.latent_dim)
        out = head(z)
        assert "predicted_expression" in out


class TestTransitionModel:
    def test_forward_shape(self, small_config):
        from tissueshift.world_model.transition_model import SubtypeLatticeTransition
        model = SubtypeLatticeTransition(small_config)
        B = 2
        z = torch.randn(B, small_config.tissue_state.latent_dim)
        t = torch.tensor([[365.0], [730.0]])
        out = model(z, t)
        assert "next_state" in out
        assert out["next_state"].shape == (B, small_config.tissue_state.latent_dim)


class TestLoss:
    def test_loss_computes(self, small_config):
        from tissueshift.training.losses import TissueShiftLoss
        loss_fn = TissueShiftLoss(small_config)
        B = 2

        outputs = {
            "subtype": {
                "lattice_logits": torch.randn(B, small_config.heads.subtype_classes),
            },
            "tissue_state": {
                "mu": torch.randn(B, small_config.tissue_state.latent_dim),
                "logvar": torch.randn(B, small_config.tissue_state.latent_dim),
            },
        }
        targets = {
            "subtype_label": torch.randint(0, small_config.heads.subtype_classes, (B,)),
        }

        loss = loss_fn(outputs, targets)
        assert loss.dim() == 0  # scalar
        assert torch.isfinite(loss)
