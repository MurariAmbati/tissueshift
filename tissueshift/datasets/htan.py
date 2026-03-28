"""
HTAN dataset loaders.

HTAN provides open processed level 3/4 data (Synapse) and open
imaging (IDC) under CC BY 4.0.  Organized around the dynamic
cellular, morphological, and molecular features of cancers as
they evolve from precancerous lesions to advanced disease.

HTANMetastaticDataset covers the metastatic breast atlas — 67
biopsies from 60 patients across nine anatomic sites, combining
H&E with sc/snRNA-seq and spatial assays.
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


# ======================================================================
# HTAN general (spatial + evolution)
# ======================================================================
class HTANDataset(Dataset):
    """
    HTAN open processed + imaging data loader.

    Loads spatial assay outputs (cell-level features, neighborhood
    graphs) and matched H&E imaging for spatial encoder training.
    """

    def __init__(
        self,
        cfg: TissueShiftConfig,
        split: str = "train",
        modalities: Tuple[str, ...] = ("spatial", "imaging"),
        transform=None,
    ):
        super().__init__()
        self.cfg = cfg
        self.split = split
        self.modalities = modalities
        self.transform = transform

        self.manifest = self._load_manifest()
        self.samples = self._split_samples()
        logger.info("HTANDataset [%s]: %d samples", split, len(self.samples))

    def _load_manifest(self) -> pd.DataFrame:
        """Load or create sample manifest from HTAN directory structure."""
        proc_dir = self.cfg.data.htan_processed_dir
        spatial_dir = self.cfg.data.htan_spatial_dir

        records: List[Dict[str, Any]] = []

        # Scan spatial directory for sample folders
        if spatial_dir.exists():
            for sample_dir in sorted(spatial_dir.iterdir()):
                if sample_dir.is_dir():
                    records.append({
                        "sample_id": sample_dir.name,
                        "spatial_dir": sample_dir,
                        "has_cell_features": (sample_dir / "cell_features.csv").exists(),
                        "has_neighborhoods": (sample_dir / "neighborhoods.csv").exists(),
                        "has_graph": (sample_dir / "cell_graph.pt").exists(),
                    })

        # Scan processed directory
        if proc_dir.exists():
            for sample_dir in sorted(proc_dir.iterdir()):
                if sample_dir.is_dir() and sample_dir.name not in {r["sample_id"] for r in records}:
                    records.append({
                        "sample_id": sample_dir.name,
                        "spatial_dir": None,
                        "has_cell_features": False,
                        "has_neighborhoods": False,
                        "has_graph": False,
                    })

        return pd.DataFrame(records) if records else pd.DataFrame(
            columns=["sample_id", "spatial_dir", "has_cell_features",
                     "has_neighborhoods", "has_graph"]
        )

    def _split_samples(self) -> List[Dict[str, Any]]:
        samples = self.manifest.to_dict("records")
        rng = np.random.RandomState(self.cfg.training.seed)
        idx = rng.permutation(len(samples))
        n = len(samples)
        bounds = {"train": (0, int(.7*n)), "val": (int(.7*n), int(.85*n)), "test": (int(.85*n), n)}
        lo, hi = bounds.get(self.split, (0, n))
        return [samples[i] for i in idx[lo:hi]]

    def _load_cell_graph(self, sample: Dict) -> Dict[str, torch.Tensor]:
        """Load cell graph (PyG format) or build from cell features."""
        graph_path = Path(sample.get("spatial_dir", "")) / "cell_graph.pt"
        if graph_path.exists():
            return torch.load(graph_path, weights_only=False)

        # Fall-back: load cell features CSV and build k-NN graph
        feat_path = Path(sample.get("spatial_dir", "")) / "cell_features.csv"
        if feat_path.exists():
            df = pd.read_csv(feat_path)
            coords = df[["x", "y"]].values.astype(np.float32) if {"x", "y"}.issubset(df.columns) else np.zeros((1, 2), dtype=np.float32)
            feats = df.drop(columns=["x", "y"], errors="ignore").values.astype(np.float32)
            return {
                "x": torch.tensor(feats),
                "pos": torch.tensor(coords),
                "num_nodes": feats.shape[0],
            }

        # Placeholder
        return {
            "x": torch.zeros(1, self.cfg.spatial_encoder.node_feature_dim),
            "pos": torch.zeros(1, 2),
            "num_nodes": 0,
        }

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        s = self.samples[idx]
        out: Dict[str, Any] = {"sample_id": s["sample_id"]}

        if "spatial" in self.modalities:
            out["cell_graph"] = self._load_cell_graph(s)

        if "imaging" in self.modalities:
            img_dir = self.cfg.data.htan_imaging_dir
            img_path = img_dir / f"{s['sample_id']}.svs" if img_dir.exists() else None
            out["has_slide"] = img_path is not None and img_path.exists()
            out["slide_path"] = img_path

        return out


# ======================================================================
# HTAN Metastatic Breast Atlas
# ======================================================================
class HTANMetastaticDataset(Dataset):
    """
    HTAN metastatic breast atlas loader.

    67 biopsies from 60 patients, nine anatomic sites.
    H&E + sc/snRNA-seq + four spatial assays.
    Focused on resistance mechanisms and patient-specific
    expression programs.
    """

    ANATOMIC_SITES = (
        "breast", "liver", "lung", "brain", "bone",
        "skin", "lymph_node", "soft_tissue", "other",
    )

    def __init__(
        self,
        cfg: TissueShiftConfig,
        split: str = "train",
        transform=None,
    ):
        super().__init__()
        self.cfg = cfg
        self.split = split
        self.transform = transform

        self.manifest = self._load_manifest()
        self.samples = self._split_samples()
        logger.info("HTANMetastaticDataset [%s]: %d samples", split, len(self.samples))

    def _load_manifest(self) -> pd.DataFrame:
        met_dir = self.cfg.data.htan_metastatic_dir
        manifest_path = met_dir / "manifest.csv"
        if manifest_path.exists():
            df = pd.read_csv(manifest_path)
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            return df

        # Build from directory
        records = []
        if met_dir.exists():
            for biopsy_dir in sorted(met_dir.iterdir()):
                if biopsy_dir.is_dir():
                    records.append({
                        "biopsy_id": biopsy_dir.name,
                        "patient_id": biopsy_dir.name.split("_")[0],
                        "anatomic_site": "unknown",
                        "has_he": (biopsy_dir / "he.svs").exists() or (biopsy_dir / "he.tiff").exists(),
                        "has_scrna": (biopsy_dir / "scrna.h5ad").exists(),
                        "has_spatial": (biopsy_dir / "spatial").is_dir(),
                    })
        return pd.DataFrame(records) if records else pd.DataFrame(
            columns=["biopsy_id", "patient_id", "anatomic_site",
                     "has_he", "has_scrna", "has_spatial"]
        )

    def _split_samples(self) -> List[Dict[str, Any]]:
        # Split by patient ID to prevent leakage
        patients = self.manifest["patient_id"].unique().tolist() if "patient_id" in self.manifest.columns else []
        rng = np.random.RandomState(self.cfg.training.seed)
        rng.shuffle(patients)
        n = len(patients)
        bounds = {"train": (0, int(.7*n)), "val": (int(.7*n), int(.85*n)), "test": (int(.85*n), n)}
        lo, hi = bounds.get(self.split, (0, n))
        split_patients = set(patients[lo:hi])

        if "patient_id" in self.manifest.columns:
            mask = self.manifest["patient_id"].isin(split_patients)
            return self.manifest[mask].to_dict("records")
        return []

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        s = self.samples[idx]
        met_dir = self.cfg.data.htan_metastatic_dir
        biopsy_dir = met_dir / s.get("biopsy_id", "")

        out: Dict[str, Any] = {
            "biopsy_id": s.get("biopsy_id", ""),
            "patient_id": s.get("patient_id", ""),
            "anatomic_site": s.get("anatomic_site", "unknown"),
        }

        # H&E slide
        for ext in ("svs", "tiff", "ndpi"):
            he_path = biopsy_dir / f"he.{ext}"
            if he_path.exists():
                out["slide_path"] = he_path
                break

        # Spatial graph
        spatial_dir = biopsy_dir / "spatial"
        graph_path = spatial_dir / "cell_graph.pt" if spatial_dir.exists() else None
        if graph_path and graph_path.exists():
            out["cell_graph"] = torch.load(graph_path, weights_only=False)

        # scRNA embedding
        scrna_path = biopsy_dir / "scrna_embedding.pt"
        if scrna_path.exists():
            out["scrna_embedding"] = torch.load(scrna_path, weights_only=True)

        return out
