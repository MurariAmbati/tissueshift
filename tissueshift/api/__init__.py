"""TissueShift REST API — FastAPI backend for the clinical dashboard.

Provides endpoints for:
- Patient management (CRUD)
- Slide upload & AI analysis
- Model inference (subtypes, biomarkers, survival)
- Digital twin simulation
- Treatment comparison
- Report generation
- Cohort analytics
- Knowledge graph queries
- Federated learning status

Launch:
    uvicorn tissueshift.api.server:app --host 0.0.0.0 --port 8000
"""
