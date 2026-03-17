"""Stain normalization for H&E whole-slide images."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class MacenkoNormalizer:
    """Macenko stain normalization for H&E images.

    Reference: Macenko et al., "A method for normalizing histology slides
    for quantitative analysis," ISBI 2009.

    Wraps TIAToolbox StainNormalizer when available, falls back to
    manual implementation.
    """

    def __init__(self):
        self._tia_normalizer = None
        self._reference_stain_matrix = None
        self._reference_concentrations = None
        self._fitted = False

    def fit(self, reference_image: np.ndarray) -> MacenkoNormalizer:
        """Fit normalizer to a reference H&E image.

        Args:
            reference_image: RGB image array (H, W, 3) with values in [0, 255]
        """
        try:
            from tiatoolbox.tools.stainextract import MacenkoExtractor
            from tiatoolbox.tools.stainnorm import MacenkoNormaliser

            self._tia_normalizer = MacenkoNormaliser()
            self._tia_normalizer.fit(reference_image)
            self._fitted = True
            logger.info("Fitted Macenko normalizer using TIAToolbox")
            return self
        except ImportError:
            pass

        # Fallback: manual Macenko implementation
        self._reference_stain_matrix = self._extract_stain_matrix(reference_image)
        ref_od = self._rgb_to_od(reference_image)
        self._reference_concentrations = self._get_concentrations(
            ref_od, self._reference_stain_matrix
        )
        self._ref_max_concentrations = np.percentile(
            self._reference_concentrations, 99, axis=0
        )
        self._fitted = True
        logger.info("Fitted Macenko normalizer (manual implementation)")
        return self

    def transform(self, image: np.ndarray) -> np.ndarray:
        """Normalize an H&E image to the reference stain.

        Args:
            image: RGB image array (H, W, 3) with values in [0, 255]

        Returns:
            Normalized RGB image array
        """
        if not self._fitted:
            raise RuntimeError("Call fit() before transform()")

        if self._tia_normalizer is not None:
            return self._tia_normalizer.transform(image)

        # Manual normalization
        stain_matrix = self._extract_stain_matrix(image)
        od = self._rgb_to_od(image)
        concentrations = self._get_concentrations(od, stain_matrix)

        max_conc = np.percentile(concentrations, 99, axis=0)
        max_conc[max_conc == 0] = 1  # Avoid division by zero

        concentrations *= self._ref_max_concentrations / max_conc

        od_normalized = concentrations @ self._reference_stain_matrix
        normalized = self._od_to_rgb(od_normalized, image.shape)

        return normalized.astype(np.uint8)

    def fit_transform(self, reference: np.ndarray, image: np.ndarray) -> np.ndarray:
        """Fit to reference and transform image in one call."""
        self.fit(reference)
        return self.transform(image)

    @staticmethod
    def _rgb_to_od(image: np.ndarray) -> np.ndarray:
        """Convert RGB image to optical density."""
        image = image.astype(np.float64) + 1  # Avoid log(0)
        od = -np.log(image / 256.0)
        return od.reshape(-1, 3)

    @staticmethod
    def _od_to_rgb(od: np.ndarray, shape: tuple) -> np.ndarray:
        """Convert optical density back to RGB."""
        rgb = 256.0 * np.exp(-od)
        rgb = np.clip(rgb, 0, 255).reshape(shape)
        return rgb

    @staticmethod
    def _extract_stain_matrix(image: np.ndarray) -> np.ndarray:
        """Extract 2x3 stain matrix using SVD on optical density."""
        od = MacenkoNormalizer._rgb_to_od(image)

        # Remove background (low OD)
        od_thresh = od[np.all(od > 0.15, axis=1)]
        if len(od_thresh) < 10:
            od_thresh = od[np.any(od > 0.05, axis=1)]

        if len(od_thresh) < 10:
            # Return default H&E stain matrix if extraction fails
            return np.array([
                [0.6500, 0.7040, 0.2860],
                [0.2680, 0.5700, 0.7760],
            ])

        # SVD
        _, _, vh = np.linalg.svd(od_thresh, full_matrices=False)
        plane = vh[:2, :]

        # Project onto plane and find extreme angles
        projected = od_thresh @ plane.T
        angles = np.arctan2(projected[:, 1], projected[:, 0])

        min_angle = np.percentile(angles, 1)
        max_angle = np.percentile(angles, 99)

        v1 = np.array([np.cos(min_angle), np.sin(min_angle)]) @ plane
        v2 = np.array([np.cos(max_angle), np.sin(max_angle)]) @ plane

        # Enforce H first, E second (H is more blue → higher OD in blue channel)
        if v1[0] > v2[0]:
            stain_matrix = np.array([v1, v2])
        else:
            stain_matrix = np.array([v2, v1])

        # Normalize rows
        stain_matrix /= np.linalg.norm(stain_matrix, axis=1, keepdims=True)
        return stain_matrix

    @staticmethod
    def _get_concentrations(od: np.ndarray, stain_matrix: np.ndarray) -> np.ndarray:
        """Get stain concentrations via least squares."""
        return np.linalg.lstsq(stain_matrix.T, od.T, rcond=None)[0].T


def select_reference_image(
    slides_dir: str | Path, n_samples: int = 50, seed: int = 42
) -> np.ndarray:
    """Select a reference image for stain normalization.

    Selects the slide with median stain characteristics from a
    random sample to use as normalization target.
    """
    import random

    slides_dir = Path(slides_dir)
    slide_files = list(slides_dir.glob("*.svs")) + list(slides_dir.glob("*.tif"))

    rng = random.Random(seed)
    sample = rng.sample(slide_files, min(n_samples, len(slide_files)))

    logger.info(f"Selecting reference from {len(sample)} slides...")

    # For efficiency, use thumbnails
    mean_colors = []
    thumbnails = []
    for sf in sample:
        try:
            img = Image.open(sf)
            thumb = img.resize((512, 512))
            arr = np.array(thumb.convert("RGB"))
            mean_colors.append(arr.mean(axis=(0, 1)))
            thumbnails.append(arr)
        except Exception:
            continue

    if not thumbnails:
        logger.warning("No slides could be read. Returning default reference.")
        return np.ones((256, 256, 3), dtype=np.uint8) * 200

    mean_colors = np.array(mean_colors)
    overall_mean = mean_colors.mean(axis=0)
    distances = np.linalg.norm(mean_colors - overall_mean, axis=1)
    median_idx = np.argmin(distances)

    logger.info(f"Selected reference slide: {sample[median_idx].name}")
    return thumbnails[median_idx]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stain normalization")
    parser.add_argument("--reference", required=True, help="Reference image path")
    parser.add_argument("--input", required=True, help="Input image to normalize")
    parser.add_argument("--output", required=True, help="Output normalized image path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    ref = np.array(Image.open(args.reference).convert("RGB"))
    img = np.array(Image.open(args.input).convert("RGB"))

    normalizer = MacenkoNormalizer()
    normalized = normalizer.fit_transform(ref, img)

    Image.fromarray(normalized).save(args.output)
    logger.info(f"Saved normalized image to {args.output}")
