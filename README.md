# TissueShift

**Open Temporal Histopathology-to-Omics Model for Breast Cancer Subtype Emergence and Progression**

---

## Overview

TissueShift is a multimodal deep-learning framework that learns a shared
**tissue-state manifold** from histopathology images, molecular profiles, and
spatial transcriptomics. It models breast cancer subtype emergence, disease
progression, and morphology-molecule bridging through a biologically
constrained **subtype lattice transition model**.

### Key Capabilities

| Capability | Description |
|---|---|
| **Subtype classification** | PAM50 (5-class), IHC (4-class), and lattice (7-class) with calibrated confidence |
| **Progression staging** | Pre-invasive → invasive → locally advanced → metastatic-adapted, ordinal score |
| **Drift prediction** | Stable / within-lineage / cross-subtype transitions between time-points |
| **Morphology-molecule bridge** | Predict gene expression, pathway activity, and protein levels from histology |
| **Micro-environment scoring** | Six-component remodelling score (stromal, immune, ECM, angiogenic, invasive, metabolic) |
| **Survival prediction** | Discrete-time hazard model producing full survival curves |
| **Interactive atlas** | Streamlit app with manifold visualisation, subtype river diagrams, and molecular bridge explorer |

---

## Architecture

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Pathology   │   │  Molecular   │   │   Spatial    │
│   Encoder    │   │   Encoder    │   │   Encoder    │
│ (UNI / MIL)  │   │ (Transformer)│   │ (GATv2/GNN) │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                   │
       └────────┬─────────┴───────────────────┘
                │
        ┌───────▼────────┐
        │  Cross-Modal   │
        │   Attention    │
        └───────┬────────┘
                │
        ┌───────▼────────┐
        │  VAE Bottleneck │ ──► 128-dim latent z
        │  (μ, log σ²)   │ ──► 8 interpretable axes
        └───────┬────────┘
                │
     ┌──────────┼──────────────────────┐
     │          │                      │
┌────▼────┐ ┌──▼──────────┐  ┌────────▼────────┐
│ Subtype │ │ Transition  │  │ Prediction Heads │
│  Head   │ │   Model     │  │ (6 task heads)   │
└─────────┘ │ (Lattice)   │  └─────────────────┘
            └─────────────┘
```

### Subtype Lattice (7 nodes)

```
Normal-like ←→ Luminal A ←→ Luminal B → HER2-enriched
                                        ↕
                            Basal-like → Metaplastic
                                ↕
                          Mixed / Ambiguous
```

### 8 Tissue Axes

1. Proliferative index
2. Immune infiltration
3. Stromal remodelling
4. Differentiation grade
5. Hormonal signalling
6. HER2 amplification
7. Metabolic reprogramming
8. Invasive potential

---

## Installation

### Prerequisites

- Python ≥ 3.10
- CUDA ≥ 11.8 (recommended for GPU training)
- OpenSlide system library (required for WSI processing)

### From Source

```bash
git clone https://github.com/tissueshift/tissueshift.git
cd tissueshift

# Core installation
pip install -e .

# Full installation (all optional dependencies)
pip install -e ".[all]"

# Or install specific extras
pip install -e ".[pathology,graph,viz]"
```

### From Requirements

```bash
pip install -r requirements.txt
```

### OpenSlide System Library

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install openslide-tools
```

**macOS:**
```bash
brew install openslide
```

**Windows:**
Download from https://openslide.org/download/ and add to PATH.

---

## Data Setup

### Open-Access Datasets

