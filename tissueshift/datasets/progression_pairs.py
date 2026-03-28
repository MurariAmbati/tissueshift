"""
Progression pairs dataset — produces patient-matched
(timepoint_early, timepoint_late) sample tuples for
training the transition model and subtype drift heads.

Arc 1: DCIS → invasive (pre-invasive progression)
Arc 2: primary → metastatic (subtype drift)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from tissueshift.config import TissueShiftConfig

logger = logging.getLogger(__name__)


class ProgressionPairsDataset(Dataset):
    """
    Produces (early, late) sample pairs for supervision of:
      - subtype drift (primary PAM50 → metastatic PAM50)
      - stage transition (DCIS → invasive)
      - time-to-event targets

    When real paired samples are unavailable, pseudo-temporal
    ordering is used (sorted by inferred progression score).
    """

    def __init__(
        self,
        cfg: TissueShiftConfig,
        early_dataset: Dataset,
        late_dataset: Dataset,
        pair_manifest: Optional[pd.DataFrame] = None,
        use_pseudo_temporal: bool = False,
        split: str = "train",
    ):
        super().__init__()
        self.cfg = cfg
        self.early_ds = early_dataset
        self.late_ds = late_dataset
        self.use_pseudo_temporal = use_pseudo_temporal
        self.split = split

        if pair_manifest is not None:
            self.pairs = self._build_from_manifest(pair_manifest)
        elif use_pseudo_temporal:
            self.pairs = self._build_pseudo_temporal()
        else:
            self.pairs = self._build_by_patient_id()

        logger.info("ProgressionPairsDataset [%s]: %d pairs", split, len(self.pairs))

    def _build_from_manifest(self, manifest: pd.DataFrame) -> List[Tuple[int, int]]:
        """Build pairs from explicit manifest with early_idx, late_idx columns."""
        pairs = []
        for _, row in manifest.iterrows():
            e_idx = int(row.get("early_idx", -1))
            l_idx = int(row.get("late_idx", -1))
            if 0 <= e_idx < len(self.early_ds) and 0 <= l_idx < len(self.late_ds):
                pairs.append((e_idx, l_idx))
        return pairs

    def _build_by_patient_id(self) -> List[Tuple[int, int]]:
        """Match by patient_id across early/late datasets."""
        early_map: Dict[str, int] = {}
        for i in range(len(self.early_ds)):
            s = self.early_ds[i]
            pid = s.get("patient_id") or s.get("case_id") or s.get("sample_id", "")
            if pid:
                early_map[str(pid)] = i

        pairs = []
        for j in range(len(self.late_ds)):
            s = self.late_ds[j]
            pid = s.get("patient_id") or s.get("case_id") or s.get("sample_id", "")
            if str(pid) in early_map:
                pairs.append((early_map[str(pid)], j))
        return pairs

    def _build_pseudo_temporal(self) -> List[Tuple[int, int]]:
        """
        Create pseudo-temporal pairs by pairing each early sample
        with the most similar late sample (by molecular distance or
        random assignment if features unavailable).
        """
        n_early = len(self.early_ds)
        n_late = len(self.late_ds)
        rng = np.random.RandomState(self.cfg.training.seed)
        # Random pairing as baseline — can be refined with embedding distance
        late_indices = rng.choice(n_late, size=n_early, replace=n_late < n_early)
        return list(zip(range(n_early), late_indices.tolist()))

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        e_idx, l_idx = self.pairs[idx]
        early = self.early_ds[e_idx]
        late = self.late_ds[l_idx]

        return {
            "early": early,
            "late": late,
            "pair_idx": idx,
            "is_real_pair": not self.use_pseudo_temporal,
        }
