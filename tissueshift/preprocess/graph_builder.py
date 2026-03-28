"""
Cell graph construction from spatial assay outputs.

Builds cell-level graphs suitable for PyTorch Geometric, with node
features from cell phenotype / morphology and edges from spatial
proximity (k-NN or radius graph).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import torch

from tissueshift.config import TissueShiftConfig

logger = logging.getLogger(__name__)


class CellGraphBuilder:
    """
    Constructs cell graphs from spatial single-cell data.

    Input: CSV / AnnData with cell coordinates + features.
    Output: PyG-compatible dict with x, edge_index, pos, batch.
    """

    def __init__(self, cfg: TissueShiftConfig):
        self.cfg = cfg
        self.radius = cfg.spatial_encoder.neighborhood_radius_um
        self.max_cells = cfg.spatial_encoder.max_cells_per_region
        self.node_dim = cfg.spatial_encoder.node_feature_dim

    def build_from_csv(
        self,
        csv_path: Path,
        coord_cols: tuple = ("x", "y"),
        feature_cols: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Build graph from a cell-feature CSV.

        Parameters
        ----------
        csv_path : Path
            CSV with at least coordinate columns and feature columns.
        coord_cols : tuple
            Names of X and Y coordinate columns.
        feature_cols : list or None
            If None, all numeric columns except coords are features.
        """
        import pandas as pd

        df = pd.read_csv(csv_path)

        # Subsample if too many cells
        if len(df) > self.max_cells:
            df = df.sample(n=self.max_cells, random_state=42).reset_index(drop=True)

        # Coordinates
        coords = df[list(coord_cols)].values.astype(np.float32)

        # Features
        if feature_cols is None:
            feature_cols = [c for c in df.columns if c not in coord_cols and df[c].dtype in (np.float64, np.float32, np.int64)]
        feats = df[feature_cols].values.astype(np.float32) if feature_cols else np.zeros((len(df), self.node_dim), dtype=np.float32)

        # Build edges via radius graph
        edge_index = self._radius_graph(coords, self.radius)

        return {
            "x": torch.tensor(feats),
            "pos": torch.tensor(coords),
            "edge_index": edge_index,
            "num_nodes": feats.shape[0],
        }

    def build_from_anndata(self, adata_path: Path) -> Dict[str, Any]:
        """Build graph from an AnnData (.h5ad) spatial object."""
        try:
            import anndata
        except ImportError:
            logger.error("anndata not installed")
            return self._empty_graph()

        adata = anndata.read_h5ad(adata_path)

        # Coordinates from obsm
        if "spatial" in adata.obsm:
            coords = adata.obsm["spatial"].astype(np.float32)
        elif "X_spatial" in adata.obsm:
            coords = adata.obsm["X_spatial"].astype(np.float32)
        else:
            logger.warning("No spatial coordinates in %s", adata_path)
            coords = np.zeros((adata.n_obs, 2), dtype=np.float32)

        # Features from X (dense)
        if hasattr(adata.X, "toarray"):
            feats = adata.X.toarray().astype(np.float32)
        else:
            feats = np.asarray(adata.X, dtype=np.float32)

        # Subsample
        if feats.shape[0] > self.max_cells:
            idx = np.random.RandomState(42).choice(feats.shape[0], self.max_cells, replace=False)
            feats = feats[idx]
            coords = coords[idx]

        edge_index = self._radius_graph(coords, self.radius)

        return {
            "x": torch.tensor(feats),
            "pos": torch.tensor(coords),
            "edge_index": edge_index,
            "num_nodes": feats.shape[0],
        }

    @staticmethod
    def _radius_graph(coords: np.ndarray, radius: float) -> torch.Tensor:
        """
        Build radius graph using scipy KDTree (avoids PyG dependency
        at build time, but PyG's radius_graph is used if available).
        """
        try:
            from torch_geometric.nn import radius_graph as pyg_radius_graph
            pos = torch.tensor(coords)
            return pyg_radius_graph(pos, r=radius, loop=False)
        except ImportError:
            pass

        from scipy.spatial import cKDTree
        tree = cKDTree(coords)
        pairs = tree.query_pairs(r=radius, output_type="ndarray")
        if len(pairs) == 0:
            return torch.zeros((2, 0), dtype=torch.long)
        # Undirected: both directions
        src = np.concatenate([pairs[:, 0], pairs[:, 1]])
        dst = np.concatenate([pairs[:, 1], pairs[:, 0]])
        return torch.tensor(np.stack([src, dst]), dtype=torch.long)

    def _empty_graph(self) -> Dict[str, Any]:
        return {
            "x": torch.zeros(1, self.node_dim),
            "pos": torch.zeros(1, 2),
            "edge_index": torch.zeros(2, 0, dtype=torch.long),
            "num_nodes": 0,
        }

    def save_graph(self, graph: Dict[str, Any], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(graph, path)
        logger.info("Saved cell graph (%d nodes) → %s", graph["num_nodes"], path)
