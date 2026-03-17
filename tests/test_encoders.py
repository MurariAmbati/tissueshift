"""Tests for encoder modules."""

from __future__ import annotations

import pytest
import torch


def test_uni_encoder_passthrough():
    from encoders.pathology.uni_encoder import UNIEncoder

    encoder = UNIEncoder(feature_dim=1024, adapter_dim=None)
    x = torch.randn(2, 100, 1024)
    out = encoder(x)
    assert out.shape == (2, 100, 1024)
    assert torch.allclose(out, x)  # No adapter = passthrough


def test_uni_encoder_adapter():
    from encoders.pathology.uni_encoder import UNIEncoder

    encoder = UNIEncoder(feature_dim=1024, adapter_dim=64)
    x = torch.randn(2, 50, 1024)
    out = encoder(x)
    assert out.shape == (2, 50, 1024)
    # Adapter initialized near-zero, so output should be close to input
    assert torch.allclose(out, x, atol=0.1)


def test_region_tokenizer():
    from encoders.pathology.region_tokenizer import RegionTokenizer

    tokenizer = RegionTokenizer(feature_dim=1024, n_region_types=7)
    features = torch.randn(2, 100, 1024)
    coords = torch.randint(0, 5000, (2, 100, 2)).float()
    labels = torch.randint(0, 7, (2, 100))

    tokens, mask = tokenizer(features, coords, labels)
    assert tokens.shape == (2, 7, 1024)
    assert mask.shape == (2, 7)
    assert mask.dtype == torch.bool


def test_abmil():
    from encoders.pathology.slide_aggregator import ABMIL

    model = ABMIL(input_dim=1024, output_dim=512)
    tokens = torch.randn(4, 10, 1024)
    mask = torch.ones(4, 10, dtype=torch.bool)
    mask[0, 5:] = False  # Some tokens masked

    embedding, attn = model(tokens, mask)
    assert embedding.shape == (4, 512)
    assert attn.shape[0] == 4


def test_transmil():
    from encoders.pathology.slide_aggregator import TransMIL

    model = TransMIL(input_dim=1024, output_dim=512)
    tokens = torch.randn(4, 10, 1024)
    mask = torch.ones(4, 10, dtype=torch.bool)

    embedding, attn = model(tokens, mask)
    assert embedding.shape == (4, 512)


def test_molecular_encoder():
    from encoders.molecular.expression_encoder import MolecularEncoder

    encoder = MolecularEncoder(
        expression_dim=250, pathway_dim=50, proteomic_dim=200, output_dim=256
    )
    expr = torch.randn(4, 250)
    pathway = torch.randn(4, 50)
    prot = torch.randn(4, 200)
    prot_avail = torch.tensor([True, True, False, True])

    z_mol = encoder(expr, pathway, prot, prot_avail)
    assert z_mol.shape == (4, 256)


def test_molecular_encoder_missing_modalities():
    from encoders.molecular.expression_encoder import MolecularEncoder

    encoder = MolecularEncoder(output_dim=256)
    encoder.eval()  # No modality dropout in eval mode

    expr = torch.randn(4, 250)
    z_mol = encoder(expression=expr)
    assert z_mol.shape == (4, 256)


def test_spatial_encoder_stub():
    from encoders.spatial.graph_encoder import build_spatial_encoder

    encoder = build_spatial_encoder("stub", output_dim=128)
    z = encoder(batch_size=4)
    assert z.shape == (4, 128)


def test_build_slide_aggregator():
    from encoders.pathology.slide_aggregator import build_slide_aggregator

    for method in ["abmil", "transmil"]:
        model = build_slide_aggregator(method=method, input_dim=512, output_dim=256)
        tokens = torch.randn(2, 8, 512)
        emb, attn = model(tokens)
        assert emb.shape == (2, 256)
