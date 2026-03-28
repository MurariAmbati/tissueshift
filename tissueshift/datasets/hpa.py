"""
Human Protein Atlas dataset loader.

HPA cancer resource: mRNA expression across 21 cancer types,
protein data from 20 cancers (IHC) and 11 cancers (mass-spec),
millions of tissue-section images, and survival-linked expression.

For TissueShift, HPA is a morphology-to-protein grounding layer and
a route to visually rich biomarker panels.
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


class HPADataset(Dataset):
    """
    HPA cancer pathology image + expression loader.

    Each sample is an IHC tissue image with associated protein
    expression level, gene name, cancer type, and optional
    survival context.
    """

    EXPRESSION_LEVELS = ("not_detected", "low", "medium", "high")
    EXPR_TO_IDX = {e: i for i, e in enumerate(EXPRESSION_LEVELS)}

    def __init__(
        self,
        cfg: TissueShiftConfig,
        cancer_type: str = "breast_cancer",
        split: str = "train",
        transform=None,
    ):
        super().__init__()
        self.cfg = cfg
        self.cancer_type = cancer_type
        self.split = split
        self.transform = transform

        self.pathology_df = self._load_pathology()
        self.survival_df = self._load_survival()
        self.samples = self._build_samples()

        logger.info("HPADataset [%s/%s]: %d samples", cancer_type, split, len(self.samples))

    def _load_pathology(self) -> pd.DataFrame:
        p = self.cfg.data.hpa_cancer_expression
        if not p.exists():
            return pd.DataFrame(columns=[
                "gene", "cancer_type", "expression_level",
                "num_patients", "staining", "image_url",
            ])
        df = pd.read_csv(p, sep="\t", low_memory=False)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        if "cancer_type" in df.columns:
            df = df[df["cancer_type"].str.lower().str.contains(self.cancer_type.replace("_", " "))]
        return df.reset_index(drop=True)

    def _load_survival(self) -> pd.DataFrame:
        p = self.cfg.data.hpa_survival
        if not p.exists():
            return pd.DataFrame()
        df = pd.read_csv(p, sep="\t", low_memory=False)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        return df

    def _build_samples(self) -> List[Dict[str, Any]]:
        samples = []
        img_dir = self.cfg.data.hpa_images_dir

        for _, row in self.pathology_df.iterrows():
            gene = str(row.get("gene", ""))
            expr = str(row.get("expression_level", "not_detected")).lower()

            # Look for downloaded image
            img_path = img_dir / f"{gene}.jpg" if img_dir.exists() else None
            if img_path and not img_path.exists():
                img_path = None

            # Lookup survival
            surv_row = {}
            if len(self.survival_df) > 0 and "gene" in self.survival_df.columns:
                match = self.survival_df[self.survival_df["gene"] == gene]
                if len(match) > 0:
                    surv_row = match.iloc[0].to_dict()

            samples.append({
                "gene": gene,
                "expression_level": expr,
                "expression_idx": self.EXPR_TO_IDX.get(expr, 0),
                "image_path": img_path,
                "survival_p_value": float(surv_row.get("p_value", -1)),
                "prognostic": str(surv_row.get("prognostic", "unknown")),
            })

        # Split
        rng = np.random.RandomState(self.cfg.training.seed)
        idx = rng.permutation(len(samples))
        n = len(samples)
        bounds = {"train": (0, int(.7 * n)), "val": (int(.7 * n), int(.85 * n)),
                  "test": (int(.85 * n), n)}
        lo, hi = bounds.get(self.split, (0, n))
        return [samples[i] for i in idx[lo:hi]]

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        s = self.samples[idx]
        out: Dict[str, Any] = {
            "gene": s["gene"],
            "expression_level": s["expression_level"],
            "expression_idx": s["expression_idx"],
        }

        if s["image_path"] and s["image_path"].exists():
            from PIL import Image
            import torchvision.transforms as T
            img = Image.open(s["image_path"]).convert("RGB")
            t = self.transform or T.Compose([T.Resize(256), T.ToTensor()])
            out["image"] = t(img)
        else:
            out["image"] = torch.zeros(3, 256, 256)

        out["survival_p_value"] = s["survival_p_value"]
        out["prognostic"] = s["prognostic"]
        return out
