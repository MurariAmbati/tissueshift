"""Base dataset interface for TissueShift cohorts."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class CohortInfo:
    """Metadata about a cohort."""

    name: str
    description: str
    n_subjects: int
    access_level: str  # "open", "controlled", "request-based"
    license: str
    data_types: list[str] = field(default_factory=list)
    url: str = ""


class BaseDataset(ABC):
    """Base class for all TissueShift dataset loaders."""

    def __init__(self, data_dir: str | Path, cache_dir: str | Path | None = None):
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir) if cache_dir else self.data_dir / "cache"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def info(self) -> CohortInfo:
        """Return cohort metadata."""

    @abstractmethod
    def get_manifest(self) -> pd.DataFrame:
        """Return the sample manifest with all metadata columns."""

    @abstractmethod
    def download(self, subset: str | None = None) -> None:
        """Download data from the source."""

    def get_splits(self, split_file: str | Path | None = None) -> dict[str, list[str]]:
        """Load train/val/test split. Returns dict with keys 'train', 'val', 'test'."""
        if split_file is None:
            split_file = Path(__file__).parent / "splits" / f"{self.info().name}_splits.json"
        split_file = Path(split_file)
        if not split_file.exists():
            raise FileNotFoundError(
                f"Split file not found: {split_file}. "
                f"Run create_splits() first or provide a split file."
            )
        with open(split_file) as f:
            return json.load(f)

    def create_splits(
        self,
        train_frac: float = 0.70,
        val_frac: float = 0.15,
        stratify_col: str = "pam50_subtype",
        seed: int = 42,
        output_file: str | Path | None = None,
    ) -> dict[str, list[str]]:
        """Create stratified train/val/test splits."""
        from sklearn.model_selection import train_test_split

        manifest = self.get_manifest()
        ids = manifest.index.tolist() if manifest.index.name else manifest.iloc[:, 0].tolist()
        labels = manifest[stratify_col].tolist() if stratify_col in manifest.columns else None

        # First split: train+val vs test
        test_frac = 1.0 - train_frac - val_frac
        train_val_ids, test_ids = train_test_split(
            ids, test_size=test_frac, stratify=labels, random_state=seed
        )

        # Second split: train vs val
        if labels is not None:
            train_val_labels = [
                labels[ids.index(i)] for i in train_val_ids
            ]
        else:
            train_val_labels = None

        relative_val = val_frac / (train_frac + val_frac)
        train_ids, val_ids = train_test_split(
            train_val_ids, test_size=relative_val, stratify=train_val_labels, random_state=seed
        )

        splits = {"train": train_ids, "val": val_ids, "test": test_ids}

        if output_file is None:
            output_file = Path(__file__).parent / "splits" / f"{self.info().name}_splits.json"
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(splits, f, indent=2, default=str)

        return splits

    def __repr__(self) -> str:
        info = self.info()
        return f"{info.name}(n={info.n_subjects}, access={info.access_level})"
