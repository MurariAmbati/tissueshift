"""Tests for experiment tracking."""

import json
import tempfile
import shutil

import pytest

from tissueshift.tracking import JSONTracker, ExperimentTracker


class TestJSONTracker:
    def test_log_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            tracker = JSONTracker(output_dir=d, run_name="test")
            tracker.log_metrics({"loss": 0.5, "accuracy": 0.8}, step=0)
            tracker.log_metrics({"loss": 0.3, "accuracy": 0.9}, step=1)

            with open(tracker.metrics_path) as f:
                lines = f.readlines()
            assert len(lines) == 2
            record = json.loads(lines[0])
            assert record["step"] == 0
            assert record["loss"] == 0.5

    def test_log_config(self):
        with tempfile.TemporaryDirectory() as d:
            tracker = JSONTracker(output_dir=d, run_name="test")
            tracker.log_config({"lr": 1e-4, "batch_size": 32})

            with open(tracker.config_path) as f:
                config = json.load(f)
            assert config["lr"] == 1e-4

    def test_log_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            tracker = JSONTracker(output_dir=d, run_name="test")
            tracker.log_artifact("/path/to/model.pt", "best_model", "model")

    def test_log_text(self):
        with tempfile.TemporaryDirectory() as d:
            tracker = JSONTracker(output_dir=d, run_name="test")
            tracker.log_text("note", "Stage 1 complete", step=100)
            with open(tracker.text_path) as f:
                record = json.loads(f.readline())
            assert record["key"] == "note"


class TestExperimentTracker:
    def test_json_backend(self):
        with tempfile.TemporaryDirectory() as d:
            tracker = ExperimentTracker(
                backends=["json"],
                log_dir=d,
                run_name="unit_test",
                config={"test": True},
            )
            tracker.log_metrics({"loss": 0.5})
            tracker.log_epoch(stage=0, epoch=1, train_loss=0.4, val_loss=0.5, lr=1e-4)
            tracker.log_stage(0, "pathology_pretraining")
            tracker.finish()

    def test_step_increments(self):
        with tempfile.TemporaryDirectory() as d:
            tracker = ExperimentTracker(backends=["json"], log_dir=d)
            assert tracker.step == 0
            tracker.log_epoch(stage=0, epoch=1, train_loss=0.5)
            assert tracker.step == 1
            tracker.log_epoch(stage=0, epoch=2, train_loss=0.4)
            assert tracker.step == 2
