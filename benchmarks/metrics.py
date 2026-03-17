"""Evaluation metrics for all six benchmark tracks."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    f1_score,
    cohen_kappa_score,
    balanced_accuracy_score,
    roc_auc_score,
    r2_score,
    mean_absolute_error,
)


def compute_subtype_call_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray | None = None
) -> dict[str, float]:
    """Track 1: SubtypeCall — PAM50 subtype classification.

    Primary: Macro-F1
    Secondary: Cohen's kappa, balanced accuracy
    """
    metrics = {
        "macro_f1": f1_score(y_true, y_pred, average="macro"),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted"),
        "cohen_kappa": cohen_kappa_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
    }

    # Per-class F1
    per_class = f1_score(y_true, y_pred, average=None)
    subtypes = ["LumA", "LumB", "Her2", "Basal", "Normal"]
    for i, name in enumerate(subtypes):
        if i < len(per_class):
            metrics[f"f1_{name}"] = per_class[i]

    return metrics


def compute_subtype_drift_metrics(
    y_true: np.ndarray,
    y_pred_prob: np.ndarray,
    target_subtype_true: np.ndarray | None = None,
    target_subtype_pred: np.ndarray | None = None,
) -> dict[str, float]:
    """Track 2: SubtypeDrift — subtype change prediction.

    Primary: AUROC for drift detection
    Secondary: Macro-F1 for target subtype prediction
    """
    metrics = {
        "drift_auroc": roc_auc_score(y_true, y_pred_prob),
    }

    if target_subtype_true is not None and target_subtype_pred is not None:
        mask = y_true == 1  # Only evaluate target subtype where drift actually occurred
        if mask.sum() > 0:
            metrics["target_macro_f1"] = f1_score(
                target_subtype_true[mask], target_subtype_pred[mask], average="macro"
            )

    return metrics


def compute_progression_metrics(
    y_true: np.ndarray, y_pred: np.ndarray
) -> dict[str, float]:
    """Track 3: ProgressionStage — ordinal progression.

    Primary: Quadratic Weighted Kappa (QWK)
    Secondary: MAE, balanced accuracy
    """
    return {
        "qwk": cohen_kappa_score(y_true, y_pred, weights="quadratic"),
        "mae": mean_absolute_error(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
    }


def compute_morph2mol_metrics(
    y_true: np.ndarray, y_pred: np.ndarray
) -> dict[str, float]:
    """Track 4: Morph2Mol — morphology-to-molecule prediction.

    Primary: Mean R² across genes
    Secondary: per-gene R², MAE
    """
    n_genes = y_true.shape[1] if y_true.ndim > 1 else 1

    if n_genes == 1:
        return {"r2": r2_score(y_true, y_pred)}

    r2_per_gene = []
    for g in range(n_genes):
        if np.std(y_true[:, g]) > 1e-8:
            r2_per_gene.append(r2_score(y_true[:, g], y_pred[:, g]))

    return {
        "mean_r2": float(np.mean(r2_per_gene)) if r2_per_gene else 0.0,
        "median_r2": float(np.median(r2_per_gene)) if r2_per_gene else 0.0,
        "n_genes_positive_r2": sum(1 for r in r2_per_gene if r > 0),
        "mae": float(mean_absolute_error(y_true.flat, y_pred.flat)),
    }


def compute_survival_metrics(
    event_times: np.ndarray,
    event_indicators: np.ndarray,
    risk_scores: np.ndarray,
) -> dict[str, float]:
    """Track 5: Survival — overall survival prediction.

    Primary: Concordance index (C-index)
    """
    # Compute C-index
    n = len(event_times)
    concordant = 0
    discordant = 0
    tied = 0

    for i in range(n):
        for j in range(i + 1, n):
            if event_indicators[i] == 0 and event_indicators[j] == 0:
                continue

            if event_times[i] < event_times[j] and event_indicators[i] == 1:
                if risk_scores[i] > risk_scores[j]:
                    concordant += 1
                elif risk_scores[i] < risk_scores[j]:
                    discordant += 1
                else:
                    tied += 1
            elif event_times[j] < event_times[i] and event_indicators[j] == 1:
                if risk_scores[j] > risk_scores[i]:
                    concordant += 1
                elif risk_scores[j] < risk_scores[i]:
                    discordant += 1
                else:
                    tied += 1

    total = concordant + discordant + tied
    c_index = (concordant + 0.5 * tied) / total if total > 0 else 0.5

    return {"c_index": c_index}


def compute_spatial_phenotype_metrics(
    til_true: np.ndarray,
    til_pred: np.ndarray,
    stromal_true: np.ndarray | None = None,
    stromal_pred: np.ndarray | None = None,
) -> dict[str, float]:
    """Track 6: SpatialPhenotype — microenvironment prediction.

    Primary: R²-TIL (TIL density prediction)
    Secondary: R²-stromal, MAE
    """
    metrics = {
        "r2_til": r2_score(til_true, til_pred),
        "mae_til": mean_absolute_error(til_true, til_pred),
    }

    if stromal_true is not None and stromal_pred is not None:
        metrics["r2_stromal"] = r2_score(stromal_true, stromal_pred)
        metrics["mae_stromal"] = mean_absolute_error(stromal_true, stromal_pred)

    return metrics


# Mapping from track name to evaluation function
TRACK_EVALUATORS = {
    "SubtypeCall": compute_subtype_call_metrics,
    "SubtypeDrift": compute_subtype_drift_metrics,
    "ProgressionStage": compute_progression_metrics,
    "Morph2Mol": compute_morph2mol_metrics,
    "Survival": compute_survival_metrics,
    "SpatialPhenotype": compute_spatial_phenotype_metrics,
}

PRIMARY_METRICS = {
    "SubtypeCall": "macro_f1",
    "SubtypeDrift": "drift_auroc",
    "ProgressionStage": "qwk",
    "Morph2Mol": "mean_r2",
    "Survival": "c_index",
    "SpatialPhenotype": "r2_til",
}
