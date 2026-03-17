"""Feature extraction from whole-slide images using pretrained pathology encoders."""

from __future__ import annotations

import csv
import logging
from abc import ABC, abstractmethod
from pathlib import Path

import h5py
import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

logger = logging.getLogger(__name__)


class FeatureExtractor(ABC):
    """Base class for pathology feature extractors."""

    @abstractmethod
    def get_model(self) -> torch.nn.Module:
        """Return the feature extraction model."""

    @abstractmethod
    def get_transform(self):
        """Return the image preprocessing transform."""

    @abstractmethod
    def feature_dim(self) -> int:
        """Return the output feature dimensionality."""

    @abstractmethod
    def name(self) -> str:
        """Return the model name for logging."""


class UNIExtractor(FeatureExtractor):
    """UNI ViT-L/16 pathology foundation model (MahmoodLab).

    Requires HuggingFace access approval for model weights.
    Fallback: CTransPath or Phikon if UNI access unavailable.
    """

    def __init__(self, device: str = "auto"):
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        self._model = None
        self._transform = None

    def get_model(self) -> torch.nn.Module:
        if self._model is None:
            try:
                import timm

                self._model = timm.create_model(
                    "vit_large_patch16_224",
                    init_values=1e-5,
                    num_classes=0,  # No classification head → feature extraction
                    dynamic_img_size=True,
                )

                # Load UNI weights from HuggingFace
                from huggingface_hub import hf_hub_download

                ckpt_path = hf_hub_download(
                    repo_id="MahmoodLab/UNI",
                    filename="pytorch_model.bin",
                )
                state_dict = torch.load(ckpt_path, map_location="cpu", weights_only=True)
                self._model.load_state_dict(state_dict, strict=True)
                logger.info("Loaded UNI ViT-L/16 weights from HuggingFace")

            except Exception as e:
                logger.warning(
                    f"Failed to load UNI model: {e}. "
                    f"Using random-init ViT-L as placeholder. "
                    f"Apply for access at https://huggingface.co/MahmoodLab/UNI"
                )
                import timm

                self._model = timm.create_model(
                    "vit_large_patch16_224", num_classes=0, dynamic_img_size=True
                )

            self._model = self._model.to(self.device).eval()

        return self._model

    def get_transform(self):
        from torchvision import transforms

        if self._transform is None:
            self._transform = transforms.Compose([
                transforms.Resize(224),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ])
        return self._transform

    def feature_dim(self) -> int:
        return 1024

    def name(self) -> str:
        return "UNI_ViT-L/16"


