"""Tests for checkpoint utilities."""

import pytest
import shutil
import tempfile
import torch
import torch.nn as nn

from tissueshift.training.checkpointing import (
    TopKCheckpointManager,
    ExponentialMovingAverage,
    average_checkpoints,
    find_best_checkpoint,
)


class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(10, 5)

    def forward(self, x):
        return self.fc(x)


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestTopKCheckpointManager:
    def test_saves_checkpoints(self, tmp_dir):
        mgr = TopKCheckpointManager(tmp_dir, top_k=2, mode="min")
        model = SimpleModel()
        path = mgr.save(model, score=0.5, epoch=1, stage=0)
        assert path is not None
        assert len(mgr.all_checkpoints) == 1

    def test_keeps_only_top_k(self, tmp_dir):
        mgr = TopKCheckpointManager(tmp_dir, top_k=2, mode="min")
        model = SimpleModel()
        mgr.save(model, score=0.3, epoch=1)
        mgr.save(model, score=0.1, epoch=2)
        mgr.save(model, score=0.2, epoch=3)
        # Should keep the two best (0.1, 0.2) and discard 0.3
        assert len(mgr.all_checkpoints) == 2
        scores = [c["score"] for c in mgr.all_checkpoints]
        assert 0.3 not in scores

    def test_rejects_worse_checkpoint(self, tmp_dir):
        mgr = TopKCheckpointManager(tmp_dir, top_k=2, mode="min")
        model = SimpleModel()
        mgr.save(model, score=0.1, epoch=1)
        mgr.save(model, score=0.2, epoch=2)
        path = mgr.save(model, score=0.5, epoch=3)
        assert path is None  # rejected

    def test_best_path(self, tmp_dir):
        mgr = TopKCheckpointManager(tmp_dir, top_k=3, mode="min")
        model = SimpleModel()
        mgr.save(model, score=0.5, epoch=1)
        mgr.save(model, score=0.1, epoch=2)
        mgr.save(model, score=0.3, epoch=3)
        assert "score0.1" in mgr.best_path

    def test_max_mode(self, tmp_dir):
        mgr = TopKCheckpointManager(tmp_dir, top_k=2, mode="max")
        model = SimpleModel()
        mgr.save(model, score=0.8, epoch=1)
        mgr.save(model, score=0.9, epoch=2)
        mgr.save(model, score=0.7, epoch=3)
        scores = [c["score"] for c in mgr.all_checkpoints]
        assert 0.7 not in scores
        assert mgr.best_score == 0.9


class TestExponentialMovingAverage:
    def test_update_changes_shadow(self):
        model = SimpleModel()
        ema = ExponentialMovingAverage(model, decay=0.9)
        original_shadow = {k: v.clone() for k, v in ema.shadow.items()}

        # Change model weights
        with torch.no_grad():
            for p in model.parameters():
                p.add_(torch.ones_like(p))
        ema.update(model)

        # Shadow should have moved toward new weights
        for name in ema.shadow:
            assert not torch.equal(ema.shadow[name], original_shadow[name])

    def test_apply_and_restore(self):
        model = SimpleModel()
        ema = ExponentialMovingAverage(model, decay=0.9)

        original_weights = {n: p.data.clone() for n, p in model.named_parameters()}

        # Modify model
        with torch.no_grad():
            for p in model.parameters():
                p.add_(torch.ones_like(p) * 10)

        ema.update(model)
        ema.apply(model)

        # Weights should now be EMA shadow
        for n, p in model.named_parameters():
            if n in ema.shadow:
                assert torch.allclose(p.data, ema.shadow[n])

        ema.restore(model)

        # Weights should be back to modified values (not original)
        for n, p in model.named_parameters():
            assert not torch.allclose(p.data, original_weights[n])

    def test_state_dict_roundtrip(self):
        model = SimpleModel()
        ema = ExponentialMovingAverage(model, decay=0.995)
        state = ema.state_dict()

        ema2 = ExponentialMovingAverage(model, decay=0.5)
        ema2.load_state_dict(state)

        assert ema2.decay == 0.995
        for key in ema.shadow:
            assert torch.equal(ema.shadow[key], ema2.shadow[key])


class TestAverageCheckpoints:
    def test_averages_weights(self, tmp_dir):
        model1 = SimpleModel()
        model2 = SimpleModel()

        # Set distinct weights
        with torch.no_grad():
            for p in model1.parameters():
                p.fill_(2.0)
            for p in model2.parameters():
                p.fill_(4.0)

        path1 = f"{tmp_dir}/ckpt1.pt"
        path2 = f"{tmp_dir}/ckpt2.pt"
        torch.save({"model_state_dict": model1.state_dict()}, path1)
        torch.save({"model_state_dict": model2.state_dict()}, path2)

        avg_model = SimpleModel()
        avg_model = average_checkpoints([path1, path2], avg_model)

        # Each param should be 3.0 (average of 2 and 4)
        for p in avg_model.parameters():
            assert torch.allclose(p.data, torch.full_like(p.data, 3.0))

    def test_empty_paths_raises(self):
        with pytest.raises(ValueError, match="No checkpoint"):
            average_checkpoints([], SimpleModel())


class TestFindBestCheckpoint:
    def test_finds_best_min(self, tmp_dir):
        # Create dummy checkpoint files
        for score in [0.5, 0.2, 0.8]:
            path = f"{tmp_dir}/stage0_epoch1_score{score:.4f}.pt"
            torch.save({}, path)

        best = find_best_checkpoint(tmp_dir, mode="min")
        assert "score0.2000" in best

    def test_finds_best_max(self, tmp_dir):
        for score in [0.5, 0.2, 0.8]:
            path = f"{tmp_dir}/stage0_epoch1_score{score:.4f}.pt"
            torch.save({}, path)

        best = find_best_checkpoint(tmp_dir, mode="max")
        assert "score0.8000" in best

    def test_returns_none_empty_dir(self, tmp_dir):
        assert find_best_checkpoint(tmp_dir) is None
