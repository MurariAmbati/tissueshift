"""Tissue detection and patch tiling from whole-slide images."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Defaults
PATCH_SIZE = 256
MAGNIFICATION = 20  # 20x
BACKGROUND_THRESHOLD = 0.70  # Discard patches with >70% background
MIN_TISSUE_FRACTION = 0.30


def get_tissue_mask(
    slide_path: str | Path,
    thumbnail_size: tuple[int, int] = (1024, 1024),
    threshold: int | None = None,
) -> tuple[np.ndarray, tuple[int, int]]:
    """Generate tissue mask from WSI thumbnail using Otsu thresholding.

    Returns:
        mask: Binary tissue mask at thumbnail resolution
        dimensions: Original slide dimensions (width, height)
    """
    try:
        import openslide

        slide = openslide.OpenSlide(str(slide_path))
        dimensions = slide.dimensions
        thumbnail = slide.get_thumbnail(thumbnail_size)
        slide.close()
    except ImportError:
        logger.warning("openslide not available, using PIL (limited format support)")
        img = Image.open(slide_path)
        dimensions = img.size
        thumbnail = img.resize(thumbnail_size)

    thumb_array = np.array(thumbnail.convert("RGB"))

    # Convert to grayscale
    gray = np.mean(thumb_array, axis=2).astype(np.uint8)

    # Otsu thresholding
    if threshold is None:
        from scipy import ndimage

        hist, bin_edges = np.histogram(gray, bins=256, range=(0, 256))
        total = gray.size
        sum_total = np.sum(np.arange(256) * hist)

        best_thresh = 0
        best_var = 0
        sum_bg = 0
        weight_bg = 0

        for t in range(256):
            weight_bg += hist[t]
            if weight_bg == 0:
                continue
            weight_fg = total - weight_bg
            if weight_fg == 0:
                break

            sum_bg += t * hist[t]
            mean_bg = sum_bg / weight_bg
            mean_fg = (sum_total - sum_bg) / weight_fg

            var_between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
            if var_between > best_var:
                best_var = var_between
                best_thresh = t

        threshold = best_thresh

    # Tissue is darker than background → invert
    mask = gray < threshold

    # Morphological cleanup
    try:
        from scipy import ndimage as ndi

        mask = ndi.binary_fill_holes(mask)
        mask = ndi.binary_opening(mask, iterations=2)
        mask = ndi.binary_closing(mask, iterations=2)
    except ImportError:
        pass

    return mask.astype(np.uint8), dimensions


def extract_patch_coordinates(
    slide_path: str | Path,
    patch_size: int = PATCH_SIZE,
    magnification: float = MAGNIFICATION,
    min_tissue_fraction: float = MIN_TISSUE_FRACTION,
) -> list[tuple[int, int]]:
    """Extract coordinates of tissue-containing patches from a WSI.

    Returns list of (x, y) top-left coordinates at the target magnification level.
    """
    mask, (slide_w, slide_h) = get_tissue_mask(slide_path)
    mask_h, mask_w = mask.shape

    # Scale factors
    scale_x = mask_w / slide_w
    scale_y = mask_h / slide_h

    coords = []
    for y in range(0, slide_h - patch_size + 1, patch_size):
        for x in range(0, slide_w - patch_size + 1, patch_size):
            # Map patch region to mask coordinates
            mx1 = int(x * scale_x)
            my1 = int(y * scale_y)
            mx2 = int((x + patch_size) * scale_x)
            my2 = int((y + patch_size) * scale_y)

            mx2 = min(mx2, mask_w)
            my2 = min(my2, mask_h)

            if mx2 <= mx1 or my2 <= my1:
                continue

            region = mask[my1:my2, mx1:mx2]
            tissue_fraction = region.mean()

            if tissue_fraction >= min_tissue_fraction:
                coords.append((x, y))

    logger.info(f"Extracted {len(coords)} patch coordinates from {Path(slide_path).name}")
    return coords


def tile_slide(
    slide_path: str | Path,
    output_dir: str | Path,
    patch_size: int = PATCH_SIZE,
    min_tissue_fraction: float = MIN_TISSUE_FRACTION,
    save_patches: bool = False,
) -> Path:
    """Tile a whole-slide image and save patch coordinates.

    Args:
        slide_path: Path to WSI file
        output_dir: Directory for output files
        patch_size: Patch dimensions in pixels
        min_tissue_fraction: Minimum tissue fraction to keep a patch
        save_patches: If True, also save patch images as PNG

    Returns:
        Path to the coordinates CSV file
    """
    slide_path = Path(slide_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    slide_id = slide_path.stem
    coords = extract_patch_coordinates(
        slide_path, patch_size=patch_size, min_tissue_fraction=min_tissue_fraction
    )

    # Save coordinates
    coords_file = output_dir / f"{slide_id}_coords.csv"
    with open(coords_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["x", "y", "patch_size"])
        for x, y in coords:
            writer.writerow([x, y, patch_size])

    # Save thumbnail for QC
    mask, dims = get_tissue_mask(slide_path)
    thumb = Image.fromarray(mask * 255)
    thumb.save(output_dir / f"{slide_id}_tissue_mask.png")

    # Optionally extract and save actual patch images
    if save_patches:
        patches_dir = output_dir / slide_id
        patches_dir.mkdir(exist_ok=True)
        _extract_patch_images(slide_path, coords, patch_size, patches_dir)

    logger.info(
        f"Tiled {slide_id}: {len(coords)} patches → {coords_file}"
    )
    return coords_file


def _extract_patch_images(
    slide_path: Path,
    coords: list[tuple[int, int]],
    patch_size: int,
    output_dir: Path,
) -> None:
    """Extract and save patch images from a WSI."""
    try:
        import openslide

        slide = openslide.OpenSlide(str(slide_path))
        for i, (x, y) in enumerate(coords):
            patch = slide.read_region((x, y), 0, (patch_size, patch_size)).convert("RGB")
            patch.save(output_dir / f"patch_{i:05d}_{x}_{y}.png")
        slide.close()
    except ImportError:
        logger.error("openslide required for patch extraction. Install: pip install openslide-python")


def tile_cohort(
    slides_dir: str | Path,
    output_dir: str | Path,
    patch_size: int = PATCH_SIZE,
    min_tissue_fraction: float = MIN_TISSUE_FRACTION,
    extensions: tuple[str, ...] = (".svs", ".ndpi", ".tif", ".tiff", ".dcm"),
) -> list[Path]:
    """Tile all slides in a directory."""
    slides_dir = Path(slides_dir)
    output_dir = Path(output_dir)

    slide_files = []
    for ext in extensions:
        slide_files.extend(slides_dir.glob(f"*{ext}"))

    logger.info(f"Found {len(slide_files)} slides in {slides_dir}")

    coord_files = []
    for slide_path in sorted(slide_files):
        try:
            cf = tile_slide(
                slide_path, output_dir, patch_size=patch_size,
                min_tissue_fraction=min_tissue_fraction,
            )
            coord_files.append(cf)
        except Exception as e:
            logger.error(f"Failed to tile {slide_path.name}: {e}")

    logger.info(f"Tiled {len(coord_files)}/{len(slide_files)} slides")
    return coord_files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tile whole-slide images")
    parser.add_argument("--slides-dir", required=True, help="Directory containing WSI files")
    parser.add_argument("--output-dir", required=True, help="Output directory for coordinates")
    parser.add_argument("--patch-size", type=int, default=PATCH_SIZE)
    parser.add_argument("--min-tissue", type=float, default=MIN_TISSUE_FRACTION)
    parser.add_argument("--save-patches", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    tile_cohort(args.slides_dir, args.output_dir, args.patch_size, args.min_tissue)
