"""Evaluation script for TissueShift benchmark tracks.

Usage:
    python -m benchmarks.evaluate \\
        --track SubtypeCall \\
        --predictions submissions/SubtypeCall/my_team.json \\
        --labels data/tcga_brca/test_labels.json \\
        --output results/SubtypeCall/my_team.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

from benchmarks.metrics import TRACK_EVALUATORS, PRIMARY_METRICS

logger = logging.getLogger(__name__)


def load_predictions(path: str) -> dict:
    """Load prediction file."""
    with open(path) as f:
        data = json.load(f)
    return data


def load_labels(path: str) -> dict:
    """Load ground-truth labels."""
    with open(path) as f:
        data = json.load(f)
    return data


def validate_submission(predictions: dict, track: str) -> list[str]:
    """Validate submission format, return list of errors."""
    errors = []

    if "track" not in predictions:
        errors.append("Missing 'track' field")
    elif predictions["track"] != track:
        errors.append(f"Track mismatch: expected {track}, got {predictions['track']}")

    if "team" not in predictions:
        errors.append("Missing 'team' field")

    if "predictions" not in predictions:
        errors.append("Missing 'predictions' field")
    elif not isinstance(predictions["predictions"], (list, dict)):
        errors.append("'predictions' must be a list or dict")

    return errors


def evaluate_track(
    track: str,
    predictions: dict,
    labels: dict,
) -> dict[str, float]:
    """Evaluate predictions against labels for the given track."""
    evaluator = TRACK_EVALUATORS.get(track)
    if evaluator is None:
        raise ValueError(f"Unknown track: {track}")

    preds = predictions["predictions"]
    label_data = labels.get("labels", labels)

    if track == "SubtypeCall":
        sample_ids = [p["sample_id"] for p in preds]
        y_pred = np.array([p["prediction"] for p in preds])
        y_true = np.array([label_data[sid]["subtype"] for sid in sample_ids])
        y_prob = None
        if "probabilities" in preds[0]:
            y_prob = np.array([list(p["probabilities"].values()) for p in preds])
        return evaluator(y_true, y_pred, y_prob)

    elif track == "SubtypeDrift":
        sample_ids = [p["sample_id"] for p in preds]
        y_pred_prob = np.array([p["drift_probability"] for p in preds])
        y_true = np.array([label_data[sid]["drift"] for sid in sample_ids])
        return evaluator(y_true, y_pred_prob)

    elif track == "ProgressionStage":
        sample_ids = [p["sample_id"] for p in preds]
        y_pred = np.array([p["prediction"] for p in preds])
        y_true = np.array([label_data[sid]["stage"] for sid in sample_ids])
        return evaluator(y_true, y_pred)

    elif track == "Morph2Mol":
        sample_ids = [p["sample_id"] for p in preds]
        y_pred = np.array([p["gene_predictions"] for p in preds])
        y_true = np.array([label_data[sid]["expression"] for sid in sample_ids])
        return evaluator(y_true, y_pred)

    elif track == "Survival":
        sample_ids = [p["sample_id"] for p in preds]
        risk_scores = np.array([p["risk_score"] for p in preds])
        event_times = np.array([label_data[sid]["time"] for sid in sample_ids])
        event_indicators = np.array([label_data[sid]["event"] for sid in sample_ids])
        return evaluator(event_times, event_indicators, risk_scores)

    elif track == "SpatialPhenotype":
        sample_ids = [p["sample_id"] for p in preds]
        til_pred = np.array([p["til_density"] for p in preds])
        til_true = np.array([label_data[sid]["til_density"] for sid in sample_ids])
        return evaluator(til_true, til_pred)

    return {}


def main():
    parser = argparse.ArgumentParser(description="Evaluate TissueShift submission")
    parser.add_argument("--track", required=True, choices=list(TRACK_EVALUATORS.keys()))
    parser.add_argument("--predictions", required=True, help="Path to predictions JSON")
    parser.add_argument("--labels", required=True, help="Path to ground-truth labels JSON")
    parser.add_argument("--output", help="Path to save results JSON")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # Load
    predictions = load_predictions(args.predictions)
    labels = load_labels(args.labels)

    # Validate
    errors = validate_submission(predictions, args.track)
    if errors:
        logger.error(f"Submission validation failed: {errors}")
        sys.exit(1)

    # Evaluate
    metrics = evaluate_track(args.track, predictions, labels)
    primary_metric = PRIMARY_METRICS[args.track]
    primary_score = metrics.get(primary_metric, 0.0)

    # Results
    result = {
        "track": args.track,
        "team": predictions.get("team", "unknown"),
        "model": predictions.get("model", "unknown"),
        "primary_metric": primary_metric,
        "primary_score": primary_score,
        "all_metrics": metrics,
    }

    logger.info(f"Track: {args.track}")
    logger.info(f"Team: {result['team']}")
    logger.info(f"{primary_metric}: {primary_score:.4f}")
    for k, v in metrics.items():
        logger.info(f"  {k}: {v:.4f}")

    # Save
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Results saved to {output_path}")
    else:
        print(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    main()
