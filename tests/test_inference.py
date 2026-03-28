"""Tests for the inference pipeline."""

import pytest
import torch
from unittest.mock import MagicMock, patch

from tissueshift.inference import InferencePipeline, TissueShiftPrediction


class TestTissueShiftPrediction:
    def test_to_dict_empty(self):
        pred = TissueShiftPrediction(sample_id="test")
        d = pred.to_dict()
        assert d["sample_id"] == "test"
        # None fields should be excluded
        assert "tissue_state" not in d

    def test_to_dict_with_data(self):
        import numpy as np
        pred = TissueShiftPrediction(
            sample_id="s1",
            tissue_state=np.array([1.0, 2.0, 3.0]),
            subtype_confidence=0.95,
            tissue_axes={"axis1": 0.5, "axis2": -0.3},
        )
        d = pred.to_dict()
        assert d["sample_id"] == "s1"
        assert d["tissue_state"] == [1.0, 2.0, 3.0]
        assert d["subtype_confidence"] == 0.95
        assert d["tissue_axes"]["axis1"] == 0.5


class TestInferencePipeline:
    def test_predict_no_input_returns_empty(self):
        mock_model = MagicMock()
        mock_config = MagicMock()
        pipeline = InferencePipeline(mock_model, mock_config, device="cpu")
        pred = pipeline.predict(sample_id="empty")
        assert pred.sample_id == "empty"
        assert pred.tissue_state is None

    def test_predict_with_gene_expression(self):
        # Create a mock model that returns expected structure
        mock_model = MagicMock()
        mock_model.eval = MagicMock()
        mock_model.to = MagicMock(return_value=mock_model)
        mock_model.parameters = MagicMock(return_value=iter([torch.zeros(1)]))

        # Mock forward to return tissue state
        mock_model.__call__ = MagicMock(return_value={
            "tissue_state": torch.randn(1, 32),
        })

        mock_config = MagicMock()
        pipeline = InferencePipeline(mock_model, mock_config, device="cpu")
        expr = torch.randn(2000)
        pred = pipeline.predict(gene_expression=expr, sample_id="test_mol")
        assert pred.sample_id == "test_mol"


class TestInferencePredictionSerialization:
    def test_roundtrip(self):
        import json
        import numpy as np
        pred = TissueShiftPrediction(
            sample_id="patient_001",
            subtype_pam50_probs=np.array([0.1, 0.2, 0.3, 0.2, 0.2]),
            progression_ordinal_score=0.45,
            risk_score=-1.2,
        )
        d = pred.to_dict()
        serialized = json.dumps(d)
        deserialized = json.loads(serialized)
        assert deserialized["sample_id"] == "patient_001"
        assert len(deserialized["subtype_pam50_probs"]) == 5
        assert abs(deserialized["progression_ordinal_score"] - 0.45) < 1e-6
