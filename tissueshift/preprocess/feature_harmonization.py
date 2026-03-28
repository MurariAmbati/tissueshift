"""
Feature harmonisation across cohorts.

Handles batch-effect correction, gene-name mapping, and
expression-level alignment between TCGA, CPTAC, HTAN, and GEO
data so that downstream encoders see a consistent feature space.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureHarmonizer:
    """
    Cross-cohort feature harmonisation.

    Steps:
      1. Gene-symbol normalisation (alias resolution via HGNC).
      2. Intersection to shared gene set.
      3. Quantile normalisation across cohorts.
      4. Optional ComBat batch correction.
    """

    def __init__(
        self,
        target_genes: Optional[List[str]] = None,
        use_combat: bool = False,
    ):
        self.target_genes = target_genes
        self.use_combat = use_combat
        self._gene_map: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Gene symbol normalisation
    # ------------------------------------------------------------------
    def load_gene_alias_map(self, alias_path: str) -> None:
        """
        Load HGNC alias → approved symbol mapping.

        Parameters
        ----------
        alias_path : str
            TSV with columns: alias_symbol, approved_symbol
        """
        df = pd.read_csv(alias_path, sep="\t")
        for _, row in df.iterrows():
            alias = str(row.get("alias_symbol", "")).upper()
            approved = str(row.get("approved_symbol", "")).upper()
            if alias and approved:
                self._gene_map[alias] = approved
        logger.info("Loaded %d gene aliases", len(self._gene_map))

    def normalise_gene_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map gene symbols to approved HGNC names."""
        new_index = [self._gene_map.get(g.upper(), g.upper()) for g in df.index]
        df.index = new_index
        # Collapse duplicates
        df = df.groupby(df.index).mean()
        return df

    # ------------------------------------------------------------------
    # Intersection
    # ------------------------------------------------------------------
    def intersect_genes(self, *dataframes: pd.DataFrame) -> List[pd.DataFrame]:
        """Restrict all dataframes to shared gene set."""
        if self.target_genes:
            shared = set(self.target_genes)
        else:
            sets = [set(df.index) for df in dataframes if len(df) > 0]
            shared = sets[0].intersection(*sets[1:]) if sets else set()

        logger.info("Shared gene set: %d genes", len(shared))
        return [df.loc[df.index.isin(shared)].sort_index() for df in dataframes]

    # ------------------------------------------------------------------
    # Quantile normalisation
    # ------------------------------------------------------------------
    @staticmethod
    def quantile_normalise(df: pd.DataFrame) -> pd.DataFrame:
        """Quantile-normalise columns (samples) of a genes × samples matrix."""
        rank_mean = df.stack().groupby(
            df.rank(method="first").stack().astype(int)
        ).mean()
        normed = df.rank(method="min").stack().astype(int).map(rank_mean).unstack()
        return normed

    # ------------------------------------------------------------------
    # ComBat batch correction
    # ------------------------------------------------------------------
    @staticmethod
    def combat_correct(
        expression: pd.DataFrame,
        batch_labels: np.ndarray,
    ) -> pd.DataFrame:
        """
        Apply ComBat batch correction.

        Requires the `pycombat` or `combat` package.
        """
        try:
            from combat.pycombat import pycombat
            corrected = pycombat(expression, batch_labels)
            return corrected
        except ImportError:
            logger.warning("pycombat not installed — skipping ComBat correction")
            return expression

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------
    def harmonise(
        self,
        cohort_dfs: Dict[str, pd.DataFrame],
    ) -> Dict[str, pd.DataFrame]:
        """
        Run full harmonisation pipeline.

        Parameters
        ----------
        cohort_dfs : dict
            {"tcga": df_tcga, "cptac": df_cptac, ...}
            Each df is genes × samples.

        Returns
        -------
        dict  — same keys, harmonised DataFrames.
        """
        # Step 1: gene name normalisation
        for name in cohort_dfs:
            cohort_dfs[name] = self.normalise_gene_names(cohort_dfs[name])

        # Step 2: intersect
        keys = list(cohort_dfs.keys())
        dfs = list(cohort_dfs.values())
        dfs = self.intersect_genes(*dfs)
        cohort_dfs = dict(zip(keys, dfs))

        # Step 3: quantile normalise each cohort
        for name in cohort_dfs:
            if len(cohort_dfs[name]) > 0:
                cohort_dfs[name] = self.quantile_normalise(cohort_dfs[name])

        # Step 4: optional ComBat across cohorts
        if self.use_combat and len(cohort_dfs) > 1:
            merged = pd.concat(list(cohort_dfs.values()), axis=1)
            labels = np.concatenate([
                np.full(df.shape[1], i) for i, df in enumerate(cohort_dfs.values())
            ])
            corrected = self.combat_correct(merged, labels)
            # Split back
            start = 0
            for name, df in cohort_dfs.items():
                end = start + df.shape[1]
                cohort_dfs[name] = corrected.iloc[:, start:end]
                start = end

        logger.info("Harmonisation complete: %s", {k: v.shape for k, v in cohort_dfs.items()})
        return cohort_dfs
