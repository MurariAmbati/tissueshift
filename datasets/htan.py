"""HTAN breast cancer dataset loader (stub for post-MVP integration)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from datasets.base import BaseDataset, CohortInfo

logger = logging.getLogger(__name__)


class HTANBreastDataset(BaseDataset):
    """HTAN breast cancer spatial atlases (stub — full integration in Phase 11).

    HTAN provides open processed L3/L4 data through Synapse and open imaging
    through IDC under CC BY 4.0. The metastatic breast atlas includes 67 biopsies
    from 60 patients across 9 anatomic sites with H&E, sc/snRNA-seq, and
    multiple spatial assays.
    """

    def info(self) -> CohortInfo:
        return CohortInfo(
            name="htan_breast",
            description=(
                "HTAN breast cancer atlases. Open processed spatial and single-cell data "
                "plus open imaging for tumor evolution studies. Metastatic breast atlas: "
                "67 biopsies, 60 patients, 9 anatomic sites."
            ),
            n_subjects=60,
            access_level="open",
            license="CC BY 4.0",
            data_types=[
                "spatial_transcriptomics",
                "single_cell_rnaseq",
                "histopathology_wsi",
                "cell_type_annotations",
                "spatial_phenotypes",
            ],
            url="https://humantumoratlas.org/",
        )

    def download(self, subset: str | None = None) -> None:
        logger.info(
            "HTAN data download is deferred to Phase 11 (post-MVP).\n"
            "Open processed data: https://www.synapse.org/ (requires Synapse account)\n"
            "Open imaging: https://portal.imaging.datacommons.cancer.gov/"
        )

    def get_manifest(self) -> pd.DataFrame:
        logger.info("HTAN manifest not yet available (Phase 11).")
        return pd.DataFrame(
            columns=["case_id", "biopsy_id", "anatomic_site", "data_type"]
        )


class GEOProgressionDataset(BaseDataset):
    """GEO DCIS-to-invasive progression cohorts (stub for Phase 13)."""

    def info(self) -> CohortInfo:
        return CohortInfo(
            name="geo_progression",
            description=(
                "Public GEO series for DCIS-to-invasive breast cancer progression. "
                "GSE214093/GSE214094: recurrence and progression datasets."
            ),
            n_subjects=0,
            access_level="open",
            license="Public",
            data_types=["gene_expression", "clinical"],
            url="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE214093",
        )

    def download(self, subset: str | None = None) -> None:
        logger.info(
            "GEO progression data download is deferred to Phase 13 (post-MVP).\n"
            "GSE214093: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE214093\n"
            "GSE214094: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE214094"
        )

    def get_manifest(self) -> pd.DataFrame:
        logger.info("GEO progression manifest not yet available (Phase 13).")
        return pd.DataFrame(columns=["sample_id", "series", "progression_status"])
