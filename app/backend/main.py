"""FastAPI backend for TissueShift."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("TissueShift backend starting")
    # Load model checkpoint if available
    checkpoint_path = Path("checkpoints/best_model.pt")
    if checkpoint_path.exists():
        logger.info(f"Model checkpoint found: {checkpoint_path}")
    else:
        logger.info("No model checkpoint found — running in demo mode")
    yield
    logger.info("TissueShift backend shutting down")


app = FastAPI(
    title="TissueShift API",
    description="Open temporal histopathology-to-omics model API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://tissueshift.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
