"""
Stain normalization for H&E whole-slide images.

Supports Macenko, Vahadane, and Reinhard methods via
TIAToolbox or equivalent open-source stain normalization.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class StainNormalizer:
    """
    H&E stain normalisation wrapper.

    Methods
    -------
    fit(reference_image)
        Fit normaliser to a reference H&E image.
    transform(image)
        Normalise an input tile to the reference stain profile.
    """

    SUPPORTED_METHODS = ("macenko", "vahadane", "reinhard")

    def __init__(self, method: str = "macenko"):
        if method not in self.SUPPORTED_METHODS:
            raise ValueError(f"Unknown method {method!r}; choose from {self.SUPPORTED_METHODS}")
        self.method = method
        self._normalizer = None
        self._is_fitted = False
        self._init_backend()

    def _init_backend(self) -> None:
        """Initialise the stain normalisation backend."""
        try:
            from tiatoolbox.tools.stainnorm import (
                MacenkoNormalizer,
                VahadaneNormalizer,
                ReinhardNormalizer,
            )
            backends = {
                "macenko": MacenkoNormalizer,
                "vahadane": VahadaneNormalizer,
                "reinhard": ReinhardNormalizer,
            }
            self._normalizer = backends[self.method]()
            logger.info("Using TIAToolbox %s normalizer", self.method)
        except ImportError:
            logger.warning(
                "TIAToolbox not installed — falling back to basic Reinhard approximation"
            )
            self._normalizer = None

    def fit(self, reference_image: np.ndarray) -> "StainNormalizer":
        """
        Fit to a reference H&E image.

        Parameters
        ----------
        reference_image : np.ndarray
            RGB image, shape (H, W, 3), uint8.
        """
        if self._normalizer is not None:
            self._normalizer.fit(reference_image)
        else:
            # Basic Reinhard: store per-channel mean/std
            self._ref_mean = reference_image.astype(np.float64).mean(axis=(0, 1))
            self._ref_std = reference_image.astype(np.float64).std(axis=(0, 1)) + 1e-6
        self._is_fitted = True
        return self

    def transform(self, image: np.ndarray) -> np.ndarray:
        """
        Normalise *image* to the fitted reference stain.

        Parameters
        ----------
        image : np.ndarray
            RGB tile, shape (H, W, 3), uint8.

        Returns
        -------
        np.ndarray
            Normalised RGB tile, same shape.
        """
        if not self._is_fitted:
            raise RuntimeError("Call .fit(reference_image) before .transform()")

        if self._normalizer is not None:
            return self._normalizer.transform(image)

        # Fallback Reinhard
        img = image.astype(np.float64)
        src_mean = img.mean(axis=(0, 1))
        src_std = img.std(axis=(0, 1)) + 1e-6
        normed = (img - src_mean) / src_std * self._ref_std + self._ref_mean
        return np.clip(normed, 0, 255).astype(np.uint8)

    def fit_transform(self, image: np.ndarray) -> np.ndarray:
        """Fit and transform in one call (self-normalise)."""
        return self.fit(image).transform(image)
