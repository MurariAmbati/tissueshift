"""Federated learning orchestration endpoints."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────

class SiteStatus(BaseModel):
    site_id: str
    name: str
    institution: str
    patients: int
    status: str  # active | syncing | offline
    contribution: float
    last_sync: str
    dp_epsilon: float


class AggregationRound(BaseModel):
    round_num: int
    global_accuracy: float
    avg_loss: float
    participating_sites: int
    timestamp: str


class FederatedOverview(BaseModel):
    active_sites: int
    total_sites: int
    current_round: int
    global_accuracy: float
    privacy_budget_epsilon: float
    sites: list[SiteStatus]


class FederatedHistory(BaseModel):
    rounds: list[AggregationRound]


# ── Static demo data ───────────────────────────────────────────────

_BASE_SITES: list[dict] = [
    dict(site_id="msk", name="MSK Site", institution="Memorial Sloan Kettering",
         patients=1240, status="active", contribution=0.32, dp_epsilon=1.0),
    dict(site_id="mda", name="MDA Site", institution="MD Anderson Cancer Center",
         patients=980, status="active", contribution=0.28, dp_epsilon=1.2),
    dict(site_id="curie", name="Curie Site", institution="Institut Curie",
         patients=720, status="syncing", contribution=0.18, dp_epsilon=0.8),
    dict(site_id="ucsf", name="UCSF Site", institution="University of California SF",
         patients=580, status="active", contribution=0.15, dp_epsilon=1.5),
    dict(site_id="charite", name="Charité Site", institution="Charité – Universitätsmedizin Berlin",
         patients=410, status="offline", contribution=0.07, dp_epsilon=1.0),
]


def _build_overview() -> dict:
    now = datetime.utcnow()
    sites = []
    for s in _BASE_SITES:
        offset = random.randint(0, 180)
        last_sync = (now - timedelta(minutes=offset)).isoformat()
        sites.append(SiteStatus(**{**s, "last_sync": last_sync}))

    active = sum(1 for s in sites if s.status in ("active", "syncing"))
    return FederatedOverview(
        active_sites=active,
        total_sites=len(sites),
        current_round=42,
        global_accuracy=0.943,
        privacy_budget_epsilon=1.2,
        sites=sites,
    ).model_dump()


def _build_history(last_n: int = 10) -> dict:
    now = datetime.utcnow()
    rounds = []
    for i in range(last_n):
        r = 42 - (last_n - 1 - i)
        rounds.append(AggregationRound(
            round_num=r,
            global_accuracy=round(0.90 + i * 0.004 + random.uniform(-0.002, 0.002), 4),
            avg_loss=round(0.25 - i * 0.012 + random.uniform(-0.005, 0.005), 4),
            participating_sites=random.randint(3, 5),
            timestamp=(now - timedelta(hours=(last_n - i) * 6)).isoformat(),
        ))
    return FederatedHistory(rounds=rounds).model_dump()


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("/status", response_model=FederatedOverview)
async def federated_status():
    """Get current federated learning status across all sites."""
    return _build_overview()


@router.get("/history", response_model=FederatedHistory)
async def aggregation_history(last_n: int = Query(10, ge=1, le=100)):
    """Get aggregation round history."""
    return _build_history(last_n)


@router.post("/trigger-round")
async def trigger_round():
    """Manually trigger a new aggregation round (admin only in prod)."""
    return {"message": "Aggregation round 43 initiated", "status": "pending"}