| Dataset | Download |
|---|---|
| TCGA-BRCA | [GDC Data Portal](https://portal.gdc.cancer.gov/) |
| CPTAC-BRCA | [CPTAC Data Portal](https://proteomics.cancer.gov/) |
| HPA | [proteinatlas.org](https://www.proteinatlas.org/) |
| GEO GSE59246 | [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE59246) |
| GEO GSE148426 | [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE148426) |

### Controlled-Access Datasets

| Dataset | Access |
|---|---|
| HTAN Breast | [dbGaP](https://www.ncbi.nlm.nih.gov/gap/) — requires Data Access Request |
| HTAN Metastatic | [dbGaP](https://www.ncbi.nlm.nih.gov/gap/) — requires Data Access Request |

### Directory Structure

Organise downloaded data under a root directory and configure paths in a YAML
config file:

```
data/
├── tcga_brca/
│   ├── slides/          # .svs whole-slide images
│   ├── rna_dir/         # per-sample .tsv RNA-seq files
│   ├── cnv_dir/         # per-sample CNV segment files
│   └── clinical.tsv
├── cptac_brca/
│   ├── slides/
│   ├── rna_dir/
│   └── proteomics.tsv
├── hpa/
│   └── images/
├── htan/
│   └── spatial/
└── geo/
    ├── GSE59246/
    └── GSE148426/
```

---

## Configuration

TissueShift uses a single dataclass-backed configuration system that can be
saved/loaded as YAML:

```python
from tissueshift.config import TissueShiftConfig

# Create default config
cfg = TissueShiftConfig()

# Customise
cfg.data.tcga_slide_dir = "/path/to/tcga/slides"
cfg.training.stages[0].learning_rate = 5e-5

# Save
cfg.save_yaml("configs/my_experiment.yaml")

# Load
cfg = TissueShiftConfig.from_yaml("configs/my_experiment.yaml")
```

---

## Training

TissueShift uses a **6-stage curriculum**:

| Stage | Name | What Trains | Epochs | LR |
|---|---|---|---|---|
| 1 | Pathology pre-training | Pathology encoder + region head | 30 | 1e-4 |
| 2 | Molecular pre-training | Molecular encoder + reconstruction | 30 | 5e-4 |
| 3 | Spatial pre-training | Spatial encoder + graph tasks | 20 | 3e-4 |
| 4 | Manifold alignment | All encoders + VAE + cross-modal | 50 | 1e-4 |
| 5 | Transition training | Transition model + drift head | 40 | 5e-5 |
| 6 | End-to-end fine-tuning | Full model, all heads | 30 | 1e-5 |

### Quick Start

```python
from tissueshift.config import TissueShiftConfig
from tissueshift.world_model.tissueshift_model import TissueShiftModel
from tissueshift.training.trainer import TissueShiftTrainer

cfg = TissueShiftConfig()
model = TissueShiftModel(cfg)
trainer = TissueShiftTrainer(model, cfg)

# Train all 6 stages
trainer.train_all_stages(
    train_loader=train_loader,
    val_loader=val_loader,
)
```

### Resuming Training

```python
# Checkpoints are saved automatically after each stage
# Resume from a specific stage
trainer.train_stage(
    stage_idx=4,
    train_loader=train_loader,
    val_loader=val_loader,
)
```

---

## Evaluation

The benchmark suite implements a **4-layer evaluation protocol**:

```python
from tissueshift.benchmarks.evaluator import TissueShiftEvaluator

evaluator = TissueShiftEvaluator(model, cfg)

# Layer 1: Static subtype classification
subtype_results = evaluator.evaluate_subtype(test_loader)

# Layer 2: Progression staging
progression_results = evaluator.evaluate_progression(test_loader)

# Layer 3: Drift prediction + survival
drift_results = evaluator.evaluate_drift(test_loader)

# Layer 4: Spatial / bridging
spatial_results = evaluator.evaluate_spatial(test_loader)

# Full evaluation
all_results = evaluator.evaluate_all(test_loader)
```

### Baselines

```python
from tissueshift.benchmarks.baselines import SubtypeBaselines

baselines = SubtypeBaselines()
baselines.fit(X_train, y_train)
results = baselines.evaluate(X_test, y_test)
```

---

## Interactive Atlas

Launch the Streamlit-based exploration app:

```bash
streamlit run tissueshift/app/atlas.py
```

### Pages

1. **Overview** — Project description and architecture
2. **Patient Explorer** — Search and view individual patient data
3. **Subtype River** — Stacked area chart of subtype composition over time
4. **Tissue Manifold** — UMAP/PHATE/PCA embedding visualisation with trajectories
5. **Molecular Bridge** — Predict molecular profiles from histology embeddings
6. **Benchmarks** — Performance metrics across all 4 evaluation layers
7. **Data Sources** — Documentation of all training datasets

---

## Project Structure

```
TISSUESHIFT/
├── tissueshift/
│   ├── __init__.py              # Package root
│   ├── config.py                # Master configuration (dataclasses + YAML)
│   ├── datasets/
│   │   ├── tcga_brca.py         # TCGA-BRCA loader (1098 subjects)
│   │   ├── cptac_brca.py        # CPTAC-BRCA loader (198 subjects)
│   │   ├── hpa.py               # Human Protein Atlas loader
│   │   ├── htan.py              # HTAN spatial + metastatic loaders
│   │   ├── geo_progression.py   # GEO DCIS→IDC + AURORA loaders
│   │   ├── multimodal.py        # Unified multi-source wrapper
│   │   └── progression_pairs.py # (early, late) pair dataset
│   ├── preprocess/
│   │   ├── stain_normalization.py  # Macenko / Vahadane / Reinhard
│   │   ├── tile_extraction.py      # WSI → 256px tiles at 20×
│   │   ├── graph_builder.py        # Cell coordinates → PyG graphs
│   │   └── feature_harmonization.py # Gene mapping, ComBat, quantile norm
│   ├── encoders/
│   │   ├── pathology_encoder.py    # UNI/CTransPath backbone + MIL
│   │   ├── molecular_encoder.py    # 4-stream Transformer fusion
│   │   └── spatial_encoder.py      # GATv2/GraphSAGE/GIN + readout
│   ├── world_model/
│   │   ├── tissue_state_model.py   # Cross-modal attention + VAE + axes
│   │   ├── transition_model.py     # Subtype lattice + time encoding
│   │   └── tissueshift_model.py    # Full model assembly
│   ├── heads/
│   │   ├── subtype_head.py         # PAM50 / IHC / lattice classification
│   │   ├── drift_head.py           # 3-class drift + target subtype
│   │   ├── progression_head.py     # 5-stage ordinal progression
│   │   ├── morphology_bridge.py    # Hist → mol prediction
│   │   ├── microenvironment_head.py # 6-component remodelling score
│   │   └── survival_head.py        # Discrete-time hazard model
│   ├── training/
│   │   ├── losses.py               # Composite multi-task loss
│   │   └── trainer.py              # 6-stage curriculum trainer
│   ├── benchmarks/
│   │   ├── evaluator.py            # 4-layer evaluation protocol
│   │   └── baselines.py            # RF, PAM50 caller, logistic regression
│   └── app/
│       └── atlas.py                # Streamlit interactive atlas
├── docs/
│   ├── MODEL_CARD.md
│   ├── DATA_CARD.md
│   ├── ETHICS.md
│   └── CITATIONS.md
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Responsible Use

TissueShift is a **research-only** tool. It has not been validated for clinical
deployment. See [docs/ETHICS.md](docs/ETHICS.md) for full ethical guidelines,
known biases, and responsible development practices.

Key points:

- **Not for clinical use** — do not use predictions for diagnosis or treatment.
- **Demographic bias** — TCGA training data over-represents White patients.
- **Rare subtypes** — metaplastic and mixed subtypes are under-represented.
- **Data governance** — controlled-access data requires dbGaP approval.

---

## Citation

```bibtex
@software{tissueshift2024,
  title   = {TissueShift: Open Temporal Histopathology-to-Omics Model for
             Breast Cancer Subtype Emergence and Progression},
  author  = {TissueShift Open Science Consortium},
  year    = {2024},
  url     = {https://github.com/tissueshift/tissueshift},
  license = {Apache-2.0}
}
```

See [docs/CITATIONS.md](docs/CITATIONS.md) for full references to all datasets
and methods used.

---

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