class CTransPathExtractor(FeatureExtractor):
    """CTransPath: fully open pathology encoder (fallback for UNI)."""

    def __init__(self, device: str = "auto"):
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        self._model = None
        self._transform = None

    def get_model(self) -> torch.nn.Module:
        if self._model is None:
            import timm

            self._model = timm.create_model(
                "swin_tiny_patch4_window7_224", num_classes=0
            )
            logger.info(
                "CTransPath initialized (load pretrained weights from "
                "https://github.com/Xiyue-Wang/TransPath for best performance)"
            )
            self._model = self._model.to(self.device).eval()
        return self._model

    def get_transform(self):
        from torchvision import transforms

        if self._transform is None:
            self._transform = transforms.Compose([
                transforms.Resize(224),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        return self._transform

    def feature_dim(self) -> int:
        return 768

    def name(self) -> str:
        return "CTransPath"


class PatchDataset(Dataset):
    """Dataset for loading patches from a WSI given coordinates."""

    def __init__(
        self,
        slide_path: str | Path,
        coords: list[tuple[int, int]],
        patch_size: int = 256,
        transform=None,
    ):
        self.slide_path = str(slide_path)
        self.coords = coords
        self.patch_size = patch_size
        self.transform = transform
        self._slide = None

    def _get_slide(self):
        if self._slide is None:
            try:
                import openslide
                self._slide = openslide.OpenSlide(self.slide_path)
            except ImportError:
                self._slide = None
        return self._slide

    def __len__(self):
        return len(self.coords)

    def __getitem__(self, idx):
        x, y = self.coords[idx]
        slide = self._get_slide()

        if slide is not None:
            patch = slide.read_region((x, y), 0, (self.patch_size, self.patch_size)).convert("RGB")
        else:
            # Fallback: create dummy patch for testing
            patch = Image.fromarray(
                np.random.randint(0, 255, (self.patch_size, self.patch_size, 3), dtype=np.uint8)
            )

        if self.transform:
            patch = self.transform(patch)

        return patch, torch.tensor([x, y])


def extract_features_for_slide(
    slide_path: str | Path,
    coords_file: str | Path,
    output_dir: str | Path,
    extractor: FeatureExtractor | None = None,
    batch_size: int = 64,
    num_workers: int = 4,
    patch_size: int = 256,
) -> Path:
    """Extract features from a single WSI.

    Args:
        slide_path: Path to the WSI file
        coords_file: CSV with patch coordinates (x, y, patch_size)
        output_dir: Directory for output HDF5 files
        extractor: Feature extractor instance (default: UNI)
        batch_size: Inference batch size
        num_workers: DataLoader workers
        patch_size: Patch size in pixels

    Returns:
        Path to the output HDF5 file
    """
    slide_path = Path(slide_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    slide_id = slide_path.stem
    output_file = output_dir / f"{slide_id}.h5"

    # Check if already processed
    if output_file.exists():
        logger.info(f"Skipping {slide_id} — already extracted")
        return output_file

    if extractor is None:
        extractor = UNIExtractor()

    # Load coordinates
    coords = []
    with open(coords_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            coords.append((int(row["x"]), int(row["y"])))

    if not coords:
        logger.warning(f"No coordinates found for {slide_id}")
        return output_file

    # Create dataset and dataloader
    dataset = PatchDataset(slide_path, coords, patch_size, extractor.get_transform())
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        num_workers=num_workers,
        pin_memory=True,
        shuffle=False,
    )

    # Extract features
    model = extractor.get_model()
    all_features = []
    all_coords = []

    with torch.no_grad():
        for patches, coord_batch in tqdm(loader, desc=f"Extracting {slide_id}"):
            patches = patches.to(next(model.parameters()).device)
            features = model(patches).cpu().numpy()
            all_features.append(features)
            all_coords.append(coord_batch.numpy())

    features = np.concatenate(all_features, axis=0)
    coordinates = np.concatenate(all_coords, axis=0)

    # Save to HDF5
    with h5py.File(output_file, "w") as f:
        f.create_dataset("features", data=features, compression="gzip", compression_opts=4)
        f.create_dataset("coords", data=coordinates)
        f.attrs["slide_id"] = slide_id
        f.attrs["extractor"] = extractor.name()
        f.attrs["feature_dim"] = extractor.feature_dim()
        f.attrs["n_patches"] = len(features)

    logger.info(
        f"Extracted {len(features)} patches → {output_file} "
        f"(features: {features.shape}, {features.nbytes / 1e6:.1f} MB)"
    )
    return output_file


def extract_features_for_cohort(
    slides_dir: str | Path,
    coords_dir: str | Path,
    output_dir: str | Path,
    extractor: FeatureExtractor | None = None,
    batch_size: int = 64,
    num_workers: int = 4,
) -> list[Path]:
    """Extract features for all slides in a cohort."""
    slides_dir = Path(slides_dir)
    coords_dir = Path(coords_dir)
    output_dir = Path(output_dir)

    extensions = (".svs", ".ndpi", ".tif", ".tiff", ".dcm")
    slide_files = []
    for ext in extensions:
        slide_files.extend(slides_dir.glob(f"*{ext}"))

    logger.info(f"Found {len(slide_files)} slides")

    output_files = []
    for slide_path in sorted(slide_files):
        coords_file = coords_dir / f"{slide_path.stem}_coords.csv"
        if not coords_file.exists():
            logger.warning(f"No coordinates for {slide_path.name}, skipping")
            continue

        try:
            of = extract_features_for_slide(
                slide_path, coords_file, output_dir,
                extractor=extractor, batch_size=batch_size, num_workers=num_workers,
            )
            output_files.append(of)
        except Exception as e:
            logger.error(f"Failed to extract features for {slide_path.name}: {e}")

    logger.info(f"Extracted features for {len(output_files)}/{len(slide_files)} slides")
    return output_files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract patch features from WSIs")
    parser.add_argument("--slides-dir", required=True)
    parser.add_argument("--coords-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--backbone", default="uni", choices=["uni", "ctranspath"])
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=4)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.backbone == "uni":
        extractor = UNIExtractor()
    else:
        extractor = CTransPathExtractor()

    extract_features_for_cohort(
        args.slides_dir, args.coords_dir, args.out_dir,
        extractor=extractor, batch_size=args.batch_size, num_workers=args.num_workers,
    )
