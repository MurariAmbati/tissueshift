"""
CPTAC-BRCA dataset loader.

Sources: IDC/TCIA for imaging, CPTAC DCC for proteomics.
198 subjects — breast invasive carcinoma proteogenomic cohort
with public pathology, imaging, proteomic, and genomic context.
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


class CPTACBRCADataset(Dataset):
    """
    CPTAC-BRCA cohort loader.

    Provides slide-level pathology tiles, proteomics abundance,
    RNA-seq, and clinical annotations.  Ideal for the
    morphology-to-protein branch of TissueShift.
    """

    def __init__(
        self,
        cfg: TissueShiftConfig,
        split: str = "train",
        modalities: Tuple[str, ...] = ("pathology", "proteomics", "rna", "clinical"),
        transform=None,
    ):
        super().__init__()
        self.cfg = cfg
        self.split = split
        self.modalities = modalities
        self.transform = transform

        self.clinical = self._load_clinical()
        self.samples = self._split_samples()

        self._prot_df: Optional[pd.DataFrame] = None
        self._rna_df: Optional[pd.DataFrame] = None

        logger.info(
            "CPTACBRCADataset [%s]: %d samples", split, len(self.samples),
        )

    def _load_clinical(self) -> pd.DataFrame:
        path = self.cfg.data.cptac_brca_clinical
        if not path.exists():
            return pd.DataFrame(columns=[
                "case_id", "pam50_subtype", "er_status", "pr_status",
                "her2_status", "pathologic_stage", "age_at_diagnosis",
            ])
        df = pd.read_csv(path, sep="\t", low_memory=False)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        return df

    def _split_samples(self) -> List[Dict[str, Any]]:
        samples: List[Dict[str, Any]] = []
        slides_dir = self.cfg.data.cptac_brca_slides_dir

        if slides_dir.exists():
            for slide_path in sorted(slides_dir.glob("*.svs")):
                case_id = slide_path.stem.split("-")[0]
                clin = self.clinical[self.clinical["case_id"].astype(str) == case_id]
                row = clin.iloc[0] if len(clin) > 0 else pd.Series()
                samples.append({
                    "case_id": case_id,
                    "slide_path": slide_path,
                    "pam50_subtype": str(row.get("pam50_subtype", "unknown")),
                })
        else:
            for _, row in self.clinical.iterrows():
                samples.append({
                    "case_id": str(row.get("case_id", row.name)),
                    "slide_path": None,
                    "pam50_subtype": str(row.get("pam50_subtype", "unknown")),
                })

        # Deterministic split
        rng = np.random.RandomState(self.cfg.training.seed)
        idx = rng.permutation(len(samples))
        n = len(samples)
        bounds = {"train": (0, int(.7 * n)), "val": (int(.7 * n), int(.85 * n)),
                  "test": (int(.85 * n), n)}
        lo, hi = bounds.get(self.split, (0, n))
        return [samples[i] for i in idx[lo:hi]]

    # ------------------------------------------------------------------
    # Lazy molecular loaders
    # ------------------------------------------------------------------
    @property
    def proteomics(self) -> pd.DataFrame:
        if self._prot_df is None:
            p = self.cfg.data.cptac_brca_proteomics
            self._prot_df = pd.read_csv(p, sep="\t", index_col=0) if p.exists() else pd.DataFrame()
        return self._prot_df

    @property
    def rna(self) -> pd.DataFrame:
        if self._rna_df is None:
            p = self.cfg.data.cptac_brca_rna
            self._rna_df = pd.read_csv(p, sep="\t", index_col=0) if p.exists() else pd.DataFrame()
        return self._rna_df

    # ------------------------------------------------------------------
    # Tile loading
    # ------------------------------------------------------------------
    def _load_tiles(self, sample: Dict) -> torch.Tensor:
        tile_dir = self.cfg.data.cptac_brca_slides_dir / "tiles" / sample["case_id"]
        if tile_dir.exists():
            paths = sorted(tile_dir.glob("*.pt"))[:self.cfg.data.max_tiles_per_slide]
            if paths:
                return torch.stack([torch.load(p, weights_only=True) for p in paths])
        return torch.zeros(1, 3, self.cfg.data.tile_size, self.cfg.data.tile_size)

    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        s = self.samples[idx]
        out: Dict[str, Any] = {"case_id": s["case_id"], "pam50_subtype": s["pam50_subtype"]}

        if "pathology" in self.modalities:
            t = self._load_tiles(s)
            out["tiles"] = self.transform(t) if self.transform else t
            out["num_tiles"] = t.shape[0]

        if "proteomics" in self.modalities:
            cid = s["case_id"]
            if cid in self.proteomics.columns:
                out["proteomics"] = torch.tensor(self.proteomics[cid].values.astype(np.float32))
            else:
                out["proteomics"] = torch.zeros(self.proteomics.shape[0] or 10000)

        if "rna" in self.modalities:
            cid = s["case_id"]
            if cid in self.rna.columns:
                out["rna"] = torch.tensor(self.rna[cid].values.astype(np.float32))
            else:
                out["rna"] = torch.zeros(self.rna.shape[0] or 20000)

        return out
