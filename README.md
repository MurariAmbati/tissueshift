<div align="center">

# 🧬 TissueShift

### Open Temporal Histopathology-to-Omics Model for Subtype Emergence and Progression in Breast Cancer

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-red.svg)](https://pytorch.org)

**TissueShift predicts how a breast tumor's subtype is changing over time by reading tissue morphology together with molecular evidence.**

[Architecture](#architecture) · [Quickstart](#quickstart) · [Data](#data-strategy) · [Leaderboard](#leaderboard) · [Contributing](#contributing)

</div>

---

## What Is TissueShift?

TissueShift is a **multimodal temporal tissue-state model** that fuses histopathology, spatial microenvironment structure, transcriptomic and proteomic signals, and longitudinal clinical context into a **shared latent tissue manifold**. It then predicts:

1. **Current Tissue State** — subtype identity from morphology + molecular evidence
2. **Subtype Drift** — probability that the tumor will remain stable, drift within lineage, or switch toward a more aggressive state
3. **Progression Stage** — where the biopsy sits on a pre-invasive → invasive → metastatic continuum
4. **Morphology-to-Molecule Bridge** — which pathways and markers the tissue appears to be expressing, and *where*

Most breast-cancer AI stops at static subtyping. TissueShift models subtype as a **trajectory**, not a fixed label.

## Why This Matters

Breast cancer progression is dynamic: receptor discordance between primary and metastatic disease is well recognized, and paired primary–metastatic studies have shown intrinsic subtype conversion. TissueShift matters because it models that change directly rather than pretending a tumor has one permanent identity.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT MODALITIES                         │
│  H&E WSI  │  IHC/Markers  │  RNA/Protein  │  Spatial Context   │
└─────┬─────┴──────┬────────┴──────┬────────┴────────┬───────────┘
      │            │               │                 │
      ▼            ▼               ▼                 ▼
┌──────────┐ ┌──────────┐  ┌──────────────┐  ┌──────────────┐
│ UNI ViT  │ │  Marker  │  │  Expression  │  │    Graph     │
│ Encoder  │ │  Encoder │  │   Encoder    │  │   Encoder    │
│ (frozen) │ │          │  │  + Pathway   │  │  (PyG GIN)   │
└────┬─────┘ └────┬─────┘  └──────┬───────┘  └──────┬───────┘
     │            │               │                  │
     ▼            │               ▼                  │
┌──────────┐      │        ┌──────────────┐          │
│  Region  │      │        │  Proteomic   │          │
│Tokenizer │      │        │   Encoder    │          │
└────┬─────┘      │        └──────┬───────┘          │
     │            │               │                  │
     ▼            ▼               ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              CROSS-ATTENTION FUSION (8 tissue-state queries)    │
│  Lineage │ Prolif │ HER2 │ Basal │ Immune │ Stroma │ CIN │ Unc│
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  TISSUE-STATE       │
                    │  MANIFOLD (z∈R⁵¹²)  │
                    │  + VICReg + Contrast │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
     ┌────────────────┐ ┌───────────┐ ┌────────────────┐
     │ TRANSITION     │ │ PREDICTION│ │ VISUALIZATION  │
     │ MODEL          │ │ HEADS     │ │ DECODER        │
     │ (Subtype       │ │ • Subtype │ │ z → R²/R³      │
     │  Lattice)      │ │ • Drift   │ │ (Subtype River)│
     │                │ │ • Stage   │ │                │
     │                │ │ • Survival│ │                │
     │                │ │ • Morph2Mo│ │                │
     │                │ │ • MicroEnv│ │                │
     └────────────────┘ └───────────┘ └────────────────┘
```

## Quickstart

### With Docker (recommended)
```bash
git clone https://github.com/tissueshift/tissueshift.git
cd tissueshift
cp .env.example .env
# Edit .env with your HuggingFace token
docker compose up
# Frontend: http://localhost:3000
# API: http://localhost:8000/docs
```

### Local Development
```bash
git clone https://github.com/tissueshift/tissueshift.git
cd tissueshift
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Download data
python -m datasets.tcga_brca download --data-dir ./data

# Extract features (requires GPU)
python -m preprocess.feature_extract --slides-dir ./data/slides --out-dir ./data/features

# Train Stage 1 (pathology encoder + subtype head)
python -m training.train --config configs/stage1_pretrain.yaml

# Run benchmarks
python -m benchmarks.evaluate --track SubtypeCall --predictions results/predictions.json
```

## Data Strategy

TissueShift is **public-data-first**:

| Source | Subjects | Role | Access |
|--------|----------|------|--------|
| **TCGA-BRCA** (IDC) | 1,098 | Primary training: histopathology + genomics | Open |
| **CPTAC-BRCA** (IDC) | 198 | External validation: proteogenomics | Open |
| **Human Protein Atlas** | — | Protein-expression grounding + IHC images | Open |
| **HTAN Breast** | 60+ | Spatial atlases + metastatic evolution | Open (L3/L4) |
| **GEO Progression** | varies | DCIS-to-invasive progression | Open |
| **AURORA** | 371 | Paired primary-metastatic (future) | Request-based* |

*AURORA is not currently accepting new data-sharing proposals. TissueShift is designed to work without it.*

See [docs/data_governance.md](docs/data_governance.md) for complete access details.

## Leaderboard

TissueShift maintains a **six-track public benchmark** for breast cancer computational pathology:

| Track | Task | Primary Metric |
|-------|------|----------------|
| `SubtypeCall` | PAM50 subtype from H&E | Macro-F1 |
| `SubtypeDrift` | Predict subtype change primary→met | AUROC |
| `ProgressionStage` | Classify pre-invasive→metastatic stage | QWK (Quadratic Weighted Kappa) |
| `Morph2Mol` | Predict gene expression from morphology | R² |
| `Survival` | Predict overall survival risk | C-index |
| `SpatialPhenotype` | Predict spatial cell neighborhoods | R²-TIL |

### Submit to the leaderboard
```bash
# 1. Generate predictions
python -m benchmarks.baselines.path_only_abmil --split test --out predictions.json

# 2. Submit via PR
cp predictions.json submissions/SubtypeCall/my_model_v1.json
# Add submission.json with model metadata
git checkout -b submission/my-model
git add submissions/
git commit -m "Submit: MyModel to SubtypeCall track"
git push && gh pr create
```

The CI pipeline will automatically evaluate your submission and post results.

## Project Structure

```
tissueshift/
├── datasets/           # Data loaders, manifests, data cards
├── preprocess/         # Tiling, stain normalization, feature extraction
├── encoders/           # Pathology, molecular, spatial tokenizers
│   ├── pathology/      #   UNI encoder, region tokenizer, slide aggregator
│   ├── molecular/      #   Expression, pathway, proteomic encoders
│   └── spatial/        #   Graph encoder (PyG)
├── world_model/        # Fusion, manifold, transition model
├── heads/              # Subtype, drift, progression, survival, morph2mol
├── benchmarks/         # Evaluation scripts, baselines, leaderboard
├── training/           # Training loop, configs, losses
├── app/                # FastAPI inference + leaderboard API
│   └── backend/        #   API server, routes, models
├── frontend/           # Next.js + Three.js interactive atlas
├── docs/               # Model card, ethics, data governance
├── notebooks/          # Exploration and visualization
└── tests/              # Unit and integration tests
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Ways to contribute:**
- 🏆 Submit to the [leaderboard](#leaderboard)
- 🔬 Add a new dataset loader
- 🧠 Implement a new encoder backbone
- 📊 Add evaluation metrics
- 🎨 Improve the interactive atlas
- 📝 Improve documentation

## Ethics & Limitations

TissueShift is a **research tool**, not a clinical diagnostic device. See [docs/ethics.md](docs/ethics.md) for responsible use guidelines, known limitations, and bias considerations.

## Citation

```bibtex
@software{tissueshift2026,
  title={TissueShift: Open Temporal Histopathology-to-Omics Model for Breast Cancer},
  author={TissueShift Contributors},
  year={2026},
  url={https://github.com/tissueshift/tissueshift}
}
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
