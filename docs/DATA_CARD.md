# TissueShift — Data Card

## Overview

TissueShift draws on six public (or controlled-access) breast cancer datasets
spanning histopathology whole-slide images, bulk RNA-seq, proteomics,
copy-number variation, spatial transcriptomics, and clinical outcomes.

---

## 1. TCGA-BRCA (The Cancer Genome Atlas — Breast Invasive Carcinoma)

| Field | Value |
|---|---|
| **Subjects** | 1 098 |
| **Modalities** | H&E diagnostic slides, RNA-seq (RSEM TPM), Affymetrix SNP6 CNV, clinical (stage, grade, OS, DFS, demographics) |
| **Labels** | PAM50 intrinsic subtype (LumA, LumB, HER2, Basal, Normal-like); IHC subtype (HR+/HER2−, HR+/HER2+, HR−/HER2+, TNBC) |
| **Access** | Open via GDC Data Portal |
| **License** | NIH Genomic Data Sharing Policy |
| **Known Biases** | ~73 % White patients; over-representation of stage I–II; few metaplastic / mixed cases |
| **Preprocessing** | Slides → Macenko-normalised 256 px tiles at 20× magnification; RNA → TPM → log₂(TPM+1) → top 2 000 variable genes |

### Splits

Deterministic 70 / 15 / 15 train / val / test split, stratified by PAM50
subtype, with patient-level isolation (seed = 42).

---

## 2. CPTAC-BRCA (Clinical Proteomic Tumor Analysis Consortium)

| Field | Value |
|---|---|
| **Subjects** | 198 |
| **Modalities** | H&E slides, RNA-seq, TMT label-free proteomics (~12 000 proteins) |
| **Labels** | PAM50 subtype, IHC subtype (derived) |
| **Access** | Open via CPTAC Data Portal |
| **Known Biases** | Small cohort; predominantly early-stage; no CNV in standard release |
| **Preprocessing** | Slides → tile pipeline identical to TCGA; proteomics → log₂ → quantile normalised |

---

## 3. Human Protein Atlas (HPA)

| Field | Value |
|---|---|
| **Subjects** | ~1 000 breast-annotated tissue samples |
| **Modalities** | IHC tissue micro-array images, RNA expression (consensus NX), survival Kaplan-Meier |
| **Labels** | Expression level (Not detected / Low / Medium / High); 5-year survival |
| **Access** | Open (proteinatlas.org, CC BY-SA 3.0) |
| **Known Biases** | TMA patches are small (≤ 1 mm²) and may not capture tumour heterogeneity |

---

## 4. HTAN Breast (Human Tumor Atlas Network)

| Field | Value |
|---|---|
| **Subjects** | ~500 |
| **Modalities** | Spatial transcriptomics (MERFISH / Visium), multiplex imaging (CODEX / CyCIF), scRNA-seq, H&E |
| **Labels** | Cell-type annotations, spatial domains, clinical outcome |
| **Access** | **Controlled** — dbGaP accession required |
| **Known Biases** | Multi-site collection introduces batch effects; limited longitudinal pairs |

---

## 5. HTAN Metastatic

| Field | Value |
|---|---|
| **Subjects** | 60 patients, 67 biopsies, 9 anatomical sites |
| **Modalities** | H&E + RNA-seq + clinical |
| **Labels** | Metastatic site, prior therapy, overall survival |
| **Access** | **Controlled** — dbGaP |
| **Known Biases** | Small cohort; selection bias towards patients with accessible biopsies |

---

## 6. GEO Progression

### GSE59246 — DCIS-to-IDC Progression

| Field | Value |
|---|---|
| **Subjects** | Matched DCIS → IDC pairs from same patients |
| **Modalities** | Microarray gene expression |
| **Labels** | DCIS vs. IDC; histological grade |
| **Access** | Open (GEO) |

### GSE148426 — AURORA US Longitudinal

| Field | Value |
|---|---|
| **Subjects** | Longitudinal metastatic breast cancer |
| **Modalities** | RNA-seq at multiple time-points |
| **Labels** | Treatment response, time-to-event |
| **Access** | Open (GEO) |

---

## Data Governance

| Access Tier | Datasets | Requirements |
|---|---|---|
| **Open** | TCGA-BRCA, CPTAC-BRCA, HPA, GEO | None beyond terms of use |
| **Controlled** | HTAN Breast, HTAN Metastatic | dbGaP Data Access Request + institutional approval |

### De-identification

All datasets provide de-identified data under HIPAA Safe Harbor. No protected
health information (PHI) is stored or processed by TissueShift code. Users are
responsible for complying with their institutional IRB and data use agreements.

### Consent

Participation in TCGA, CPTAC, HTAN, and GEO studies involves informed consent
for genomic and tissue data sharing under the respective study protocols.

---

## Feature Harmonisation

When combining across datasets, TissueShift applies:

1. **Gene-symbol alias resolution** — maps NCBI aliases to canonical HGNC symbols.
2. **Gene intersection** — retains genes present in ≥ 2 datasets.
3. **Quantile normalisation** — aligns marginal distributions within each modality.
4. **ComBat batch correction** — removes dataset-level batch effects from the
   expression matrix while preserving biological signal.

---

## Recommended Citation per Dataset

| Dataset | Citation |
|---|---|
| TCGA-BRCA | Cancer Genome Atlas Network. *Nature* 490, 61–70 (2012) |
| CPTAC-BRCA | Krug et al. *Cell* 183, 1–17 (2020) |
| HPA | Uhlén et al. *Science* 347, 1260419 (2015) |
| HTAN | Rozenblatt-Rosen et al. *Cell* 181, 236–249 (2020) |
| GEO GSE59246 | Lee et al. *Nat Commun* 6, 10060 (2015) |
| GEO GSE148426 | Brady et al. *Cancer Discov* 12, 1398–1413 (2022) |
