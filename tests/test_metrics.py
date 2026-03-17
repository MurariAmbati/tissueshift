"""Tests for benchmark metrics."""

from __future__ import annotations

import numpy as np

from benchmarks.metrics import (
    compute_subtype_call_metrics,
    compute_progression_metrics,
    compute_survival_metrics,
    compute_morph2mol_metrics,
    compute_spatial_phenotype_metrics,
)


def test_subtype_call_perfect():
    y_true = np.array([0, 1, 2, 3, 4, 0, 1, 2, 3, 4])
    y_pred = np.array([0, 1, 2, 3, 4, 0, 1, 2, 3, 4])
    metrics = compute_subtype_call_metrics(y_true, y_pred)
    assert metrics["macro_f1"] == 1.0
    assert metrics["cohen_kappa"] == 1.0
    assert metrics["balanced_accuracy"] == 1.0


def test_subtype_call_imperfect():
    y_true = np.array([0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    y_pred = np.array([0, 1, 1, 1, 2, 3, 3, 3, 4, 4])
    metrics = compute_subtype_call_metrics(y_true, y_pred)
    assert 0 < metrics["macro_f1"] < 1.0


def test_progression_ordinal():
    y_true = np.array([0, 1, 2, 3, 4])
    y_pred = np.array([0, 1, 2, 3, 4])
    metrics = compute_progression_metrics(y_true, y_pred)
    assert metrics["qwk"] == 1.0
    assert metrics["mae"] == 0.0


def test_survival_c_index():
    event_times = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    event_indicators = np.array([1, 1, 0, 1, 0])
    risk_scores = np.array([5.0, 4.0, 3.0, 2.0, 1.0])

    metrics = compute_survival_metrics(event_times, event_indicators, risk_scores)
    assert "c_index" in metrics
    assert 0 <= metrics["c_index"] <= 1


def test_morph2mol_r2():
    y_true = np.random.randn(20, 10)
    y_pred = y_true + np.random.randn(20, 10) * 0.1  # Near-perfect prediction
    metrics = compute_morph2mol_metrics(y_true, y_pred)
    assert metrics["mean_r2"] > 0.5


def test_spatial_phenotype():
    til_true = np.random.rand(20)
    til_pred = til_true + np.random.randn(20) * 0.05
    metrics = compute_spatial_phenotype_metrics(til_true, til_pred)
    assert "r2_til" in metrics
