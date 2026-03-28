"""FastAPI application — main entry point for TissueShift backend."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tissueshift.api.routes import (
    analysis,
    cohort,
    digital_twin,
    federated,
    knowledge_graph,
    patients,
    predictions,
    reports,
)

logger = logging.getLogger(__name__)


# ── Lifespan ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    logger.info("TissueShift API starting …")
    # On startup: load model weights, warm caches, etc.
    app.state.model = None  # lazy-loaded on first request
    app.state.kg = None
    yield
    logger.info("TissueShift API shutting down …")


# ── App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="TissueShift Clinical AI API",
    description=(
        "REST API for the TissueShift breast-cancer histopathology-to-omics "
        "prediction platform. Provides patient management, AI inference, "
        "digital twin simulation, treatment analysis, and report generation."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend (dev & production)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,https://*.vercel.app",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ──────────────────────────────────────────────────────────

app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Slide Analysis"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(digital_twin.router, prefix="/api/digital-twin", tags=["Digital Twin"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(cohort.router, prefix="/api/cohort", tags=["Cohort Analytics"])
app.include_router(knowledge_graph.router, prefix="/api/knowledge-graph", tags=["Knowledge Graph"])
app.include_router(federated.router, prefix="/api/federated", tags=["Federated Learning"])


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "model_loaded": app.state.model is not None,
    }
