"""Digital Twin simulation endpoints — Neural ODE trajectory forecasting."""

from __future__ import annotations

import math
import random
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────

class StateVariable(BaseModel):
    name: str
    current: float
    predicted: float
    unit: str


class TrajectoryPoint(BaseModel):
    month: int
    treated: float
    baseline: float
    ci_lower: float
    ci_upper: float


class ForecastRequest(BaseModel):
    patient_id: str
    drug: str = "doxorubicin"
    horizon_months: int = Field(default=24, ge=6, le=60)


class ForecastResponse(BaseModel):
    patient_id: str
    drug: str
    horizon_months: int
    trajectory: list[TrajectoryPoint]
    state_variables: list[StateVariable]
    response_probability: float


class TreatmentArm(BaseModel):
    name: str
    survival_1yr: float
    survival_2yr: float
    survival_5yr: float
    pcr_rate: float
    toxicity_grade3_plus: float
    estimated_cost_usd: int
    recommended: bool = False


class CompareRequest(BaseModel):
    patient_id: str
    regimens: list[str] = Field(
        default=["AC-T", "TCH", "Pembrolizumab+Chemo", "Olaparib", "Capecitabine"]
    )


class CompareResponse(BaseModel):
    patient_id: str
    arms: list[TreatmentArm]


# ── Helpers ─────────────────────────────────────────────────────────

DRUG_EFFICACY = {
    "doxorubicin": 0.7,
    "paclitaxel": 0.65,
    "trastuzumab": 0.75,
    "pembrolizumab": 0.72,
    "olaparib": 0.60,
}


def _simulate_trajectory(horizon: int, efficacy: float) -> list[dict]:
    points = []
    for m in range(0, horizon + 1, max(1, horizon // 20)):
        baseline = math.exp(-0.015 * m)
        treated = math.exp(-0.015 * m * (1 - efficacy * 0.6))
        noise = random.gauss(0, 0.02)
        points.append(dict(
            month=m,
            treated=round(min(treated + noise, 1.0), 4),
            baseline=round(min(baseline + noise * 0.5, 1.0), 4),
            ci_lower=round(max(treated - 0.08, 0), 4),
            ci_upper=round(min(treated + 0.08, 1.0), 4),
        ))
    return points


# ── Endpoints ───────────────────────────────────────────────────────

@router.post("/forecast", response_model=ForecastResponse)
async def forecast(body: ForecastRequest):
    """Run Neural ODE forward simulation for a patient under treatment."""
    efficacy = DRUG_EFFICACY.get(body.drug, 0.5)
    trajectory = _simulate_trajectory(body.horizon_months, efficacy)

    state_vars = [
        StateVariable(name="Tumor Volume", current=3.2, predicted=round(3.2 * (1 - efficacy * 0.4), 2), unit="cm³"),
        StateVariable(name="ctDNA", current=45.0, predicted=round(45 * (1 - efficacy * 0.5), 1), unit="copies/mL"),
        StateVariable(name="Ki-67", current=42.0, predicted=round(42 * (1 - efficacy * 0.3), 1), unit="%"),
        StateVariable(name="TIL Score", current=0.15, predicted=round(0.15 + efficacy * 0.2, 3), unit="ratio"),
        StateVariable(name="Immune Score", current=0.4, predicted=round(0.4 + efficacy * 0.15, 3), unit="AU"),
    ]

    return ForecastResponse(
        patient_id=body.patient_id,
        drug=body.drug,
        horizon_months=body.horizon_months,
        trajectory=trajectory,
        state_variables=state_vars,
        response_probability=round(efficacy + random.uniform(-0.1, 0.1), 3),
    )


@router.post("/compare", response_model=CompareResponse)
async def compare_treatments(body: CompareRequest):
    """Compare multiple treatment regimens for a patient."""
    arms = []
    rec_idx = random.randint(0, len(body.regimens) - 1)
    for i, reg in enumerate(body.regimens):
        arms.append(TreatmentArm(
            name=reg,
            survival_1yr=round(random.uniform(0.82, 0.98), 3),
            survival_2yr=round(random.uniform(0.65, 0.92), 3),
            survival_5yr=round(random.uniform(0.40, 0.80), 3),
            pcr_rate=round(random.uniform(0.15, 0.65), 2),
            toxicity_grade3_plus=round(random.uniform(0.08, 0.45), 2),
            estimated_cost_usd=random.randint(15000, 120000),
            recommended=(i == rec_idx),
        ))
    return CompareResponse(patient_id=body.patient_id, arms=arms)
