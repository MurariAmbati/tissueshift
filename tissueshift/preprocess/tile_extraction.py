"""
Tile extraction from whole-slide images.

Extracts tissue-containing tiles at a target magnification,
applies tissue detection to skip background, and optionally
applies stain normalisation on-the-fly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import torch

from tissueshift.config import TissueShiftConfig
from tissueshift.preprocess.stain_normalization import StainNormalizer

logger = logging.getLogger(__name__)


class TileExtractor:
    """
    Extract tiles from whole-slide images using OpenSlide or TIAToolbox.

    Tiles are saved as individual .pt tensors organised by case_id.
    """

    def __init__(
        self,
        cfg: TissueShiftConfig,
        stain_normalizer: Optional[StainNormalizer] = None,
    ):
        self.cfg = cfg
        self.tile_size = cfg.data.tile_size
        self.magnification = cfg.data.tile_magnification
        self.overlap = cfg.data.tile_overlap
        self.max_tiles = cfg.data.max_tiles_per_slide
        self.stain_normalizer = stain_normalizer

    # ------------------------------------------------------------------
    # Tissue detection
    # ------------------------------------------------------------------
    @staticmethod
    def _tissue_mask(thumbnail: np.ndarray, threshold: int = 220) -> np.ndarray:
        """
        Simple tissue detection on a low-res thumbnail.

        Converts to grayscale, thresholds, and returns a binary mask
        where True = tissue.
        """
        gray = np.mean(thumbnail, axis=2)
        mask = gray < threshold
        return mask

    @staticmethod
    def _get_tissue_coords(
        mask: np.ndarray, tile_size: int, downsample: float
    ) -> List[Tuple[int, int]]:
        """Return (x, y) top-left coords at full resolution for each tissue tile."""
        step = int(tile_size * downsample)
        coords = []
        h, w = mask.shape
        for y in range(0, h, max(1, int(tile_size / downsample))):
            for x in range(0, w, max(1, int(tile_size / downsample))):
                if mask[y, x]:
                    coords.append((int(x * downsample), int(y * downsample)))
        return coords

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------
    def extract_slide(
        self,
        slide_path: Path,
        output_dir: Path,
    ) -> int:
        """
        Extract tiles from one slide and save as .pt files.

        Returns number of tiles extracted.
        """
        try:
            import openslide
        except ImportError:
            logger.error("openslide-python not installed — cannot extract tiles")
            return 0

        output_dir.mkdir(parents=True, exist_ok=True)
        slide = openslide.OpenSlide(str(slide_path))

        # Find appropriate level
        target_mpp = 10.0 / self.magnification  # approximate
        best_level = 0
        best_downsample = slide.level_downsamples[0]
        for lvl, ds in enumerate(slide.level_downsamples):
            if ds <= 32:
                best_level = lvl
                best_downsample = ds

        # Thumbnail for tissue detection
        thumb_size = (
            max(1, int(slide.dimensions[0] / best_downsample / 4)),
            max(1, int(slide.dimensions[1] / best_downsample / 4)),
        )
        thumbnail = np.array(slide.get_thumbnail(thumb_size).convert("RGB"))
        mask = self._tissue_mask(thumbnail)

        # Get tissue coordinates
        coords = self._get_tissue_coords(mask, self.tile_size, best_downsample * 4)
        if len(coords) > self.max_tiles:
            rng = np.random.RandomState(42)
            chosen = rng.choice(len(coords), self.max_tiles, replace=False)
            coords = [coords[i] for i in chosen]

        # Extract and save tiles
        count = 0
        for i, (x, y) in enumerate(coords):
            try:
                region = slide.read_region((x, y), 0, (self.tile_size, self.tile_size))
                tile = np.array(region.convert("RGB"))

                # Stain normalisation
                if self.stain_normalizer is not None:
                    tile = self.stain_normalizer.transform(tile)

                # Convert to tensor (C, H, W), float32 [0, 1]
                tensor = torch.from_numpy(tile).permute(2, 0, 1).float() / 255.0
                torch.save(tensor, output_dir / f"tile_{i:05d}.pt")
                count += 1
            except Exception as e:
                logger.debug("Skipping tile at (%d, %d): %s", x, y, e)

        slide.close()
        logger.info(
            "Extracted %d tiles from %s → %s", count, slide_path.name, output_dir,
        )
        return count

    def extract_cohort(
        self,
        slides_dir: Path,
        output_root: Path,
    ) -> int:
        """
        Extract tiles for all slides in a directory.

        Returns total number of tiles extracted.
        """
        total = 0
        slide_paths = sorted(
            list(slides_dir.glob("*.svs")) +
            list(slides_dir.glob("*.ndpi")) +
            list(slides_dir.glob("*.tiff"))
        )
        logger.info("Found %d slides in %s", len(slide_paths), slides_dir)

        for slide_path in slide_paths:
            case_id = slide_path.stem.split(".")[0][:12]
            out = output_root / case_id
            total += self.extract_slide(slide_path, out)

        return total
