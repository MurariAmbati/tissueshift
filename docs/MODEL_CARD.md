# TissueShift — Model Card

## Model Details

| Field | Value |
|---|---|
| **Model Name** | TissueShift v0.1.0 |
| **Model Type** | Multi-modal temporal world model for breast cancer histopathology-to-omics translation |
| **Architecture** | VAE-based shared latent tissue manifold with three encoders (pathology, molecular, spatial), a subtype-lattice transition model, and six prediction heads |
| **Developed By** | TissueShift Open Science Consortium |
| **License** | Apache 2.0 |
| **Framework** | PyTorch ≥ 2.0 |

---

## Model Description

TissueShift learns a shared 128-dimensional **tissue-state manifold** from three
modalities:

1. **Histopathology** — H&E whole-slide images tokenised into 256×256 px tiles,
   encoded via a frozen UNI / CTransPath backbone with gated MIL attention
   pooling.
2. **Molecular** — RNA-seq (60 660 genes → top 2 000), pathway activity (50
   Hallmark sets), copy-number segments (500 bins), and IHC marker state
   (ER/PR/HER2/Ki67), fused through a 4-head Transformer encoder.
3. **Spatial** — Cell-graph data from spatial transcriptomics or segmented
   histology, processed by a configurable GNN (GATv2 / GraphSAGE / GIN) with
   graph-level attention readout.

Each modality is projected into the shared latent space via a VAE bottleneck
that decomposes into **8 interpretable tissue axes**:

| Axis | Biological Interpretation |
|---|---|
| proliferative_index | Cell division rate / Ki67 proxy |
| immune_infiltration | TIL density and composition |
| stromal_remodelling | ECM stiffness and fibroblast activation |
| differentiation_grade | Tubule / nuclear pleomorphism |
| hormonal_signalling | ER / PR pathway activation |
| her2_amplification | HER2 / ERBB2 amplification status |
| metabolic_reprogramming | Warburg effect / oxidative phosphorylation |
| invasive_potential | EMT / basement-membrane breach |

### Subtype Lattice Transition Model

A discrete transition model over 7 subtype nodes (Normal-like → Luminal A →
Luminal B → HER2-enriched → Basal-like → Metaplastic → Mixed/Ambiguous) with
biologically constrained adjacency:

- Reversible low-risk links (Normal ↔ LumA)
- One-directional high-risk links (LumB → HER2, Basal → Metaplastic)
- Missing edges encode transitions deemed biologically implausible

---

## Intended Use

### Primary Use Cases

- **Subtype emergence tracking**: Given sequential biopsies from the same
  patient, predict how the PAM50/IHC subtype will evolve.
- **Progression staging**: Classify tissue samples into pre-invasive, invasive,
  locally advanced, metastatic-adapted, or ambiguous intermediate stages.
- **Morphology-molecule bridging**: Predict molecular profiles (gene expression,
  pathway activation) from histology images alone.
- **Micro-environment scoring**: Quantify stromal remodelling, immune exclusion,
  ECM density, angiogenic switch, invasive potential, and metabolic shift.
- **Survival prediction**: Discrete-time hazard modelling from multimodal tissue
  state vectors.

### Out-of-Scope Uses

- **Clinical diagnosis or treatment decisions** — this model is a research tool
  and has NOT been validated for clinical deployment under FDA/CE/IVDR
  regulatory standards.
- **Non-breast cancers** — the training data, subtype lattice, and transition
  priors are breast cancer–specific.
- **Real-time intraoperative use** — inference latency has not been benchmarked
  for surgical workflow integration.
- **Single-marker IHC scoring** — the model is designed for whole-slide,
  multi-modal analysis.

---

## Training Data

| Dataset | Subjects | Modalities | Access |
|---|---|---|---|
| TCGA-BRCA | 1 098 | H&E + RNA-seq + CNV + clinical + PAM50 | Open (GDC) |
| CPTAC-BRCA | 198 | H&E + RNA-seq + proteomics | Open (CPTAC Portal) |
| Human Protein Atlas | ~1 000 (breast) | IHC images + expression + survival | Open (proteinatlas.org) |
| HTAN Breast | ~500 | Spatial tx + imaging + scRNA-seq | dbGaP Controlled |
| HTAN Metastatic | 60 patients, 67 biopsies | H&E + RNA-seq + clinical | dbGaP Controlled |
| GEO Progression | GSE59246 + GSE148426 | DCIS→IDC pairs, longitudinal RNA | Open (GEO) |

**Splits** — 70 % train / 15 % validation / 15 % test, stratified by subtype
with patient-level isolation (no patient appears in more than one split).

---

## Evaluation Results

### Layer 1 — Static Subtype Classification

| Metric | Target |
|---|---|
| Balanced accuracy (PAM50, 5-class) | ≥ 0.82 |
| Balanced accuracy (IHC, 4-class) | ≥ 0.85 |
| Macro-F1 (lattice, 7-class) | ≥ 0.78 |
| Expected Calibration Error | ≤ 0.05 |

### Layer 2 — Progression Staging

| Metric | Target |
|---|---|
| Ordinal accuracy (5-stage) | ≥ 0.70 |
| Adjacent-within-1 accuracy | ≥ 0.88 |
| Mean absolute error (ordinal) | ≤ 0.35 |

### Layer 3 — Drift Prediction

| Metric | Target |
|---|---|
| Accuracy (3-class drift) | ≥ 0.70 |
| Concordance-index (survival) | ≥ 0.65 |
| Brier score (survival) | ≤ 0.22 |

### Layer 4 — Spatial / Bridging

| Metric | Target |
|---|---|
| Gene-expression R² (top 2 000) | ≥ 0.40 |
| Pathway Spearman ρ | ≥ 0.55 |
| Microenvironment AUROC (6 scores) | ≥ 0.75 |

---

## Ethical Considerations

### Bias & Fairness

- **Demographic imbalance** — TCGA-BRCA over-represents White patients
  (~73 %), with lower representation of Black, Hispanic, and Asian
  populations. Model performance should be reported **per demographic
  subgroup** and disparities flagged.
- **Grade / stage skew** — early-stage (I/II) samples dominate; metastatic
  and rare subtypes (metaplastic, mixed) are under-represented.
- **Sex bias** — male breast cancer (<1 % of cases) is essentially absent
  from training data.

### Privacy

- All training data are de-identified under HIPAA Safe Harbor.
- Controlled-access datasets (HTAN, dbGaP) require approved Data Access
  Requests. Users must comply with their own IRB and institutional
  agreements.

### Misuse Risks

- Using subtype or progression predictions to deny or alter patient care
  without clinical validation.
- Over-reliance on survival head outputs as prognostic biomarkers without
  prospective validation.
- Re-identification of patients from tissue images or genomic data.

### Limitations

- Frozen pathology backbones may not capture domain-specific features from
  specialised staining protocols.
- Transition model priors assume a tree-like subtype lattice; real
  progression may involve parallel or cyclical pathways.
- Temporal pseudo-ordering (from cross-sectional data) is an approximation;
  true longitudinal validation requires prospective cohorts.

---

## How to Cite

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
