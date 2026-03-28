"""Tests for data augmentation transforms."""

import pytest
import numpy as np
import torch
from PIL import Image

from tissueshift.preprocess.augmentation import (
    HistopathologyAugmentation,
    StainAugmentation,
    TileMixUp,
    TileCutMix,
    GeneExpressionNoise,
    GeneDropout,
    PathwayPerturbation,
    TrainAugmentationPipeline,
    ValAugmentationPipeline,
)


@pytest.fixture
def dummy_image():
    """Create a 256×256 RGB image."""
    arr = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    return Image.fromarray(arr)


class TestHistopathologyAugmentation:
    def test_returns_image(self, dummy_image):
        aug = HistopathologyAugmentation()
        result = aug(dummy_image)
        assert isinstance(result, Image.Image)
        assert result.size == dummy_image.size

    def test_no_crash_with_all_augments(self, dummy_image):
        aug = HistopathologyAugmentation(
            p_flip=1.0, p_rotate=1.0, p_color=1.0, p_blur=1.0,
        )
        result = aug(dummy_image)
        assert isinstance(result, Image.Image)


class TestStainAugmentation:
    def test_returns_image(self, dummy_image):
        aug = StainAugmentation()
        result = aug(dummy_image)
        assert isinstance(result, Image.Image)
        assert result.size == dummy_image.size

    def test_output_range(self, dummy_image):
        aug = StainAugmentation(sigma_alpha=0.1, sigma_beta=0.1)
        result = aug(dummy_image)
        arr = np.array(result)
        assert arr.min() >= 0
        assert arr.max() <= 255


class TestTileMixUp:
    def test_shapes(self):
        mixup = TileMixUp(alpha=0.4)
        a = torch.randn(50, 128)
        b = torch.randn(50, 128)
        la = torch.tensor([1.0, 0.0, 0.0])
        lb = torch.tensor([0.0, 1.0, 0.0])
        mixed_f, mixed_l = mixup(a, b, la, lb)
        assert mixed_f.shape == a.shape
        assert mixed_l.shape == la.shape

    def test_labels_are_soft(self):
        mixup = TileMixUp(alpha=0.4)
        la = torch.tensor([1.0, 0.0])
        lb = torch.tensor([0.0, 1.0])
        _, mixed_l = mixup(torch.randn(10, 8), torch.randn(10, 8), la, lb)
        assert torch.allclose(mixed_l.sum(), torch.tensor(1.0))


class TestTileCutMix:
    def test_shapes(self):
        cutmix = TileCutMix(alpha=1.0)
        a = torch.randn(50, 128)
        b = torch.randn(30, 128)
        la = torch.tensor([1.0, 0.0])
        lb = torch.tensor([0.0, 1.0])
        mixed_bag, mixed_l = cutmix(a, b, la, lb)
        assert mixed_bag.shape == a.shape
        assert mixed_l.shape == la.shape


class TestGeneExpressionNoise:
    def test_output_shape(self):
        noise = GeneExpressionNoise(sigma=0.1, p=1.0)
        expr = torch.randn(2000)
        result = noise(expr)
        assert result.shape == expr.shape

    def test_noise_added(self):
        noise = GeneExpressionNoise(sigma=1.0, p=1.0)
        expr = torch.zeros(100)
        result = noise(expr)
        assert not torch.allclose(result, expr)

    def test_no_augment_when_p_zero(self):
        noise = GeneExpressionNoise(sigma=1.0, p=0.0)
        expr = torch.randn(100)
        result = noise(expr)
        assert torch.equal(result, expr)


class TestGeneDropout:
    def test_output_shape(self):
        dropout = GeneDropout(drop_rate=0.3, p=1.0)
        expr = torch.ones(1000)
        result = dropout(expr)
        assert result.shape == expr.shape

    def test_some_zeros(self):
        dropout = GeneDropout(drop_rate=0.5, p=1.0)
        expr = torch.ones(10000)
        result = dropout(expr)
        # With 50% drop rate, many should be zero
        zero_frac = (result == 0).float().mean().item()
        assert 0.3 < zero_frac < 0.7


class TestPathwayPerturbation:
    def test_output_shape(self):
        perturb = PathwayPerturbation(sigma=0.15, p=1.0)
        scores = torch.randn(50)
        result = perturb(scores)
        assert result.shape == scores.shape


class TestTrainAugmentationPipeline:
    def test_image_augment(self, dummy_image):
        pipeline = TrainAugmentationPipeline()
        result = pipeline.augment_image(dummy_image)
        assert isinstance(result, Image.Image)

    def test_expression_augment(self):
        pipeline = TrainAugmentationPipeline()
        expr = torch.randn(2000)
        result = pipeline.augment_expression(expr)
        assert result.shape == expr.shape

    def test_pathway_augment(self):
        pipeline = TrainAugmentationPipeline()
        scores = torch.randn(50)
        result = pipeline.augment_pathways(scores)
        assert result.shape == scores.shape


class TestValAugmentationPipeline:
    def test_no_augmentation(self, dummy_image):
        pipeline = ValAugmentationPipeline()
        result = pipeline.augment_image(dummy_image)
        # Should be identical (no transform)
        assert np.array_equal(np.array(result), np.array(dummy_image))

    def test_expression_passthrough(self):
        pipeline = ValAugmentationPipeline()
        expr = torch.randn(2000)
        result = pipeline.augment_expression(expr)
        assert torch.equal(result, expr)
