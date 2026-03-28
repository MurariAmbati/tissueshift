"""
TissueShift evaluator — four-layer evaluation protocol.

Layer 1: Static subtype performance (TCGA-BRCA, CPTAC-BRCA)
Layer 2: Progression-stage validation (DCIS→invasive)
Layer 3: Metastatic subtype drift (paired primary–metastatic)
Layer 4: Spatial phenotype consistency (HTAN)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class TissueShiftEvaluator:
    """
    Comprehensive evaluation across four validation layers.
    """

    def __init__(self, config=None):
        self.config = config
        self.results: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Layer 1: Static subtype
    # ------------------------------------------------------------------
    def evaluate_static_subtype(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: Optional[np.ndarray] = None,
        class_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Evaluate static subtype classification.

        Metrics: accuracy, balanced_accuracy, macro_f1, weighted_f1,
                 cohen_kappa, AUC-OVR, calibration ECE.
        """
        from sklearn.metrics import (
            accuracy_score,
            balanced_accuracy_score,
            f1_score,
            cohen_kappa_score,
        )

        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
            "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
            "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
            "cohen_kappa": cohen_kappa_score(y_true, y_pred),
        }

        if y_prob is not None:
            try:
                from sklearn.metrics import roc_auc_score
                if y_prob.shape[1] > 2:
                    metrics["auc_ovr"] = roc_auc_score(
                        y_true, y_prob, multi_class="ovr", average="macro",
                    )
                else:
                    metrics["auc_ovr"] = roc_auc_score(y_true, y_prob[:, 1])
            except Exception as e:
                logger.warning("AUC computation failed: %s", e)
                metrics["auc_ovr"] = -1.0

            metrics["calibration_ece"] = self._expected_calibration_error(
                y_true, y_prob
            )

        self.results["static_subtype"] = metrics
        logger.info("Layer 1 — Static subtype: %s", metrics)
        return metrics

    # ------------------------------------------------------------------
    # Layer 2: Progression stage
    # ------------------------------------------------------------------
    def evaluate_progression(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: Optional[np.ndarray] = None,
    ) -> Dict[str, float]:
        """Evaluate progression-stage classification."""
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            confusion_matrix,
        )

        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        }

        if y_prob is not None:
            try:
                from sklearn.metrics import roc_auc_score
                metrics["auc_ovr"] = roc_auc_score(
                    y_true, y_prob, multi_class="ovr", average="macro",
                )
            except Exception:
                metrics["auc_ovr"] = -1.0

        cm = confusion_matrix(y_true, y_pred)
        metrics["stage_confusion"] = cm.tolist()

        self.results["progression"] = metrics
        logger.info("Layer 2 — Progression: %s",
                     {k: v for k, v in metrics.items() if k != "stage_confusion"})
        return metrics

    # ------------------------------------------------------------------
    # Layer 3: Metastatic drift
    # ------------------------------------------------------------------
    def evaluate_drift(
        self,
        primary_subtypes: np.ndarray,
        metastatic_subtypes: np.ndarray,
        predicted_drift: np.ndarray,
        survival_times: Optional[np.ndarray] = None,
        events: Optional[np.ndarray] = None,
        risk_scores: Optional[np.ndarray] = None,
    ) -> Dict[str, float]:
        """
        Evaluate subtype drift prediction against paired
        primary–metastatic ground truth.
        """
        # Drift accuracy: did the predicted drift match the actual subtype change?
        actual_drift = (primary_subtypes != metastatic_subtypes).astype(int)
        predicted_binary = (predicted_drift > 0.5).astype(int) if predicted_drift.ndim == 1 else predicted_drift.argmax(axis=1)

        from sklearn.metrics import accuracy_score, f1_score
        metrics = {
            "drift_accuracy": accuracy_score(actual_drift, predicted_binary),
            "drift_f1": f1_score(actual_drift, predicted_binary, zero_division=0),
        }

        # Concordance: how often primary and met subtypes match
        concordance = (primary_subtypes == metastatic_subtypes).mean()
        metrics["concordance_primary_met"] = float(concordance)

        # Survival metrics (if available)
        if survival_times is not None and events is not None and risk_scores is not None:
            try:
                from sksurv.metrics import concordance_index_censored
                c_index = concordance_index_censored(
                    events.astype(bool), survival_times, risk_scores
                )[0]
                metrics["c_index"] = c_index
            except ImportError:
                logger.warning("scikit-survival not installed — skipping c-index")
            except Exception as e:
                logger.warning("C-index computation failed: %s", e)

        self.results["drift"] = metrics
        logger.info("Layer 3 — Drift: %s", metrics)
        return metrics

    # ------------------------------------------------------------------
    # Layer 4: Spatial phenotype
    # ------------------------------------------------------------------
    def evaluate_spatial(
        self,
        latent_embeddings: np.ndarray,
        spatial_labels: np.ndarray,
        region_true: Optional[np.ndarray] = None,
        region_pred: Optional[np.ndarray] = None,
    ) -> Dict[str, float]:
        """
        Evaluate manifold alignment with spatial microenvironment
        structure.
        """
        from sklearn.metrics import silhouette_score, normalized_mutual_info_score

        metrics = {}

        # Silhouette score in latent space
        if len(np.unique(spatial_labels)) > 1:
            metrics["silhouette_latent"] = silhouette_score(
                latent_embeddings, spatial_labels
            )
        else:
            metrics["silhouette_latent"] = -1.0

        # Manifold alignment: NMI between latent clusters and spatial labels
        from sklearn.cluster import KMeans
        n_clusters = min(len(np.unique(spatial_labels)), 10)
        if n_clusters > 1:
            km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            latent_clusters = km.fit_predict(latent_embeddings)
            metrics["manifold_alignment_nmi"] = normalized_mutual_info_score(
                spatial_labels, latent_clusters
            )
        else:
            metrics["manifold_alignment_nmi"] = -1.0

        # Region prediction F1
        if region_true is not None and region_pred is not None:
            from sklearn.metrics import f1_score
            metrics["region_prediction_f1"] = f1_score(
                region_true, region_pred, average="macro", zero_division=0,
            )

        self.results["spatial"] = metrics
        logger.info("Layer 4 — Spatial: %s", metrics)
        return metrics

    # ------------------------------------------------------------------
    # Bootstrap confidence intervals
    # ------------------------------------------------------------------
    def bootstrap_metric(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        metric_fn,
        n_bootstrap: int = 1000,
        confidence: float = 0.95,
    ) -> Tuple[float, float, float]:
        """
        Compute bootstrap confidence interval for a metric.

        Returns (mean, lower, upper).
        """
        rng = np.random.RandomState(42)
        scores = []
        n = len(y_true)
        for _ in range(n_bootstrap):
            idx = rng.choice(n, n, replace=True)
            try:
                scores.append(metric_fn(y_true[idx], y_pred[idx]))
            except Exception:
                continue

        scores = np.array(scores)
        alpha = (1 - confidence) / 2
        return float(scores.mean()), float(np.percentile(scores, alpha * 100)), float(np.percentile(scores, (1 - alpha) * 100))

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------
    @staticmethod
    def _expected_calibration_error(
        y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 15,
    ) -> float:
        """Expected Calibration Error (ECE)."""
        if y_prob.ndim > 1:
            confidences = y_prob.max(axis=1)
            predictions = y_prob.argmax(axis=1)
        else:
            confidences = y_prob
            predictions = (y_prob > 0.5).astype(int)

        accuracies = (predictions == y_true).astype(float)
        bins = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        for lo, hi in zip(bins[:-1], bins[1:]):
            mask = (confidences >= lo) & (confidences < hi)
            if mask.sum() > 0:
                bin_acc = accuracies[mask].mean()
                bin_conf = confidences[mask].mean()
                ece += mask.sum() / len(y_true) * abs(bin_acc - bin_conf)
        return float(ece)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        """Return all accumulated evaluation results."""
        return dict(self.results)
