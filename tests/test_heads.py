"""Tests for prediction heads."""

from __future__ import annotations

import torch


def test_subtype_head():
    from heads.predictions import SubtypeHead

    head = SubtypeHead(state_dim=512, n_subtypes=5)
    state = torch.randn(4, 512)
    logits = head(state)
    assert logits.shape == (4, 5)


def test_drift_head():
    from heads.predictions import DriftHead

    head = DriftHead(state_dim=512)
    s1 = torch.randn(4, 512)
    s2 = torch.randn(4, 512)
    out = head(s1, s2)
    assert out["drift_logit"].shape == (4,)
    assert out["target_subtype_logits"].shape == (4, 5)


def test_progression_head():
    from heads.predictions import ProgressionHead

    head = ProgressionHead(state_dim=512, n_stages=5)
    state = torch.randn(4, 512)
    out = head(state)
    assert out["cumulative_logits"].shape == (4, 4)
    assert out["stage_probs"].shape == (4, 5)
    # Probs should sum to ~1
    assert torch.allclose(
        out["stage_probs"].sum(dim=-1), torch.ones(4), atol=0.01
    )


def test_survival_head():
    from heads.predictions import SurvivalHead

    head = SurvivalHead(state_dim=512, n_intervals=10)
    state = torch.randn(4, 512)
    out = head(state)
    assert out["hazard_logits"].shape == (4, 10)
    assert out["hazard"].shape == (4, 10)
    assert out["survival"].shape == (4, 10)
    # Survival should be monotonically decreasing
    for i in range(4):
        for t in range(1, 10):
            assert out["survival"][i, t] <= out["survival"][i, t - 1] + 1e-6


def test_morph2mol_head():
    from heads.predictions import Morph2MolHead

    head = Morph2MolHead(state_dim=512, n_genes=250, n_pathways=50)
    state = torch.randn(4, 512)
    out = head(state)
    assert out["gene_pred"].shape == (4, 250)
    assert out["pathway_pred"].shape == (4, 50)


def test_microenvironment_head():
    from heads.predictions import MicroenvironmentHead

    head = MicroenvironmentHead(state_dim=512)
    state = torch.randn(4, 512)
    out = head(state)
    assert out["til_density"].shape == (4,)
    assert out["stromal_fraction"].shape == (4,)
    assert out["immune_composition"].shape == (4, 8)
    # Immune composition should sum to ~1
    assert torch.allclose(
        out["immune_composition"].sum(dim=-1), torch.ones(4), atol=1e-5
    )


def test_tissueshift_heads_bundle():
    from heads.predictions import TissueShiftHeads

    heads = TissueShiftHeads(state_dim=512)
    state = torch.randn(2, 512)

    # All heads should be callable
    assert heads.subtype(state).shape == (2, 5)
    survival = heads.survival(state)
    assert "hazard" in survival
    morph = heads.morph2mol(state)
    assert "gene_pred" in morph
