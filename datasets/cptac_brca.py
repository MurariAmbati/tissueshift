"""CPTAC-BRCA dataset loader for proteogenomic breast cancer cohort."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from datasets.base import BaseDataset, CohortInfo

logger = logging.getLogger(__name__)


class CPTACBRCADataset(BaseDataset):
    """CPTAC-BRCA: 198 subjects with proteogenomic + pathology data.

    Used as external validation cohort — never trained on.
    """

    def info(self) -> CohortInfo:
        return CohortInfo(
            name="cptac_brca",
            description=(
                "CPTAC Breast Invasive Carcinoma proteogenomic cohort. 198 subjects "
                "with matched histopathology, gene expression, and proteomic quantification."
            ),
            n_subjects=198,
            access_level="open",
            license="Open Access",
            data_types=[
                "clinical",
                "gene_expression",
                "proteomics",
                "phosphoproteomics",
                "histopathology_wsi",
            ],
            url="https://proteomics.cancer.gov/programs/cptac",
        )

    def download(self, subset: str | None = None) -> None:
        """Download CPTAC-BRCA data."""
        logger.info(
            "CPTAC-BRCA data can be accessed through:\n"
            "  - Pathology images: IDC (idc-index)\n"
            "  - Proteomics: Proteomic Data Commons (PDC)\n"
            "  - Genomics: GDC (CPTAC-3 project)\n"
            "See datasets/datacards/cptac_brca.md for details."
        )

    def get_manifest(self) -> pd.DataFrame:
        """Load or build the CPTAC-BRCA manifest."""
        manifest_path = Path(__file__).parent / "manifests" / "cptac_brca_manifest.csv"
        if manifest_path.exists():
            return pd.read_csv(manifest_path)

        logger.warning(
            "CPTAC-BRCA manifest not yet available. "
            "Run download() first or create manifest from PDC/GDC metadata."
        )
        return pd.DataFrame(
            columns=["case_id", "slide_id", "pam50_subtype", "er", "pr", "her2"]
        )
