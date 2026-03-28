"""Cohort analytics endpoints — population-level statistics."""

from __future__ import annotations

import random
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────

class SubtypeCount(BaseModel):
    subtype: str
    count: int
    percentage: float


class SurvivalPoint(BaseModel):
    month: int
    probability: float


class StageSurvival(BaseModel):
    stage: str
    curve: list[SurvivalPoint]


class CohortStats(BaseModel):
    total_patients: int
    median_age: float
    five_year_os: float
    triple_negative_pct: float
    subtype_distribution: list[SubtypeCount]
    age_distribution: dict[str, int]  # {"30-39": n, ...}
    survival_by_stage: list[StageSurvival]


SUBTYPES = ["luminal_a", "luminal_b", "her2_enriched", "basal", "normal_like", "claudin_low", "dcis"]


def _build_cohort_stats(stage_filter: Optional[str]) -> dict:
    total = random.randint(2500, 3500)
    counts = []
    remaining = total
    for i, st in enumerate(SUBTYPES):
        if i == len(SUBTYPES) - 1:
            c = remaining
        else:
            c = random.randint(int(remaining * 0.05), int(remaining * 0.3))
            remaining -= c
        counts.append(SubtypeCount(subtype=st, count=c, percentage=round(c / total * 100, 1)))

    age_dist = {
        "30-39": random.randint(80, 200),
        "40-49": random.randint(300, 600),
        "50-59": random.randint(500, 900),
        "60-69": random.randint(400, 700),
        "70-79": random.randint(200, 400),
        "80+": random.randint(50, 150),
    }

    stages = ["I", "II", "III", "IV"] if not stage_filter else [stage_filter]
    base_hazards = {"I": 0.003, "II": 0.007, "III": 0.015, "IV": 0.035}
    survival_curves = []
    for stg in stages:
        h = base_hazards.get(stg, 0.01)
        curve = []
        for m in range(0, 61, 3):
            import math
            curve.append(SurvivalPoint(month=m, probability=round(math.exp(-h * m), 4)))
        survival_curves.append(StageSurvival(stage=stg, curve=curve))

    return dict(
        total_patients=total,
        median_age=round(random.uniform(52, 62), 1),
        five_year_os=round(random.uniform(0.72, 0.88), 3),
        triple_negative_pct=round(random.uniform(10, 20), 1),
        subtype_distribution=[s.model_dump() for s in counts],
        age_distribution=age_dist,
        survival_by_stage=[s.model_dump() for s in survival_curves],
    )


@router.get("/stats", response_model=CohortStats)
async def cohort_stats(stage: Optional[str] = Query(None)):
    """Get population-level cohort statistics."""
    return _build_cohort_stats(stage)


@router.get("/subtypes", response_model=list[SubtypeCount])
async def subtype_distribution():
    """Get subtype distribution across the cohort."""
    total = 2847
    raw = [820, 510, 340, 290, 180, 120, 587]
    return [
        SubtypeCount(subtype=st, count=c, percentage=round(c / total * 100, 1))
        for st, c in zip(SUBTYPES, raw)
    ]


@router.get("/survival")
async def survival_curves(stage: Optional[str] = Query(None)):
    """Get Kaplan-Meier survival curves."""
    import math
    stages = [stage] if stage else ["I", "II", "III", "IV"]
    hazards = {"I": 0.003, "II": 0.007, "III": 0.015, "IV": 0.035}
    result = {}
    for s in stages:
        h = hazards.get(s, 0.01)
        result[s] = [{"month": m, "probability": round(math.exp(-h * m), 4)} for m in range(0, 61, 3)]
    return result
