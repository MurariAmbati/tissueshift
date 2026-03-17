"""TCGA-BRCA dataset loader using GDC API and IDC for open-access data."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from datasets.base import BaseDataset, CohortInfo

logger = logging.getLogger(__name__)

GDC_API = "https://api.gdc.cancer.gov"
GDC_FILES_ENDPOINT = f"{GDC_API}/files"
GDC_CASES_ENDPOINT = f"{GDC_API}/cases"

# PAM50 genes used for intrinsic subtyping
PAM50_GENES = [
    "UBE2T", "BIRC5", "NUF2", "CDC6", "CCNB1", "TYMS", "MYBL2", "CEP55",
    "MELK", "NDC80", "RRM2", "UBE2C", "CENPF", "PTTG1", "EXO1", "ORC6",
    "ANLN", "CCNE1", "CDC20", "MKI67", "KIF2C", "ACTR3B", "MYC", "EGFR",
    "PHGDH", "CDH3", "FGFR4", "FOXC1", "KRT14", "KRT17", "KRT5", "SFRP1",
    "BAG1", "MAPT", "PGR", "CXXC5", "ESR1", "SLC39A6", "NAT1", "FOXA1",
    "BLVRA", "MLPH", "GPR160", "TMEM45B", "BCL2", "MDM2", "ERBB2", "GRB7",
    "MMP11", "ACTR3B",
]


class TCGABRCADataset(BaseDataset):
    """TCGA-BRCA dataset: 1,098 breast cancer subjects with clinical, genomic, and pathology data."""

    def info(self) -> CohortInfo:
        return CohortInfo(
            name="tcga_brca",
            description=(
                "TCGA Breast Invasive Carcinoma cohort. 1,098 subjects with clinical, "
                "genomic, histopathology, and image analysis support via IDC."
            ),
            n_subjects=1098,
            access_level="open",
            license="Open Access (NIH Genomic Data Sharing Policy)",
            data_types=[
                "clinical",
                "gene_expression",
                "copy_number",
                "histopathology_wsi",
                "nuclei_segmentation",
                "til_maps",
            ],
            url="https://portal.gdc.cancer.gov/projects/TCGA-BRCA",
        )

    def download(self, subset: str | None = None) -> None:
        """Download TCGA-BRCA open-access data."""
        if subset is None or subset == "clinical":
            self.download_clinical()
        if subset is None or subset == "expression":
            self.download_expression()
        if subset is None or subset == "slides":
            logger.info(
                "Slide download requires idc-index. "
                "Run: python -m datasets.tcga_brca download --subset slides"
            )

    def download_clinical(self) -> pd.DataFrame:
        """Download open-access clinical data from GDC API."""
        import httpx

        logger.info("Downloading TCGA-BRCA clinical data from GDC...")

        filters = {
            "op": "and",
            "content": [
                {"op": "=", "content": {"field": "project.project_id", "value": "TCGA-BRCA"}},
                {"op": "=", "content": {"field": "files.data_category", "value": "Clinical"}},
            ],
        }

        fields = [
            "case_id",
            "submitter_id",
            "diagnoses.tumor_stage",
            "diagnoses.tumor_grade",
            "diagnoses.morphology",
            "diagnoses.primary_diagnosis",
            "diagnoses.age_at_diagnosis",
            "demographic.vital_status",
            "demographic.days_to_death",
            "demographic.days_to_last_follow_up",
            "demographic.race",
            "demographic.ethnicity",
            "demographic.gender",
        ]

        params = {
            "filters": str(filters).replace("'", '"'),
            "fields": ",".join(fields),
            "size": "1200",
            "format": "JSON",
        }

        response = httpx.get(GDC_CASES_ENDPOINT, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        records = []
        for hit in data["data"]["hits"]:
            record = {
                "case_id": hit.get("case_id", ""),
                "submitter_id": hit.get("submitter_id", ""),
            }
            if hit.get("diagnoses"):
                dx = hit["diagnoses"][0]
                record["tumor_stage"] = dx.get("tumor_stage", "")
                record["tumor_grade"] = dx.get("tumor_grade", "")
                record["age_at_diagnosis"] = dx.get("age_at_diagnosis", None)
            if hit.get("demographic"):
                demo = hit["demographic"]
                record["vital_status"] = demo.get("vital_status", "")
                record["days_to_death"] = demo.get("days_to_death", None)
                record["days_to_last_follow_up"] = demo.get("days_to_last_follow_up", None)
                record["race"] = demo.get("race", "")
                record["gender"] = demo.get("gender", "")
            records.append(record)

        df = pd.DataFrame(records)
        out_path = self.data_dir / "tcga_brca_clinical.csv"
        df.to_csv(out_path, index=False)
        logger.info(f"Saved {len(df)} clinical records to {out_path}")
        return df

    def download_expression(self) -> None:
        """Download open-access gene expression quantification from GDC."""
        import httpx

        logger.info("Downloading TCGA-BRCA expression file manifest from GDC...")

        filters = {
            "op": "and",
            "content": [
                {"op": "=", "content": {"field": "cases.project.project_id", "value": "TCGA-BRCA"}},
                {"op": "=", "content": {"field": "data_category", "value": "Transcriptome Profiling"}},
                {"op": "=", "content": {"field": "data_type", "value": "Gene Expression Quantification"}},
                {"op": "=", "content": {"field": "analysis.workflow_type", "value": "STAR - Counts"}},
                {"op": "=", "content": {"field": "access", "value": "open"}},
            ],
        }

        params = {
            "filters": str(filters).replace("'", '"'),
            "fields": "file_id,file_name,cases.submitter_id,file_size",
            "size": "1200",
            "format": "JSON",
        }

        response = httpx.get(GDC_FILES_ENDPOINT, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        manifest_records = []
        for hit in data["data"]["hits"]:
            case_id = ""
            if hit.get("cases"):
                case_id = hit["cases"][0].get("submitter_id", "")
            manifest_records.append({
                "file_id": hit["file_id"],
                "file_name": hit.get("file_name", ""),
                "case_id": case_id,
                "file_size": hit.get("file_size", 0),
            })

        manifest_df = pd.DataFrame(manifest_records)
        out_path = self.data_dir / "tcga_brca_expression_manifest.csv"
        manifest_df.to_csv(out_path, index=False)
        logger.info(
            f"Saved expression manifest with {len(manifest_df)} files to {out_path}. "
            f"Use GDC Data Transfer Tool to download the actual files."
        )

    def download_slides_idc(self) -> None:
        """Download whole-slide images from IDC using idc-index."""
        try:
            from idc_index import IDCClient

            client = IDCClient()
            slides_dir = self.data_dir / "slides"
            slides_dir.mkdir(parents=True, exist_ok=True)

            logger.info("Downloading TCGA-BRCA slides from IDC...")
            client.download_from_selection(
                collection_id="tcga_brca",
                downloadDir=str(slides_dir),
            )
            logger.info(f"Slides downloaded to {slides_dir}")
        except ImportError:
            logger.error(
                "idc-index not installed. Install with: pip install idc-index"
            )

    def get_manifest(self) -> pd.DataFrame:
        """Load or build the curated sample manifest."""
        manifest_path = Path(__file__).parent / "manifests" / "tcga_brca_manifest.csv"
        if manifest_path.exists():
            return pd.read_csv(manifest_path)

        # Build from downloaded clinical data
        clinical_path = self.data_dir / "tcga_brca_clinical.csv"
        if not clinical_path.exists():
            logger.info("Clinical data not found, downloading...")
            self.download_clinical()

        df = pd.read_csv(clinical_path)
        logger.info(f"Loaded manifest with {len(df)} records")
        return df

    def get_pam50_labels(self) -> pd.DataFrame:
        """Extract PAM50 intrinsic subtype labels.

        Uses the published TCGA BRCA molecular subtype assignments.
        Falls back to the clinical data subtype field if available.
        """
        manifest = self.get_manifest()
        if "pam50_subtype" in manifest.columns:
            return manifest[["case_id", "pam50_subtype"]].dropna()

        logger.warning(
            "PAM50 labels not in manifest. You may need to download the TCGA BRCA "
            "supplementary tables and join on case_id. See datasets/datacards/tcga_brca.md"
        )
        return pd.DataFrame(columns=["case_id", "pam50_subtype"])

    def get_ihc_labels(self) -> pd.DataFrame:
        """Extract ER/PR/HER2 IHC receptor status."""
        manifest = self.get_manifest()
        ihc_cols = ["case_id", "er_status", "pr_status", "her2_status"]
        available = [c for c in ihc_cols if c in manifest.columns]
        if len(available) > 1:
            return manifest[available].dropna(subset=available[1:])

        logger.warning("IHC labels not available in manifest.")
        return pd.DataFrame(columns=ihc_cols)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TCGA-BRCA data download")
    parser.add_argument("action", choices=["download", "info", "manifest"])
    parser.add_argument("--data-dir", default="./data/tcga_brca")
    parser.add_argument("--subset", default=None, choices=["clinical", "expression", "slides"])
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    dataset = TCGABRCADataset(data_dir=args.data_dir)

    if args.action == "info":
        print(dataset.info())
    elif args.action == "download":
        dataset.download(subset=args.subset)
    elif args.action == "manifest":
        df = dataset.get_manifest()
        print(f"Manifest: {len(df)} records")
        print(df.head())
