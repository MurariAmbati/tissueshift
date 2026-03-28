"""Data augmentation transforms for histopathology and molecular data.

Provides domain-specific augmentations that go beyond standard torchvision
transforms, tailored for H&E-stained tissue images and multi-omics data.
"""

from __future__ import annotations

import math
import random
from typing import Optional, Sequence, Tuple

import numpy as np
import torch
from PIL import Image, ImageEnhance, ImageFilter

try:
    import torchvision.transforms as T
    import torchvision.transforms.functional as TF
except ImportError:
    T = None
    TF = None


# ===================================================================
# Histopathology image augmentations
# ===================================================================

class HistopathologyAugmentation:
    """Composite augmentation pipeline for H&E-stained tissue tiles.

    Applies a randomised sequence of geometric and color transforms
    designed for histopathology images, where orientation and exact
    color are less meaningful than tissue structure.

    Parameters
    ----------
    p_flip : float
        Probability of horizontal/vertical flip.
    p_rotate : float
        Probability of 90°-increment rotation.
    p_color : float
        Probability of color jittering.
    p_blur : float
        Probability of Gaussian blur.
    p_elastic : float
        Probability of elastic deformation.
    color_jitter_strength : float
        Magnitude of H&E-specific color jittering (0–1).
    """

    def __init__(
        self,
        p_flip: float = 0.5,
        p_rotate: float = 0.5,
        p_color: float = 0.7,
        p_blur: float = 0.2,
        p_elastic: float = 0.0,
        color_jitter_strength: float = 0.3,
    ) -> None:
        self.p_flip = p_flip
        self.p_rotate = p_rotate
        self.p_color = p_color
        self.p_blur = p_blur
        self.p_elastic = p_elastic
        self.color_jitter_strength = color_jitter_strength

    def __call__(self, img: Image.Image) -> Image.Image:
        # Horizontal flip
        if random.random() < self.p_flip:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        # Vertical flip
        if random.random() < self.p_flip:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        # 90° rotation
        if random.random() < self.p_rotate:
            k = random.choice([1, 2, 3])
            img = img.rotate(90 * k)
        # Color jitter (H&E-aware)
        if random.random() < self.p_color:
            img = self._he_color_jitter(img)
        # Gaussian blur
        if random.random() < self.p_blur:
            radius = random.uniform(0.5, 1.5)
            img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        # Elastic deformation
        if random.random() < self.p_elastic:
            img = self._elastic_deformation(img)
        return img

    def _he_color_jitter(self, img: Image.Image) -> Image.Image:
        """Apply color jittering tuned for H&E staining variation."""
        s = self.color_jitter_strength
        # Brightness
        factor = random.uniform(max(0, 1 - s), 1 + s)
        img = ImageEnhance.Brightness(img).enhance(factor)
        # Contrast
        factor = random.uniform(max(0, 1 - s), 1 + s)
        img = ImageEnhance.Contrast(img).enhance(factor)
        # Saturation — H&E images vary significantly here
        factor = random.uniform(max(0, 1 - s * 1.5), 1 + s * 1.5)
        img = ImageEnhance.Color(img).enhance(factor)
        # Hue shift — small for H&E
        if TF is not None:
            img_tensor = TF.to_tensor(img)
            img_tensor = TF.adjust_hue(img_tensor, random.uniform(-0.04, 0.04))
            img = TF.to_pil_image(img_tensor)
        return img

    def _elastic_deformation(
        self, img: Image.Image, alpha: float = 50.0, sigma: float = 5.0,
    ) -> Image.Image:
        """Light elastic deformation simulating tissue compression."""
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape[:2]

        dx = np.random.randn(h, w).astype(np.float32)
        dy = np.random.randn(h, w).astype(np.float32)

        # Smooth with Gaussian
        from scipy.ndimage import gaussian_filter
        dx = gaussian_filter(dx, sigma) * alpha
        dy = gaussian_filter(dy, sigma) * alpha

        y, x = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        map_x = np.clip(x + dx, 0, w - 1).astype(np.float32)
        map_y = np.clip(y + dy, 0, h - 1).astype(np.float32)

        from scipy.ndimage import map_coordinates
        channels = []
        for c in range(arr.shape[2]):
            warped = map_coordinates(arr[:, :, c], [map_y.ravel(), map_x.ravel()], order=1)
            channels.append(warped.reshape(h, w))
        result = np.stack(channels, axis=-1).astype(np.uint8)
        return Image.fromarray(result)


