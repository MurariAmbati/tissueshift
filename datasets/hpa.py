"""Human Protein Atlas cancer IHC data loader."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from datasets.base import BaseDataset, CohortInfo

logger = logging.getLogger(__name__)

HPA_API_BASE = "https://www.proteinatlas.org/api"

# Key breast cancer markers for TissueShift
BREAST_MARKERS = [
    "ESR1", "PGR", "ERBB2", "MKI67",  # Core IHC panel
    "FOXA1", "GATA3", "CDH1", "KRT5", "KRT14", "KRT17",  # Lineage markers
    "EGFR", "VIM", "SNAI1", "CDH2",  # EMT markers
    "CD8A", "CD4", "FOXP3", "CD68", "CD163",  # Immune markers
    "ACTA2", "FAP", "COL1A1",  # Stromal markers
    "PCNA", "TOP2A", "CCNB1", "AURKA",  # Proliferation markers
]


class HPADataset(BaseDataset):
    """Human Protein Atlas cancer tissue data.

    Provides IHC images, mRNA expression, and survival-linked protein data
    for morphology-to-protein grounding in TissueShift.
    """

    def info(self) -> CohortInfo:
        return CohortInfo(
            name="hpa",
            description=(
                "Human Protein Atlas cancer resource. IHC images across 20+ cancers, "
                "mRNA expression across 21 cancer types, protein data from mass spectrometry, "
                "and survival-linked expression views."
            ),
            n_subjects=0,  # Image-based, not patient-level
            access_level="open",
            license="CC BY-SA 3.0",
            data_types=["ihc_images", "mrna_expression", "protein_expression", "survival"],
            url="https://www.proteinatlas.org/",
        )

    def download(self, subset: str | None = None) -> None:
        """Download HPA breast cancer marker data."""
        if subset is None or subset == "expression":
            self._download_cancer_expression()
        if subset is None or subset == "images":
            logger.info(
                "IHC image download is marker-by-marker via HPA API. "
                "Use download_marker_images() for specific genes."
            )

    def _download_cancer_expression(self) -> None:
        """Download cancer mRNA expression data for breast markers."""
        import httpx

        logger.info("Downloading HPA cancer expression data for breast markers...")
        records = []
        for gene in BREAST_MARKERS:
            try:
                url = f"https://www.proteinatlas.org/{gene}.json"
                resp = httpx.get(url, timeout=30, follow_redirects=True)
                if resp.status_code == 200:
                    data = resp.json()
                    records.append({
                        "gene": gene,
                        "ensembl_id": data.get("Ensembl", ""),
                        "protein_class": str(data.get("Protein class", "")),
                        "has_cancer_data": "Pathology" in str(data.keys()),
                    })
                    logger.info(f"  Retrieved {gene}")
            except Exception as e:
                logger.warning(f"  Failed to retrieve {gene}: {e}")

        df = pd.DataFrame(records)
        out_path = self.data_dir / "hpa_breast_markers.csv"
        df.to_csv(out_path, index=False)
        logger.info(f"Saved {len(df)} marker records to {out_path}")

    def download_marker_images(
        self, gene: str, cancer_type: str = "breast cancer", max_images: int = 50
    ) -> list[str]:
        """Download IHC images for a specific marker in breast cancer.

        Returns list of downloaded image paths.
        """
        import httpx

        img_dir = self.data_dir / "ihc_images" / gene
        img_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading IHC images for {gene} in {cancer_type}...")
        # HPA images are accessible via direct URL pattern
        # This is a stub — full implementation would parse the HPA image API
        logger.info(
            f"  Visit https://www.proteinatlas.org/{gene}/pathology to browse images. "
            f"Programmatic bulk download requires parsing the tissue atlas pages."
        )
        return []

    def get_manifest(self) -> pd.DataFrame:
        """Load HPA breast marker data."""
        path = self.data_dir / "hpa_breast_markers.csv"
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame(columns=["gene", "ensembl_id", "protein_class", "has_cancer_data"])

    def get_survival_data(self, gene: str) -> dict | None:
        """Get survival-linked expression data for a gene in breast cancer."""
        import httpx

        try:
            url = f"https://www.proteinatlas.org/api/search_download.php?search={gene}&format=json&columns=g,up&cancer_type=breast+cancer"
            resp = httpx.get(url, timeout=30, follow_redirects=True)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"Failed to get survival data for {gene}: {e}")
        return None
