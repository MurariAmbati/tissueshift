"""Subtype prediction and risk scoring endpoints."""

from __future__ import annotations

import random
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────

class SubtypeProbabilities(BaseModel):
    luminal_a: float
    luminal_b: float
    her2_enriched: float
    basal: float
    normal_like: float
    claudin_low: float


class UncertaintyDecomposition(BaseModel):
    aleatoric: float
    epistemic: float
    total: float
    conformal_set: list[str]
    conformal_alpha: float


class PredictionResponse(BaseModel):
    patient_id: str
    predicted_subtype: str
    probabilities: SubtypeProbabilities
    risk_score: float
    confidence: float
    uncertainty: UncertaintyDecomposition
    survival_months: dict[str, float]  # {"1yr": ..., "2yr": ..., "5yr": ...}


class BatchPredictionRequest(BaseModel):
    patient_ids: list[str] = Field(..., min_length=1, max_length=100)


SUBTYPES = ["luminal_a", "luminal_b", "her2_enriched", "basal", "normal_like", "claudin_low"]


def _simulate_prediction(patient_id: str) -> dict:
    """Generate a simulated prediction for demo purposes."""
    probs = [random.random() for _ in range(6)]
    total = sum(probs)
    probs = [round(p / total, 4) for p in probs]
    predicted = SUBTYPES[probs.index(max(probs))]
    risk = round(random.uniform(0.05, 0.95), 3)
    aleatoric = round(random.uniform(0.01, 0.15), 4)
    epistemic = round(random.uniform(0.005, 0.10), 4)

    conformal_set_size = random.randint(1, 3)
    conformal_set = random.sample(SUBTYPES, conformal_set_size)
    if predicted not in conformal_set:
        conformal_set[0] = predicted

    return dict(
        patient_id=patient_id,
        predicted_subtype=predicted,
        probabilities=dict(zip(SUBTYPES, probs)),
        risk_score=risk,
        confidence=round(1 - aleatoric - epistemic, 4),
        uncertainty=dict(
            aleatoric=aleatoric,
            epistemic=epistemic,
            total=round(aleatoric + epistemic, 4),
            conformal_set=conformal_set,
            conformal_alpha=0.05,
        ),
        survival_months={
            "1yr": round(random.uniform(0.75, 0.99), 3),
            "2yr": round(random.uniform(0.55, 0.95), 3),
            "5yr": round(random.uniform(0.30, 0.85), 3),
        },
    )


@router.get("/{patient_id}", response_model=PredictionResponse)
async def predict_patient(patient_id: str):
    """Run subtype + risk prediction for one patient."""
    return _simulate_prediction(patient_id)


@router.post("/batch", response_model=list[PredictionResponse])
async def predict_batch(body: BatchPredictionRequest):
    """Run predictions for a batch of patients."""
    return [_simulate_prediction(pid) for pid in body.patient_ids]
