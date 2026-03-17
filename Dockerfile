# Dockerfile for TissueShift
# Multi-stage build: ML backend + Next.js frontend

# ============================================================
# Stage 1: Python ML Backend
# ============================================================
FROM python:3.10-slim AS backend

WORKDIR /app

# System dependencies for openslide, HDF5, and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenslide0 \
    libopenslide-dev \
    libhdf5-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .

# Copy source code
COPY datasets/ datasets/
COPY preprocess/ preprocess/
COPY encoders/ encoders/
COPY world_model/ world_model/
COPY heads/ heads/
COPY benchmarks/ benchmarks/
COPY training/ training/
COPY app/backend/ app/backend/

EXPOSE 8000

CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================================
# Stage 2: Next.js Frontend
# ============================================================
FROM node:20-slim AS frontend

WORKDIR /app/frontend

COPY app/frontend/package*.json ./
RUN npm ci --production=false 2>/dev/null || echo "No package.json yet"

COPY app/frontend/ .
RUN npm run build 2>/dev/null || echo "Frontend not yet configured"

EXPOSE 3000

CMD ["npm", "start"]
