"""
Multimodal dataset — wraps individual cohort loaders and provides
aligned multi-modal samples for joint training.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import torch
from torch.utils.data import Dataset

from tissueshift.config import TissueShiftConfig

logger = logging.getLogger(__name__)


class MultimodalTissueDataset(Dataset):
    """
    Unified multi-modal tissue dataset that aligns pathology,
    molecular, spatial, and clinical modalities per sample.

    Wraps one or more source cohorts and produces a standardised
    sample dict suitable for the TissueShift world model.
    """

    def __init__(
        self,
        cfg: TissueShiftConfig,
        sources: Optional[List[Dataset]] = None,
        split: str = "train",
    ):
        super().__init__()
        self.cfg = cfg
        self.split = split
        self.sources = sources or []

        # Flatten into a unified sample list
        self.samples: List[Tuple[int, int]] = []  # (source_idx, item_idx)
        for src_idx, src in enumerate(self.sources):
            for item_idx in range(len(src)):
                self.samples.append((src_idx, item_idx))

        logger.info(
            "MultimodalTissueDataset [%s]: %d samples from %d sources",
            split, len(self.samples), len(self.sources),
        )

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        src_idx, item_idx = self.samples[idx]
        raw = self.sources[src_idx][item_idx]

        # Standardize to common schema
        out: Dict[str, Any] = {
            "source_idx": src_idx,
            "item_idx": item_idx,
        }

        # Pathology
        if "tiles" in raw:
            out["tiles"] = raw["tiles"]
            out["num_tiles"] = raw.get("num_tiles", raw["tiles"].shape[0])

        # Molecular
        for key in ("rna", "proteomics", "cnv", "expression"):
            if key in raw:
                out[key] = raw[key]

        # Spatial
        if "cell_graph" in raw:
            out["cell_graph"] = raw["cell_graph"]

        # Labels
        for key in ("pam50_subtype", "pam50_idx", "progression_label",
                     "progression_idx", "expression_level", "expression_idx"):
            if key in raw:
                out[key] = raw[key]

        # Clinical
        if "clinical" in raw:
            out["clinical"] = raw["clinical"]

        # Identifiers
        for key in ("case_id", "sample_id", "biopsy_id", "patient_id", "gene"):
            if key in raw:
                out[key] = raw[key]

        # Metastatic context
        for key in ("anatomic_site", "pam50_primary", "pam50_metastatic",
                     "is_paired", "time_to_event"):
            if key in raw:
                out[key] = raw[key]

        return out
