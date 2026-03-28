"""Biomarker discovery via latent-space interrogation.

Mines the TissueShift shared latent manifold (128-dim) and the
biological knowledge graph to discover putative novel biomarkers that
discriminate molecular subtypes, predict treatment outcome, or
correlate with survival.

Key Components
--------------
* **LatentAxisInterpreter** — maps each latent axis to biological concepts
  using the decoder Jacobian and knowledge-graph annotations.
* **DifferentialLatentAnalysis** — compares latent representations between
  cohorts (e.g. responders vs non-responders) to identify discriminative
  axes and the genes/pathways they encode.
* **SurvivalAssociationScanner** — scans all latent dims for univariate
  and multivariate Cox-PH survival associations.
* **BiomarkerPanel** — selects a minimal panel of latent features that
  jointly classify subtypes with high AUROC, regularised via group lasso.
* **NoveltyScorer** — checks discovered latent axes against known
  biomarker databases to flag truly novel findings.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ===================================================================
# Configuration
# ===================================================================

@dataclass
class BiomarkerConfig:
    """Biomarker discovery parameters."""

    latent_dim: int = 128
    n_tissue_axes: int = 8
    top_k_genes: int = 50
    fdr_threshold: float = 0.05
    survival_n_bins: int = 4
    panel_max_size: int = 10
    panel_regularisation: float = 0.01
    known_biomarkers: List[str] = field(default_factory=lambda: [
        "ESR1", "PGR", "ERBB2", "MKI67", "TP53", "BRCA1", "BRCA2",
        "PIK3CA", "CDH1", "GATA3", "FOXA1", "MAP3K1", "PTEN",
    ])


# ===================================================================
# Latent Axis Interpreter
# ===================================================================

class LatentAxisInterpreter:
    """Interpret each latent dimension biologially via decoder Jacobian.

    Given a decoder that maps z → gene expression, the Jacobian
    ∂ĝ/∂z_k tells us which genes are most sensitive to latent axis k.
    Combined with KG annotations, we can label each axis.
    """

    @staticmethod
    @torch.enable_grad()
    def compute_jacobian(
        decoder: nn.Module,
        z_ref: torch.Tensor,
        device: str = "cpu",
    ) -> torch.Tensor:
        """Compute Jacobian ∂decoder(z)/∂z at reference point.

        Parameters
        ----------
        decoder : maps (B, D_z) → (B, D_gene)
        z_ref : (1, D_z) reference latent vector (e.g. population mean)

        Returns
        -------
        J : (D_gene, D_z)
        """
        z = z_ref.clone().detach().to(device).requires_grad_(True)
        out = decoder(z)
        if isinstance(out, dict):
            out = out.get("gene_expression", out.get("reconstruction", next(iter(out.values()))))
        out = out.squeeze(0)  # (D_gene,)

        D_gene = out.shape[0]
        D_z = z.shape[1]
        J = torch.zeros(D_gene, D_z, device=device)

        for g in range(D_gene):
            if z.grad is not None:
                z.grad.zero_()
            out[g].backward(retain_graph=True)
            J[g] = z.grad.squeeze(0).clone()

        return J.detach().cpu()

    @staticmethod
    def top_genes_per_axis(
        jacobian: torch.Tensor,
        gene_names: List[str],
        top_k: int = 20,
    ) -> Dict[int, List[Tuple[str, float]]]:
        """For each latent axis, find genes with largest |dg/dz_k|.

        Returns
        -------
        Dict mapping axis index → list of (gene_name, sensitivity).
        """
        D_z = jacobian.shape[1]
        result: Dict[int, List[Tuple[str, float]]] = {}
        for k in range(D_z):
            col = jacobian[:, k].abs()
            topk_vals, topk_idx = col.topk(min(top_k, len(col)))
            result[k] = [
                (gene_names[i], float(topk_vals[j]))
                for j, i in enumerate(topk_idx.tolist())
            ]
        return result

    @staticmethod
    def axis_pathway_enrichment(
        axis_genes: List[Tuple[str, float]],
        pathway_db: Dict[str, List[str]],
        n_background: int = 20000,
    ) -> List[Dict[str, Any]]:
        """Fisher-exact-style enrichment of axis genes against pathways.

        Uses a hypergeometric-approximation p-value.
        """
        gene_set = {g for g, _ in axis_genes}
        K = len(gene_set)
        results = []

        for pathway, pw_genes in pathway_db.items():
            pw_set = set(pw_genes)
            overlap = gene_set & pw_set
            if not overlap:
                continue

            # Hypergeometric p-value approximation
            M = n_background  # total genes
            n = len(pw_set)  # pathway size
            k = len(overlap)

            # Use scipy if available, else approximate
            try:
                from scipy.stats import hypergeom
                pval = hypergeom.sf(k - 1, M, n, K)
            except ImportError:
                # Rough approximation
                expected = K * n / M
                if k <= expected:
                    pval = 1.0
                else:
                    pval = math.exp(-2 * (k - expected) ** 2 / max(K, 1))

            results.append({
                "pathway": pathway,
                "overlap_genes": sorted(overlap),
                "overlap_count": k,
                "pathway_size": n,
                "p_value": pval,
            })

        results.sort(key=lambda x: x["p_value"])
        return results


# ===================================================================
# Differential Latent Analysis
# ===================================================================

class DifferentialLatentAnalysis:
    """Compare latent representations between two cohorts to find
    discriminative latent axes.

    Uses Welch's t-test per axis with BH-FDR correction.
    """

    @staticmethod
    def compare_cohorts(
        z_group_a: torch.Tensor,  # (Na, D)
        z_group_b: torch.Tensor,  # (Nb, D)
        axis_names: Optional[List[str]] = None,
        fdr_threshold: float = 0.05,
    ) -> Dict[str, Any]:
        """Perform differential latent analysis.

        Returns
        -------
        Dict with per-axis statistics and significant axes.
        """
        D = z_group_a.shape[1]
        a = z_group_a.numpy() if isinstance(z_group_a, torch.Tensor) else z_group_a
        b = z_group_b.numpy() if isinstance(z_group_b, torch.Tensor) else z_group_b

        results_per_axis = []
        p_values = []

        for d in range(D):
            a_d = a[:, d]
            b_d = b[:, d]

            mean_a, mean_b = a_d.mean(), b_d.mean()
            var_a, var_b = a_d.var(ddof=1), b_d.var(ddof=1)
            na, nb = len(a_d), len(b_d)

            se = math.sqrt(var_a / na + var_b / nb + 1e-10)
            t_stat = (mean_a - mean_b) / se

            # Welch's df
            num = (var_a / na + var_b / nb) ** 2
            denom = (var_a / na) ** 2 / (na - 1) + (var_b / nb) ** 2 / (nb - 1) + 1e-10
            df = num / denom

            # Two-tailed p-value via t-distribution approximation
            try:
                from scipy.stats import t as t_dist
                pval = 2 * t_dist.sf(abs(t_stat), df)
            except ImportError:
                # Normal approximation for large df
                pval = 2 * (1 - _normal_cdf(abs(t_stat)))

            effect_size = (mean_a - mean_b) / math.sqrt((var_a + var_b) / 2 + 1e-10)

            results_per_axis.append({
                "axis": d,
                "name": axis_names[d] if axis_names and d < len(axis_names) else f"z_{d}",
                "mean_a": float(mean_a),
                "mean_b": float(mean_b),
                "t_statistic": float(t_stat),
                "p_value": float(pval),
                "effect_size_cohens_d": float(effect_size),
            })
            p_values.append(pval)

        # BH-FDR correction
        adjusted = _benjamini_hochberg(p_values)
        for i, r in enumerate(results_per_axis):
            r["adjusted_p_value"] = adjusted[i]
            r["significant"] = adjusted[i] < fdr_threshold

        significant = [r for r in results_per_axis if r["significant"]]
        significant.sort(key=lambda x: abs(x["effect_size_cohens_d"]), reverse=True)

        return {
            "all_axes": results_per_axis,
            "significant_axes": significant,
            "n_significant": len(significant),
            "group_a_size": len(a),
            "group_b_size": len(b),
        }


# ===================================================================
# Survival Association Scanner
# ===================================================================

class SurvivalAssociationScanner:
    """Scan latent dims for survival associations.

    Uses a simplified log-rank test per axis (split at median).
    For production, integrate with lifelines or scikit-survival.
    """

    @staticmethod
    def scan_axes(
        z: torch.Tensor,          # (N, D)
        times: torch.Tensor,      # (N,) survival times
        events: torch.Tensor,     # (N,) 1=event, 0=censored
        fdr_threshold: float = 0.05,
    ) -> Dict[str, Any]:
        """Log-rank test for each latent axis (median split)."""
        z_np = z.numpy() if isinstance(z, torch.Tensor) else z
        t_np = times.numpy() if isinstance(times, torch.Tensor) else times
        e_np = events.numpy() if isinstance(events, torch.Tensor) else events

        D = z_np.shape[1]
        results = []
        pvals = []

        for d in range(D):
            median = np.median(z_np[:, d])
            high = z_np[:, d] >= median
            low = ~high

            # Simplified log-rank statistic
            O_high = e_np[high].sum()
            O_low = e_np[low].sum()
            N_high = high.sum()
            N_low = low.sum()
            N_total = N_high + N_low
            O_total = O_high + O_low

            E_high = O_total * N_high / max(N_total, 1)
            E_low = O_total * N_low / max(N_total, 1)

            chi2 = (O_high - E_high) ** 2 / max(E_high, 1e-6) + \
                   (O_low - E_low) ** 2 / max(E_low, 1e-6)

            try:
                from scipy.stats import chi2 as chi2_dist
                pval = chi2_dist.sf(chi2, df=1)
            except ImportError:
                pval = math.exp(-chi2 / 2)

            # Hazard ratio approximation
            hr = (O_high / max(N_high, 1)) / (O_low / max(N_low, 1) + 1e-6)

            results.append({
                "axis": d,
                "chi2_statistic": float(chi2),
                "p_value": float(pval),
                "hazard_ratio_approx": float(hr),
                "n_high": int(N_high),
                "n_low": int(N_low),
            })
            pvals.append(pval)

        adjusted = _benjamini_hochberg(pvals)
        for i, r in enumerate(results):
            r["adjusted_p_value"] = adjusted[i]
            r["significant"] = adjusted[i] < fdr_threshold

        significant = [r for r in results if r["significant"]]
        significant.sort(key=lambda x: x["chi2_statistic"], reverse=True)

        return {
            "all_axes": results,
            "significant_axes": significant,
            "n_significant": len(significant),
        }


# ===================================================================
# Biomarker Panel Selection
# ===================================================================

class BiomarkerPanel:
    """Select a compact panel of latent features for clinical use.

    Uses L1-regularised logistic regression (sparse features) to find
    the minimal set of latent axes that distinguish subtypes.
    """

    def __init__(self, cfg: BiomarkerConfig = BiomarkerConfig()):
        self.cfg = cfg
        self.selected_axes: List[int] = []
        self.weights: Optional[np.ndarray] = None

    def fit(
        self,
        z: torch.Tensor,    # (N, D)
        labels: torch.Tensor,  # (N,) integer subtype labels
    ) -> Dict[str, Any]:
        """Fit sparse panel selector."""
        z_np = z.numpy() if isinstance(z, torch.Tensor) else z
        y_np = labels.numpy() if isinstance(labels, torch.Tensor) else labels

        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import roc_auc_score
            from sklearn.preprocessing import StandardScaler

            scaler = StandardScaler()
            z_scaled = scaler.fit_transform(z_np)

            clf = LogisticRegression(
                penalty="l1",
                C=1.0 / max(self.cfg.panel_regularisation, 1e-6),
                solver="saga",
                max_iter=2000,
                multi_class="multinomial",
            )
            clf.fit(z_scaled, y_np)

            # Feature importance = sum of |coef| across classes
            importance = np.abs(clf.coef_).sum(axis=0)
            top_k = min(self.cfg.panel_max_size, (importance > 0).sum())
            selected = np.argsort(importance)[-top_k:][::-1].tolist()

            self.selected_axes = selected
            self.weights = importance

            # Evaluate panel
            z_panel = z_scaled[:, selected]
            clf_panel = LogisticRegression(max_iter=1000, multi_class="multinomial")
            clf_panel.fit(z_panel, y_np)
            probs = clf_panel.predict_proba(z_panel)

            n_classes = len(np.unique(y_np))
            if n_classes == 2:
                auroc = roc_auc_score(y_np, probs[:, 1])
            else:
                auroc = roc_auc_score(y_np, probs, multi_class="ovr", average="macro")

            return {
                "selected_axes": selected,
                "importance_scores": {int(i): float(importance[i]) for i in selected},
                "panel_size": len(selected),
                "panel_auroc": float(auroc),
                "total_axes_with_nonzero_weight": int((importance > 0).sum()),
            }

        except ImportError:
            logger.warning("scikit-learn required for BiomarkerPanel.fit()")
            return {"error": "scikit-learn not installed"}

    def evaluate_panel(
        self,
        z: torch.Tensor,
        labels: torch.Tensor,
    ) -> Dict[str, float]:
        """Evaluate selected panel on new data."""
        if not self.selected_axes:
            return {"error": "Panel not fitted yet"}

        z_panel = z[:, self.selected_axes].numpy()
        y = labels.numpy()

        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import accuracy_score, roc_auc_score
            from sklearn.model_selection import cross_val_score

            clf = LogisticRegression(max_iter=1000, multi_class="multinomial")
            scores = cross_val_score(clf, z_panel, y, cv=5, scoring="accuracy")

            return {
                "panel_axes": self.selected_axes,
                "cv_accuracy_mean": float(scores.mean()),
                "cv_accuracy_std": float(scores.std()),
            }
        except ImportError:
            return {"error": "scikit-learn not installed"}


# ===================================================================
# Novelty Scorer
# ===================================================================

class NoveltyScorer:
    """Score how 'novel' a discovered latent axis is relative to known
    biomarkers.

    If the top genes on an axis are already well-known biomarkers,
    the axis is less novel.  Axes dominated by genes NOT in the known
    set are flagged for further investigation.
    """

    def __init__(self, known_genes: Optional[List[str]] = None):
        self.known = set(known_genes or BiomarkerConfig().known_biomarkers)

    def score_axis(
        self,
        axis_genes: List[Tuple[str, float]],
    ) -> Dict[str, Any]:
        """Score novelty of an axis.

        Returns
        -------
        Dict with novelty_score (0–1, higher = more novel), known/novel genes.
        """
        if not axis_genes:
            return {"novelty_score": 0.0}

        known_found = []
        novel_found = []

        for gene, sensitivity in axis_genes:
            if gene.upper() in {g.upper() for g in self.known}:
                known_found.append((gene, sensitivity))
            else:
                novel_found.append((gene, sensitivity))

        total_sens = sum(s for _, s in axis_genes)
        novel_sens = sum(s for _, s in novel_found)
        novelty_score = novel_sens / (total_sens + 1e-10)

        return {
            "novelty_score": float(novelty_score),
            "n_known": len(known_found),
            "n_novel": len(novel_found),
            "known_genes": known_found[:10],
            "novel_genes": novel_found[:10],
            "interpretation": (
                "Highly novel — dominated by non-canonical genes"
                if novelty_score > 0.7
                else "Moderately novel — mix of known and unknown"
                if novelty_score > 0.3
                else "Low novelty — mostly known biomarkers"
            ),
        }

    def rank_axes_by_novelty(
        self,
        axes_genes: Dict[int, List[Tuple[str, float]]],
    ) -> List[Dict[str, Any]]:
        """Rank all axes by novelty score."""
        results = []
        for axis_id, genes in axes_genes.items():
            info = self.score_axis(genes)
            info["axis"] = axis_id
            results.append(info)
        results.sort(key=lambda x: x["novelty_score"], reverse=True)
        return results


# ===================================================================
# Utilities
# ===================================================================

def _normal_cdf(x: float) -> float:
    """Approximate standard normal CDF."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _benjamini_hochberg(p_values: List[float]) -> List[float]:
    """Benjamini-Hochberg FDR correction."""
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * n
    prev = 1.0
    for rank_minus_1 in range(n - 1, -1, -1):
        orig_idx, pval = indexed[rank_minus_1]
        rank = rank_minus_1 + 1
        adj = min(prev, pval * n / rank)
        adj = min(adj, 1.0)
        adjusted[orig_idx] = adj
        prev = adj
    return adjusted
