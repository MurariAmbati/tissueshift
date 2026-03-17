# Contributing to TissueShift

Thank you for your interest in contributing to TissueShift! This document explains how to contribute effectively.

## Ways to Contribute

### 1. Submit to the Leaderboard
The fastest way to contribute is to beat a baseline on one of our six benchmark tracks.

```bash
# Generate predictions on the test split
python -m benchmarks.baselines.path_only_abmil --split test --out predictions.csv

# Create a submission
mkdir -p submissions/SubtypeCall
cp predictions.csv submissions/SubtypeCall/my_model_v1.csv

# Add submission metadata
cat > submissions/SubtypeCall/my_model_v1.json << EOF
{
  "model_name": "MyModel v1",
  "description": "UNI + attention MIL with custom pooling",
  "code_url": "https://github.com/you/your-repo",
  "contact": "your@email.com"
}
EOF

# Submit via PR
git checkout -b submission/my-model-subtype
git add submissions/
git commit -m "Submit: MyModel v1 to SubtypeCall"
git push origin submission/my-model-subtype
```

The CI pipeline evaluates your predictions automatically and posts results as a PR comment.

### 2. Add a Dataset Loader
New dataset loaders go in `datasets/`. Follow the existing pattern:
- Create `datasets/your_cohort.py` with a loader class
- Add a manifest in `datasets/manifests/`
- Add a data card in `datasets/datacards/`
- Add tests in `tests/test_datasets.py`

### 3. Add an Encoder Backbone
Alternative pathology backbones (CTransPath, CONCH, Phikon) go in `encoders/pathology/`.
Your encoder must implement the `FeatureExtractor` protocol defined in `encoders/pathology/base.py`.

### 4. Add a Prediction Head
New prediction heads go in `heads/`. Each head takes a tissue-state embedding and produces a prediction.

### 5. Add Evaluation Metrics
New metrics go in `benchmarks/metrics.py`. Follow the existing pattern and add tests.

### 6. Improve the Frontend
Frontend work is in `app/frontend/`. We use Next.js 14, Three.js, D3.js, and TailwindCSS.

## Development Setup

```bash
git clone https://github.com/tissueshift/tissueshift.git
cd tissueshift
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Code Style
- **Python**: Ruff for linting and formatting (config in `pyproject.toml`)
- **TypeScript**: ESLint + Prettier (config in `app/frontend/`)
- **Line length**: 100 characters
- **Type hints**: Required for all public functions
- **Tests**: Required for all new modules

## Pull Request Process
1. Fork the repository and create a feature branch
2. Write tests for your changes
3. Ensure `ruff check .` and `pytest tests/` pass
4. Submit a PR with a clear description of what and why
5. Address review feedback

## Code of Conduct
Be respectful, constructive, and collaborative. We are building an open scientific tool.