class StainAugmentation:
    """Augment H&E stain intensity in the optical-density (OD) domain.

    Randomly perturbs the Hematoxylin and Eosin concentrations to simulate
    inter-lab staining variation, following the approach of Tellez et al.
    (2019) *Quantifying the effects of data augmentation and stain color
    normalization in convolutional neural networks for computational pathology*.

    Parameters
    ----------
    sigma_alpha : float
        Std of multiplicative perturbation on stain matrix columns.
    sigma_beta : float
        Std of additive perturbation on stain concentrations.
    """

    def __init__(self, sigma_alpha: float = 0.2, sigma_beta: float = 0.2) -> None:
        self.sigma_alpha = sigma_alpha
        self.sigma_beta = sigma_beta
        # Reference H&E stain matrix (Ruifrok & Johnston, 2001)
        self._he_ref = np.array([
            [0.6500, 0.7040, 0.2860],  # Hematoxylin
            [0.0720, 0.9900, 0.1050],  # Eosin
        ], dtype=np.float32)

    def __call__(self, img: Image.Image) -> Image.Image:
        arr = np.array(img, dtype=np.float32) / 255.0
        arr = np.clip(arr, 1e-6, 1.0)

        # Convert to OD space
        od = -np.log(arr)

        # Decompose (pseudo-inverse) into stain concentrations
        he = self._he_ref  # (2, 3)
        he_pinv = np.linalg.pinv(he)  # (3, 2)
        flat_od = od.reshape(-1, 3)  # (N, 3)
        concentrations = flat_od @ he_pinv  # (N, 2)

        # Perturb
        alpha = np.random.normal(1.0, self.sigma_alpha, size=(1, 2)).astype(np.float32)
        beta = np.random.normal(0.0, self.sigma_beta, size=(1, 2)).astype(np.float32)
        concentrations = concentrations * alpha + beta

        # Reconstruct
        perturbed_od = concentrations @ he
        perturbed = np.exp(-perturbed_od).reshape(od.shape)
        perturbed = np.clip(perturbed * 255, 0, 255).astype(np.uint8)
        return Image.fromarray(perturbed)


