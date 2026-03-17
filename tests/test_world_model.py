"""Tests for world model components."""

from __future__ import annotations

import pytest
import torch


def test_cross_attention_fusion():
    from world_model.fusion import CrossAttentionFusion

    fusion = CrossAttentionFusion(
        path_dim=512, mol_dim=256, spat_dim=128, hidden_dim=512
    )
    z_path = torch.randn(4, 512)
    z_mol = torch.randn(4, 256)
    z_spat = torch.randn(4, 128)

    z_fused = fusion(z_path, z_mol, z_spat)
    assert z_fused.shape == (4, 512)


def test_modality_dropout_fusion():
    from world_model.fusion import ModalityDropoutFusion

    fusion = ModalityDropoutFusion(
        path_dim=512, mol_dim=256, spat_dim=128, hidden_dim=512,
        modality_drop_prob=0.5,
    )
    z_path = torch.randn(4, 512)
    z_mol = torch.randn(4, 256)
    z_spat = torch.randn(4, 128)

    # Training mode — dropout may fire
    fusion.train()
    z_train = fusion(z_path, z_mol, z_spat)
    assert z_train.shape == (4, 512)

    # Eval mode — no dropout
    fusion.eval()
    z_eval = fusion(z_path, z_mol, z_spat)
    assert z_eval.shape == (4, 512)


def test_manifold_projector():
    from world_model.manifold import ManifoldProjector

    proj = ManifoldProjector(input_dim=512, proj_dim=256)
    z = torch.randn(4, 512)
    p = proj(z)
    assert p.shape == (4, 256)


def test_vicreg_loss():
    from world_model.manifold import VICRegLoss

    loss_fn = VICRegLoss()
    z1 = torch.randn(32, 256)
    z2 = torch.randn(32, 256)

    out = loss_fn(z1, z2)
    assert "loss" in out
    assert "invariance" in out
    assert "variance" in out
    assert "covariance" in out
    assert out["loss"].requires_grad


def test_contrastive_loss():
    from world_model.manifold import SubtypeContrastiveLoss

    loss_fn = SubtypeContrastiveLoss()
    features = torch.randn(16, 256)
    labels = torch.randint(0, 5, (16,))

    loss = loss_fn(features, labels)
    assert loss.shape == ()
    assert loss.requires_grad


def test_transition_model():
    from world_model.transition import SubtypeTransitionModel

    model = SubtypeTransitionModel(state_dim=512, n_subtypes=5)
    state = torch.randn(4, 512)

    out = model(state)
    assert out["subtype_logits"].shape == (4, 5)
    assert out["subtype_probs"].shape == (4, 5)
    assert out["transition_logits"].shape == (4, 5)
    assert out["transition_probs"].shape == (4, 5)

    # Probs should sum to ~1
    assert torch.allclose(out["subtype_probs"].sum(dim=-1), torch.ones(4), atol=1e-5)


def test_tissue_state_world_model():
    from world_model.tissue_state import TissueStateWorldModel

    model = TissueStateWorldModel(
        path_dim=512, mol_dim=256, spat_dim=128, state_dim=512, n_subtypes=5
    )
    z_path = torch.randn(4, 512)
    z_mol = torch.randn(4, 256)
    z_spat = torch.randn(4, 128)

    out = model(z_path, z_mol, z_spat)
    assert out.state.shape == (4, 512)
    assert out.manifold_proj.shape[0] == 4
    assert out.subtype_logits.shape == (4, 5)
    assert out.transition_probs.shape == (4, 5)


def test_tissue_state_encode():
    from world_model.tissue_state import TissueStateWorldModel

    model = TissueStateWorldModel(state_dim=512)
    z_path = torch.randn(2, 512)
    z_mol = torch.randn(2, 256)
    z_spat = torch.randn(2, 128)

    state = model.encode(z_path, z_mol, z_spat)
    assert state.shape == (2, 512)
