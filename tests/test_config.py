"""Tests for TissueShift configuration system."""

import pytest
from tissueshift.config import (
    TissueShiftConfig,
    DataConfig,
    PathologyEncoderConfig,
    MolecularEncoderConfig,
    SpatialEncoderConfig,
    TissueStateConfig,
    HeadConfig,
    TrainingConfig,
)


class TestDataConfig:
    def test_default_creation(self):
        cfg = DataConfig()
        assert cfg.tile_size == 256
        assert cfg.tile_magnification == 20.0
        assert cfg.stain_norm_method == "macenko"

    def test_invalid_tile_size(self):
        with pytest.raises(ValueError, match="tile_size"):
            DataConfig(tile_size=32)

    def test_invalid_magnification(self):
        with pytest.raises(ValueError, match="tile_magnification"):
            DataConfig(tile_magnification=15.0)

    def test_invalid_stain_method(self):
        with pytest.raises(ValueError, match="stain_norm_method"):
            DataConfig(stain_norm_method="invalid")


class TestPathologyEncoderConfig:
    def test_default_creation(self):
        cfg = PathologyEncoderConfig()
        assert cfg.backbone == "uni"
        assert cfg.dropout == 0.1

    def test_invalid_backbone(self):
        with pytest.raises(ValueError, match="backbone"):
            PathologyEncoderConfig(backbone="vit_huge")

    def test_invalid_dropout(self):
        with pytest.raises(ValueError, match="dropout"):
            PathologyEncoderConfig(dropout=1.5)


class TestMolecularEncoderConfig:
    def test_default_creation(self):
        cfg = MolecularEncoderConfig()
        assert cfg.fused_dim == 512
        assert cfg.num_attention_heads == 8

    def test_fused_dim_not_divisible(self):
        with pytest.raises(ValueError, match="divisible"):
            MolecularEncoderConfig(fused_dim=513, num_attention_heads=8)


class TestSpatialEncoderConfig:
    def test_default_creation(self):
        cfg = SpatialEncoderConfig()
        assert cfg.gnn_type == "gatv2"

    def test_invalid_gnn_type(self):
        with pytest.raises(ValueError, match="gnn_type"):
            SpatialEncoderConfig(gnn_type="transformer")


class TestTissueStateConfig:
    def test_default_creation(self):
        cfg = TissueStateConfig()
        assert cfg.latent_dim == 128
        assert len(cfg.axis_names) == cfg.num_latent_axes

    def test_latent_dim_too_small(self):
        with pytest.raises(ValueError, match="latent_dim"):
            TissueStateConfig(latent_dim=4)

    def test_axis_names_mismatch(self):
        with pytest.raises(ValueError, match="axis_names"):
            TissueStateConfig(num_latent_axes=3, axis_names=("a", "b"))


class TestHeadConfig:
    def test_default_creation(self):
        cfg = HeadConfig()
        assert cfg.subtype_classes == 7
        assert cfg.dropout == 0.1

    def test_invalid_dropout(self):
        with pytest.raises(ValueError, match="dropout"):
            HeadConfig(dropout=-0.1)

    def test_stage_names_mismatch(self):
        with pytest.raises(ValueError, match="stage_names"):
            HeadConfig(progression_stages=3, stage_names=("a", "b"))


class TestTrainingConfig:
    def test_default_creation(self):
        cfg = TrainingConfig()
        assert cfg.optimizer == "adamw"
        assert cfg.scheduler == "cosine"

    def test_invalid_optimizer(self):
        with pytest.raises(ValueError, match="optimizer"):
            TrainingConfig(optimizer="rmsprop")

    def test_invalid_scheduler(self):
        with pytest.raises(ValueError, match="scheduler"):
            TrainingConfig(scheduler="step")

    def test_invalid_stage_epochs(self):
        with pytest.raises(ValueError, match="stage1_epochs"):
            TrainingConfig(stage1_epochs=0)

    def test_invalid_stage_lr(self):
        with pytest.raises(ValueError, match="stage2_lr"):
            TrainingConfig(stage2_lr=-1e-4)


class TestTissueShiftConfig:
    def test_default_creation(self):
        cfg = TissueShiftConfig()
        assert cfg.data.tile_size == 256
        assert cfg.pathology_encoder.backbone == "uni"
        assert cfg.tissue_state.latent_dim == 128

    def test_nested_access(self):
        cfg = TissueShiftConfig()
        assert cfg.heads.subtype_classes == 7
        assert cfg.training.mixed_precision is True
        assert cfg.eval.bootstrap_n == 1000