class TileMixUp:
    """MixUp augmentation for batches of tile feature vectors.

    Operates on pre-extracted embeddings rather than raw images.

    Parameters
    ----------
    alpha : float
        Beta distribution parameter for mixing coefficient.
    """

    def __init__(self, alpha: float = 0.4) -> None:
        self.alpha = alpha

    def __call__(
        self,
        features_a: torch.Tensor,
        features_b: torch.Tensor,
        labels_a: torch.Tensor,
        labels_b: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Mix two samples.

        Returns
        -------
        mixed_features : Tensor
        mixed_labels : Tensor (soft)
        """
        lam = np.random.beta(self.alpha, self.alpha)
        mixed_features = lam * features_a + (1 - lam) * features_b
        mixed_labels = lam * labels_a + (1 - lam) * labels_b
        return mixed_features, mixed_labels


class TileCutMix:
    """CutMix for bags of tile features (MIL setting).

    Randomly swaps a fraction of tiles between two bags.

    Parameters
    ----------
    alpha : float
        Beta distribution parameter controlling swap fraction.
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha

    def __call__(
        self,
        bag_a: torch.Tensor,
        bag_b: torch.Tensor,
        label_a: torch.Tensor,
        label_b: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Swap tiles between two bags.

        Parameters
        ----------
        bag_a, bag_b : Tensor of shape (N_tiles, D)
        label_a, label_b : Tensor

        Returns
        -------
        mixed_bag : Tensor
        mixed_label : Tensor (soft)
        """
        lam = np.random.beta(self.alpha, self.alpha)
        n_a = bag_a.shape[0]
        n_swap = max(1, int((1 - lam) * n_a))

        # Random tile indices to replace
        indices = torch.randperm(n_a)[:n_swap]
        # Sample replacement tiles from bag_b
        replace_idx = torch.randint(0, bag_b.shape[0], (n_swap,))

        mixed_bag = bag_a.clone()
        mixed_bag[indices] = bag_b[replace_idx]

        actual_lam = 1.0 - n_swap / n_a
        mixed_label = actual_lam * label_a + (1 - actual_lam) * label_b
        return mixed_bag, mixed_label


# ===================================================================
# Molecular data augmentations
# ===================================================================

class GeneExpressionNoise:
    """Add Gaussian noise to log-normalised gene expression.

    Parameters
    ----------
    sigma : float
        Standard deviation of additive noise.
    p : float
        Probability of applying the augmentation.
    """

    def __init__(self, sigma: float = 0.1, p: float = 0.5) -> None:
        self.sigma = sigma
        self.p = p

    def __call__(self, expression: torch.Tensor) -> torch.Tensor:
        if random.random() > self.p:
            return expression
        noise = torch.randn_like(expression) * self.sigma
        return expression + noise


class GeneDropout:
    """Randomly zero-out a fraction of gene expression values.

    Simulates technical dropout in sequencing / missing genes.

    Parameters
    ----------
    drop_rate : float
        Fraction of genes to zero.
    p : float
        Probability of applying the augmentation.
    """

    def __init__(self, drop_rate: float = 0.1, p: float = 0.5) -> None:
        self.drop_rate = drop_rate
        self.p = p

    def __call__(self, expression: torch.Tensor) -> torch.Tensor:
        if random.random() > self.p:
            return expression
        mask = torch.bernoulli(torch.full_like(expression, 1 - self.drop_rate))
        return expression * mask


class PathwayPerturbation:
    """Perturb pathway activity scores with biologically plausible noise.

    Parameters
    ----------
    sigma : float
        Noise standard deviation.
    p : float
        Probability of applying.
    """

    def __init__(self, sigma: float = 0.15, p: float = 0.5) -> None:
        self.sigma = sigma
        self.p = p

    def __call__(self, pathway_scores: torch.Tensor) -> torch.Tensor:
        if random.random() > self.p:
            return pathway_scores
        noise = torch.randn_like(pathway_scores) * self.sigma
        return pathway_scores + noise


# ===================================================================
# Composite pipelines
# ===================================================================

class TrainAugmentationPipeline:
    """Full training augmentation pipeline combining image and molecular transforms.

    Parameters
    ----------
    image_augment : bool
        Apply histopathology image augmentations.
    stain_augment : bool
        Apply stain-space augmentation.
    molecular_augment : bool
        Apply molecular noise / dropout.
    """

    def __init__(
        self,
        image_augment: bool = True,
        stain_augment: bool = True,
        molecular_augment: bool = True,
        **kwargs,
    ) -> None:
        self.image_transform = HistopathologyAugmentation(**kwargs) if image_augment else None
        self.stain_transform = StainAugmentation() if stain_augment else None
        self.gene_noise = GeneExpressionNoise() if molecular_augment else None
        self.gene_dropout = GeneDropout() if molecular_augment else None
        self.pathway_perturb = PathwayPerturbation() if molecular_augment else None

    def augment_image(self, img: Image.Image) -> Image.Image:
        """Apply image augmentations."""
        if self.stain_transform and random.random() < 0.3:
            img = self.stain_transform(img)
        if self.image_transform:
            img = self.image_transform(img)
        return img

    def augment_expression(self, expr: torch.Tensor) -> torch.Tensor:
        """Apply molecular augmentations to gene expression."""
        if self.gene_noise:
            expr = self.gene_noise(expr)
        if self.gene_dropout:
            expr = self.gene_dropout(expr)
        return expr

    def augment_pathways(self, scores: torch.Tensor) -> torch.Tensor:
        """Apply augmentation to pathway scores."""
        if self.pathway_perturb:
            scores = self.pathway_perturb(scores)
        return scores


class ValAugmentationPipeline:
    """No-op pipeline for validation/test that only applies deterministic preprocessing."""

    def augment_image(self, img: Image.Image) -> Image.Image:
        return img

    def augment_expression(self, expr: torch.Tensor) -> torch.Tensor:
        return expr

    def augment_pathways(self, scores: torch.Tensor) -> torch.Tensor:
        return scores
