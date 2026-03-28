"""
GEO progression cohort loader.

Public series tied to recurrence / progression of DCIS to invasive
breast cancer (e.g. GSE214093/GSE214094) and AURORA US molecular
series for paired primary–metastatic molecular analyses.
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


class GEOProgressionDataset(Dataset):
    """
    GEO DCIS-to-invasive and paired primary–metastatic cohorts.

    Provides expression matrices and clinical progression annotations
    for teaching TissueShift's pre-invasive → invasive arc.
    """

    PROGRESSION_LABELS = ("dcis_stable", "dcis_progressed", "invasive", "metastatic")
    LABEL_TO_IDX = {l: i for i, l in enumerate(PROGRESSION_LABELS)}

    def __init__(
        self,
        cfg: TissueShiftConfig,
        series: str = "GSE214093",
        split: str = "train",
    ):
        super().__init__()
        self.cfg = cfg
        self.series = series
        self.split = split

        self.data_dir = self._resolve_data_dir()
        self.expression, self.clinical = self._load_data()
        self.samples = self._build_samples()
        logger.info("GEOProgressionDataset [%s/%s]: %d samples", series, split, len(self.samples))

    def _resolve_data_dir(self) -> Path:
        if self.series.lower().startswith("gse"):
            return self.cfg.data.geo_dcis_progression
        return self.cfg.data.geo_aurora_public

    def _load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        expr_path = self.data_dir / "expression_matrix.tsv"
        clin_path = self.data_dir / "series_matrix.tsv"

        expr = pd.read_csv(expr_path, sep="\t", index_col=0) if expr_path.exists() else pd.DataFrame()
        clin = pd.read_csv(clin_path, sep="\t") if clin_path.exists() else pd.DataFrame()
        if len(clin) > 0:
            clin.columns = [c.strip().lower().replace(" ", "_") for c in clin.columns]
        return expr, clin

    def _build_samples(self) -> List[Dict[str, Any]]:
        samples: List[Dict[str, Any]] = []
        for _, row in self.clinical.iterrows():
            sample_id = str(row.get("sample_id", row.name))
            progression = str(row.get("progression_label", "unknown")).lower()
            has_primary = bool(row.get("has_primary", False))
            has_metastatic = bool(row.get("has_metastatic", False))
            time_to_event = float(row.get("time_to_progression_days", -1))
            pam50_primary = str(row.get("pam50_primary", "unknown"))
            pam50_met = str(row.get("pam50_metastatic", "unknown"))

            samples.append({
                "sample_id": sample_id,
                "progression_label": progression,
                "progression_idx": self.LABEL_TO_IDX.get(progression, -1),
                "has_primary": has_primary,
                "has_metastatic": has_metastatic,
                "time_to_event": time_to_event,
                "pam50_primary": pam50_primary,
                "pam50_metastatic": pam50_met,
                "is_paired": has_primary and has_metastatic,
            })

        rng = np.random.RandomState(self.cfg.training.seed)
        idx = rng.permutation(len(samples))
        n = len(samples)
        bounds = {"train": (0, int(.7*n)), "val": (int(.7*n), int(.85*n)), "test": (int(.85*n), n)}
        lo, hi = bounds.get(self.split, (0, n))
        return [samples[i] for i in idx[lo:hi]]

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        s = self.samples[idx]
        out: Dict[str, Any] = {
            "sample_id": s["sample_id"],
            "progression_label": s["progression_label"],
            "progression_idx": s["progression_idx"],
            "is_paired": s["is_paired"],
            "pam50_primary": s["pam50_primary"],
            "pam50_metastatic": s["pam50_metastatic"],
            "time_to_event": s["time_to_event"],
        }

        # Expression vector
        sid = s["sample_id"]
        if sid in self.expression.columns:
            out["expression"] = torch.tensor(self.expression[sid].values.astype(np.float32))
        else:
            dim = self.expression.shape[0] if len(self.expression) else 20000
            out["expression"] = torch.zeros(dim)

        return out
