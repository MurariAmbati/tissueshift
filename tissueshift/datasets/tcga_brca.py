"""
TCGA-BRCA dataset loader.

Sources: Imaging Data Commons (IDC) for slides and image analyses,
GDC for clinical/genomic open-access data.

IDC exposes 1,098 TCGA-BRCA subjects with clinical, genomic,
image-analysis, and histopathology support including nuclei
segmentations and TIL maps.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from tissueshift.config import TissueShiftConfig

logger = logging.getLogger(__name__)


class TCGABRCADataset(Dataset):
    """
    TCGA-BRCA cohort loader.

    Provides slide-level pathology tiles, RNA-seq expression,
    CNV profiles, PAM50 intrinsic subtype labels, clinical
    annotations, and derived image-analysis features.
    """

    # PAM50 intrinsic subtypes
    SUBTYPES = ("LumA", "LumB", "Her2", "Basal", "Normal")
    SUBTYPE_TO_IDX = {s: i for i, s in enumerate(SUBTYPES)}

    # Clinical subtype (IHC-based)
    IHC_SUBTYPES = ("HR+/HER2-", "HR+/HER2+", "HR-/HER2+", "TNBC")

    def __init__(
        self,
        cfg: TissueShiftConfig,
        split: str = "train",
        modalities: Tuple[str, ...] = ("pathology", "rna", "clinical"),
        transform=None,
        tile_cache_dir: Optional[Path] = None,
    ):
        super().__init__()
        self.cfg = cfg
        self.split = split
        self.modalities = modalities
        self.transform = transform
        self.tile_cache_dir = tile_cache_dir or cfg.data.tcga_brca_slides_dir / "tiles"

        # Load clinical annotations
        self.clinical = self._load_clinical()

        # Apply split
        self.samples = self._split_samples()

        # Lazy-load molecular data
        self._rna_df: Optional[pd.DataFrame] = None
        self._cnv_df: Optional[pd.DataFrame] = None

        logger.info(
            "TCGABRCADataset [%s]: %d samples, modalities=%s",
            split, len(self.samples), modalities,
        )

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------
    def _load_clinical(self) -> pd.DataFrame:
        """Load and parse TCGA-BRCA clinical TSV."""
        clin_path = self.cfg.data.tcga_brca_clinical
        if not clin_path.exists():
            logger.warning("Clinical file not found: %s — using empty frame", clin_path)
            return pd.DataFrame(columns=[
                "case_id", "pam50_subtype", "ihc_subtype",
                "er_status", "pr_status", "her2_status",
                "pathologic_stage", "age_at_diagnosis",
                "vital_status", "days_to_last_follow_up",
                "days_to_death", "race", "ethnicity",
            ])

        df = pd.read_csv(clin_path, sep="\t", low_memory=False)
        # Normalize column names
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        return df

    def _split_samples(self) -> List[Dict[str, Any]]:
        """
        Deterministic 70/15/15 split by case_id hash.
        
        Returns list of sample dicts with at minimum:
          case_id, slide_path, pam50_subtype, pam50_idx, clinical_row
        """
        samples = []
        slides_dir = self.cfg.data.tcga_brca_slides_dir

        if not slides_dir.exists():
            logger.warning("Slides directory not found: %s", slides_dir)
            # Fall back to clinical-only mode
            for _, row in self.clinical.iterrows():
                case_id = str(row.get("case_id", row.name))
                samples.append(self._make_sample(case_id, None, row))
        else:
            # One sample per slide
            for slide_path in sorted(slides_dir.glob("*.svs")) + sorted(slides_dir.glob("*.ndpi")):
                case_id = slide_path.stem.split(".")[0][:12]  # TCGA barcode prefix
                clin_row = self.clinical[
                    self.clinical["case_id"].astype(str).str.startswith(case_id)
                ]
                row = clin_row.iloc[0] if len(clin_row) > 0 else pd.Series()
                samples.append(self._make_sample(case_id, slide_path, row))

        if len(samples) == 0:
            logger.warning("No samples found — dataset is empty")
            return samples

        # Deterministic hash split
        rng = np.random.RandomState(self.cfg.training.seed)
        indices = rng.permutation(len(samples))
        n = len(samples)
        n_train = int(0.70 * n)
        n_val = int(0.15 * n)

        split_map = {
            "train": indices[:n_train],
            "val": indices[n_train:n_train + n_val],
            "test": indices[n_train + n_val:],
        }
        selected = split_map.get(self.split, indices)
        return [samples[i] for i in selected]

    def _make_sample(
        self, case_id: str, slide_path: Optional[Path], row: pd.Series
    ) -> Dict[str, Any]:
        pam50 = str(row.get("pam50_subtype", "unknown"))
        return {
            "case_id": case_id,
            "slide_path": slide_path,
            "pam50_subtype": pam50,
            "pam50_idx": self.SUBTYPE_TO_IDX.get(pam50, -1),
            "er_status": str(row.get("er_status", "unknown")),
            "pr_status": str(row.get("pr_status", "unknown")),
            "her2_status": str(row.get("her2_status", "unknown")),
            "pathologic_stage": str(row.get("pathologic_stage", "unknown")),
            "age": float(row.get("age_at_diagnosis", -1)),
            "vital_status": str(row.get("vital_status", "unknown")),
            "days_to_last_follow_up": float(row.get("days_to_last_follow_up", -1)),
            "days_to_death": float(row.get("days_to_death", -1)),
        }

    # ------------------------------------------------------------------
    # Molecular data (lazy)
    # ------------------------------------------------------------------
    @property
    def rna(self) -> pd.DataFrame:
        if self._rna_df is None:
            rna_path = self.cfg.data.tcga_brca_rna
            if rna_path.exists():
                self._rna_df = pd.read_csv(rna_path, sep="\t", index_col=0)
            else:
                logger.warning("RNA file not found: %s", rna_path)
                self._rna_df = pd.DataFrame()
        return self._rna_df

    @property
    def cnv(self) -> pd.DataFrame:
        if self._cnv_df is None:
            cnv_path = self.cfg.data.tcga_brca_cnv
            if cnv_path.exists():
                self._cnv_df = pd.read_csv(cnv_path, sep="\t", index_col=0)
            else:
                self._cnv_df = pd.DataFrame()
        return self._cnv_df

    # ------------------------------------------------------------------
    # Tile loading
    # ------------------------------------------------------------------
    def _load_tiles(self, sample: Dict[str, Any]) -> torch.Tensor:
        """
        Load pre-extracted tiles for a sample.
        
        Returns tensor of shape (N, C, H, W) where N ≤ max_tiles_per_slide.
        Falls back to a zero tensor if tiles are not yet extracted.
        """
        case_id = sample["case_id"]
        tile_dir = self.tile_cache_dir / case_id

        if tile_dir.exists():
            tile_paths = sorted(tile_dir.glob("*.pt"))[:self.cfg.data.max_tiles_per_slide]
            if tile_paths:
                tiles = [torch.load(p, weights_only=True) for p in tile_paths]
                return torch.stack(tiles)

        # Placeholder — requires preprocess/tile_extraction.py to run first
        size = self.cfg.data.tile_size
        return torch.zeros(1, 3, size, size)

    # ------------------------------------------------------------------
    # __getitem__ / __len__
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        sample = self.samples[idx]
        output: Dict[str, Any] = {
            "case_id": sample["case_id"],
            "pam50_subtype": sample["pam50_subtype"],
            "pam50_idx": sample["pam50_idx"],
        }

        # Pathology tiles
        if "pathology" in self.modalities:
            tiles = self._load_tiles(sample)
            if self.transform is not None:
                tiles = self.transform(tiles)
            output["tiles"] = tiles
            output["num_tiles"] = tiles.shape[0]

        # RNA-seq
        if "rna" in self.modalities:
            case_id = sample["case_id"]
            if case_id in self.rna.columns:
                output["rna"] = torch.tensor(
                    self.rna[case_id].values.astype(np.float32)
                )
            else:
                output["rna"] = torch.zeros(self.rna.shape[0] if len(self.rna) else 20000)

        # CNV
        if "cnv" in self.modalities:
            case_id = sample["case_id"]
            if case_id in self.cnv.columns:
                output["cnv"] = torch.tensor(
                    self.cnv[case_id].values.astype(np.float32)
                )
            else:
                output["cnv"] = torch.zeros(self.cnv.shape[0] if len(self.cnv) else 20000)

        # Clinical features
        if "clinical" in self.modalities:
            output["clinical"] = {
                "er": sample["er_status"],
                "pr": sample["pr_status"],
                "her2": sample["her2_status"],
                "stage": sample["pathologic_stage"],
                "age": sample["age"],
                "vital_status": sample["vital_status"],
                "days_to_last_follow_up": sample["days_to_last_follow_up"],
                "days_to_death": sample["days_to_death"],
            }

        return output
