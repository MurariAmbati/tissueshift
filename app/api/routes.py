"""API route definitions."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Models ---

class SubtypePrediction(BaseModel):
    sample_id: str
    subtype: str
    confidence: float
    probabilities: dict[str, float]


class ManifoldPoint(BaseModel):
    id: str
    position: list[float]
    subtype: str
    confidence: float


class LeaderboardEntry(BaseModel):
    rank: int
    team: str
    model: str
    score: float
    date: str
    track: str


class SubmissionRequest(BaseModel):
    track: str
    team: str
    model_name: str
    predictions: list[dict]


# --- Endpoints ---

@router.get("/subtypes")
async def list_subtypes():
    """Return PAM50 subtype definitions."""
    return {
        "subtypes": [
            {"name": "LumA", "full_name": "Luminal A", "color": "#3b82f6"},
            {"name": "LumB", "full_name": "Luminal B", "color": "#6366f1"},
            {"name": "Her2", "full_name": "HER2-enriched", "color": "#ec4899"},
            {"name": "Basal", "full_name": "Basal-like", "color": "#ef4444"},
            {"name": "Normal", "full_name": "Normal-like", "color": "#10b981"},
        ]
    }


@router.get("/manifold")
async def get_manifold_points(n_samples: int = 250):
    """Return tissue state manifold points (UMAP projections)."""
    manifold_path = Path("data/manifold/umap_3d.json")
    if manifold_path.exists():
        with open(manifold_path) as f:
            points = json.load(f)
        return {"points": points[:n_samples]}

    # Return demo data if no real manifold computed
    import random
    subtypes = ["LumA", "LumB", "Her2", "Basal", "Normal"]
    centers = {
        "LumA": [-1.5, 0, -1],
        "LumB": [-0.5, 0.5, -0.5],
        "Her2": [1, 1, 0],
        "Basal": [2, -0.5, 1],
        "Normal": [-2, -1, 1],
    }
    points = []
    for i in range(n_samples):
        subtype = subtypes[i % len(subtypes)]
        cx, cy, cz = centers[subtype]
        points.append({
            "id": f"{subtype}_{i}",
            "position": [
                cx + random.gauss(0, 0.4),
                cy + random.gauss(0, 0.4),
                cz + random.gauss(0, 0.4),
            ],
            "subtype": subtype,
            "confidence": 0.6 + random.random() * 0.4,
        })
    return {"points": points}


@router.get("/leaderboard/{track}")
async def get_leaderboard(track: str):
    """Return leaderboard entries for a track."""
    valid_tracks = [
        "SubtypeCall", "SubtypeDrift", "ProgressionStage",
        "Morph2Mol", "Survival", "SpatialPhenotype",
    ]
    if track not in valid_tracks:
        raise HTTPException(404, f"Unknown track: {track}. Valid: {valid_tracks}")

    leaderboard_path = Path(f"data/leaderboard/{track}.json")
    if leaderboard_path.exists():
        with open(leaderboard_path) as f:
            return {"track": track, "entries": json.load(f)}

    # Demo baseline entries
    return {
        "track": track,
        "entries": [
            {
                "rank": 1,
                "team": "TissueShift-Base",
                "model": "UNI+ABMIL+CrossAttn",
                "score": 0.891 if track == "SubtypeCall" else 0.712,
                "date": "2024-01-15",
            }
        ],
    }


@router.post("/predict")
async def predict(file: UploadFile = File(...)):
    """Run inference on an uploaded slide (feature HDF5)."""
    if not file.filename or not file.filename.endswith(".h5"):
        raise HTTPException(400, "Upload an HDF5 feature file (.h5)")

    # In production, load model and run inference
    # For now return demo prediction
    return SubtypePrediction(
        sample_id=file.filename.replace(".h5", ""),
        subtype="LumA",
        confidence=0.87,
        probabilities={
            "LumA": 0.87,
            "LumB": 0.08,
            "Her2": 0.02,
            "Basal": 0.01,
            "Normal": 0.02,
        },
    )


@router.get("/tracks")
async def list_tracks():
    """Return all benchmark tracks with metadata."""
    return {
        "tracks": [
            {
                "name": "SubtypeCall",
                "metric": "Macro-F1",
                "target": 0.92,
                "description": "PAM50 subtype classification from WSI",
            },
            {
                "name": "SubtypeDrift",
                "metric": "AUROC",
                "target": 0.85,
                "description": "Predicting subtype changes in longitudinal samples",
            },
            {
                "name": "ProgressionStage",
                "metric": "QWK",
                "target": 0.80,
                "description": "Ordinal progression: Normal→ADH→DCIS→IDC→Metastatic",
            },
            {
                "name": "Morph2Mol",
                "metric": "R²",
                "target": 0.45,
                "description": "Predicting gene expression from morphology alone",
            },
            {
                "name": "Survival",
                "metric": "C-index",
                "target": 0.72,
                "description": "Overall survival prediction",
            },
            {
                "name": "SpatialPhenotype",
                "metric": "R²-TIL",
                "target": 0.50,
                "description": "TIL density and microenvironment composition",
            },
        ]
    }


@router.get("/model/info")
async def model_info():
    """Return model architecture and training information."""
    checkpoint_path = Path("checkpoints/best_model.pt")
    return {
        "name": "TissueShift-BRCA",
        "version": "0.1.0",
        "architecture": {
            "pathology_encoder": "UNI ViT-L/16 (frozen) + LoRA adapter",
            "aggregator": "ABMIL with gated attention",
            "molecular_encoder": "MLP (expression + pathway + proteomic)",
            "spatial_encoder": "Stub (Phase 11)",
            "fusion": "8-query cross-attention (2 layers)",
            "state_dim": 512,
        },
        "training": {
            "dataset": "TCGA-BRCA (1098 subjects)",
            "validation": "CPTAC-BRCA (198 subjects, external)",
            "stages": ["pretrain (subtype+manifold)", "finetune (all heads)"],
        },
        "checkpoint_available": checkpoint_path.exists(),
    }
