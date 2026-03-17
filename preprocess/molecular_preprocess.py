"""Molecular data preprocessing: expression normalization, pathway scoring, PAM50 extraction."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# PAM50 intrinsic subtype gene panel (50 genes)
PAM50_GENES = [
    "UBE2T", "BIRC5", "NUF2", "CDC6", "CCNB1", "TYMS", "MYBL2", "CEP55",
    "MELK", "NDC80", "RRM2", "UBE2C", "CENPF", "PTTG1", "EXO1", "ORC6",
    "ANLN", "CCNE1", "CDC20", "MKI67", "KIF2C", "ACTR3B", "MYC", "EGFR",
    "PHGDH", "CDH3", "FGFR4", "FOXC1", "KRT14", "KRT17", "KRT5", "SFRP1",
    "BAG1", "MAPT", "PGR", "CXXC5", "ESR1", "SLC39A6", "NAT1", "FOXA1",
    "BLVRA", "MLPH", "GPR160", "TMEM45B", "BCL2", "MDM2", "ERBB2", "GRB7",
    "MMP11",
]

# Extended gene panel for expression prediction tasks (200 genes)
EXTENDED_GENES = PAM50_GENES + [
    # Additional subtype-discriminating genes
    "TP53", "PIK3CA", "GATA3", "CDH1", "MAP3K1", "PTEN", "AKT1",
    "BRCA1", "BRCA2", "RB1", "CDKN2A", "CCND1", "FGFR1",
    # Immune markers
    "CD8A", "CD4", "FOXP3", "CD274", "PDCD1", "CTLA4", "IFNG",
    "CD68", "CD163", "MS4A1",
    # Stromal markers
    "ACTA2", "FAP", "COL1A1", "COL3A1", "FN1", "VIM",
    # EMT markers
    "SNAI1", "SNAI2", "TWIST1", "ZEB1", "CDH2",
    # Proliferation
    "PCNA", "TOP2A", "AURKA", "AURKB", "PLK1",
    # Hormone signaling
    "AR", "TFF1", "TFF3", "XBP1", "SCUBE2",
    # HER2 pathway
    "GRB2", "SHC1", "MAPK1", "MAPK3", "MTOR",
    # Survival-related
    "VEGFA", "HIF1A", "MYC", "BCL2L1", "MCL1",
    # Cell cycle
    "CDK4", "CDK6", "CDKN1A", "CDKN1B", "E2F1",
]
# Deduplicate while preserving order
EXTENDED_GENES = list(dict.fromkeys(EXTENDED_GENES))


def normalize_expression(
    expression_df: pd.DataFrame,
    method: str = "log2_zscore",
) -> pd.DataFrame:
    """Normalize gene expression values.

    Args:
        expression_df: DataFrame with genes as columns, samples as rows
        method: Normalization method
            - "log2_zscore": log2(x+1) then z-score per gene
            - "log2": log2(x+1) only
            - "zscore": z-score per gene only

    Returns:
        Normalized expression DataFrame
    """
    df = expression_df.copy()

    if method in ("log2_zscore", "log2"):
        # Add pseudocount and log2 transform
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = np.log2(df[numeric_cols] + 1)

    if method in ("log2_zscore", "zscore"):
        # Z-score per gene (column)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        means = df[numeric_cols].mean()
        stds = df[numeric_cols].std()
        stds[stds == 0] = 1  # Avoid division by zero for constant genes
        df[numeric_cols] = (df[numeric_cols] - means) / stds

    return df


def extract_pam50_features(
    expression_df: pd.DataFrame,
    gene_col_format: str = "gene_symbol",
) -> pd.DataFrame:
    """Extract PAM50 gene features from expression data.

    Args:
        expression_df: Normalized expression DataFrame
        gene_col_format: How gene columns are named

    Returns:
        DataFrame with PAM50 gene expression values
    """
    available_genes = [g for g in PAM50_GENES if g in expression_df.columns]
    missing_genes = [g for g in PAM50_GENES if g not in expression_df.columns]

    if missing_genes:
        logger.warning(f"Missing {len(missing_genes)}/{len(PAM50_GENES)} PAM50 genes: {missing_genes[:5]}...")

    pam50_df = expression_df[available_genes].copy()

    # Fill missing genes with zeros
    for gene in missing_genes:
        pam50_df[gene] = 0.0

    # Reorder to standard PAM50 ordering
    pam50_df = pam50_df[[g for g in PAM50_GENES if g in pam50_df.columns]]

    logger.info(f"Extracted {len(available_genes)}/{len(PAM50_GENES)} PAM50 gene features")
    return pam50_df


def compute_pathway_scores(
    expression_df: pd.DataFrame,
    gene_sets: str = "hallmark",
    method: str = "ssgsea",
) -> pd.DataFrame:
    """Compute pathway activity scores using ssGSEA.

    Args:
        expression_df: Normalized expression DataFrame (genes as columns)
        gene_sets: Gene set collection ("hallmark" for MSigDB Hallmark)
        method: Scoring method ("ssgsea" or "gsva")

    Returns:
        DataFrame with pathway scores (samples × pathways)
    """
    try:
        import gseapy as gp

        logger.info("Computing ssGSEA pathway scores...")

        # Transpose: gseapy expects genes as rows
        expr_t = expression_df.select_dtypes(include=[np.number]).T

        results = gp.ssgsea(
            data=expr_t,
            gene_sets=f"h.all.v2024.1.Hs.symbols.gmt" if gene_sets == "hallmark" else gene_sets,
            outdir=None,
            no_plot=True,
            processes=1,
            seed=42,
        )

        scores = results.res2d.pivot(index="Name", columns="Term", values="NES")
        logger.info(f"Computed {scores.shape[1]} pathway scores for {scores.shape[0]} samples")
        return scores

    except ImportError:
        logger.warning("gseapy not available. Computing simple mean signature scores.")
        return _compute_simple_pathway_scores(expression_df)
    except Exception as e:
        logger.warning(f"ssGSEA failed: {e}. Computing simple scores.")
        return _compute_simple_pathway_scores(expression_df)


def _compute_simple_pathway_scores(expression_df: pd.DataFrame) -> pd.DataFrame:
    """Fallback: compute pathway scores as mean expression of gene sets."""
    # Define simplified pathway gene sets
    pathways = {
        "proliferation": ["MKI67", "TOP2A", "PCNA", "AURKA", "CCNB1", "CDK4"],
        "er_signaling": ["ESR1", "PGR", "FOXA1", "GATA3", "TFF1", "XBP1"],
        "her2_signaling": ["ERBB2", "GRB7", "GRB2", "MAPK1", "MAPK3"],
        "basal_markers": ["KRT5", "KRT14", "KRT17", "EGFR", "CDH3"],
        "emt": ["VIM", "SNAI1", "SNAI2", "ZEB1", "CDH2", "TWIST1"],
        "immune_activation": ["CD8A", "CD4", "IFNG", "CD274", "PDCD1"],
        "immune_suppression": ["FOXP3", "CTLA4", "CD163"],
        "stromal": ["ACTA2", "FAP", "COL1A1", "FN1"],
        "angiogenesis": ["VEGFA", "HIF1A"],
        "apoptosis": ["BCL2", "BCL2L1", "MCL1"],
        "cell_cycle": ["CDK4", "CDK6", "CDKN1A", "CDKN1B", "E2F1", "RB1"],
        "dna_repair": ["BRCA1", "BRCA2", "TP53"],
        "pi3k_akt": ["PIK3CA", "PTEN", "AKT1", "MTOR"],
    }

    scores = {}
    for pathway_name, genes in pathways.items():
        available = [g for g in genes if g in expression_df.columns]
        if available:
            scores[pathway_name] = expression_df[available].mean(axis=1)
        else:
            scores[pathway_name] = 0.0

    return pd.DataFrame(scores, index=expression_df.index)


def preprocess_proteomics(
    protein_df: pd.DataFrame,
    log_transform: bool = True,
) -> pd.DataFrame:
    """Preprocess proteomic abundance data.

    Args:
        protein_df: DataFrame with protein abundances (samples × proteins)
        log_transform: Whether to log2-transform

    Returns:
        Preprocessed proteomic DataFrame
    """
    df = protein_df.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    if log_transform:
        # Log2 ratio (already log-ratio from mass spec typically)
        # Clip extreme values
        df[numeric_cols] = df[numeric_cols].clip(lower=-10, upper=10)

    # Z-score per protein
    means = df[numeric_cols].mean()
    stds = df[numeric_cols].std()
    stds[stds == 0] = 1
    df[numeric_cols] = (df[numeric_cols] - means) / stds

    return df


def build_molecular_feature_vector(
    expression_df: pd.DataFrame | None = None,
    pathway_scores: pd.DataFrame | None = None,
    protein_df: pd.DataFrame | None = None,
    clinical_markers: pd.DataFrame | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Build unified molecular feature vector per sample.

    Returns:
        features: (n_samples, n_features) array
        feature_names: list of feature names
    """
    parts = []
    names = []

    if expression_df is not None:
        pam50 = extract_pam50_features(expression_df)
        parts.append(pam50.values)
        names.extend([f"expr_{g}" for g in pam50.columns])

    if pathway_scores is not None:
        parts.append(pathway_scores.values)
        names.extend([f"pathway_{c}" for c in pathway_scores.columns])

    if protein_df is not None:
        parts.append(protein_df.select_dtypes(include=[np.number]).values)
        names.extend([f"protein_{c}" for c in protein_df.select_dtypes(include=[np.number]).columns])

    if clinical_markers is not None:
        parts.append(clinical_markers.select_dtypes(include=[np.number]).values)
        names.extend([f"clinical_{c}" for c in clinical_markers.select_dtypes(include=[np.number]).columns])

    if not parts:
        raise ValueError("At least one molecular data source must be provided")

    features = np.concatenate(parts, axis=1)
    logger.info(f"Built molecular feature vector: {features.shape} ({len(names)} features)")
    return features, names


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Molecular data preprocessing")
    parser.add_argument("--expression", help="Path to expression CSV")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--method", default="log2_zscore")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.expression:
        df = pd.read_csv(args.expression, index_col=0)
        normalized = normalize_expression(df, method=args.method)

        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        normalized.to_csv(output_dir / "expression_normalized.csv")
        pam50 = extract_pam50_features(normalized)
        pam50.to_csv(output_dir / "pam50_features.csv")
        pathways = compute_pathway_scores(normalized)
        pathways.to_csv(output_dir / "pathway_scores.csv")

        logger.info(f"Saved preprocessed molecular data to {output_dir}")
