# TCGA-BRCA Data Card

## Overview
- **Name**: TCGA Breast Invasive Carcinoma (TCGA-BRCA)
- **Source**: Genomic Data Commons (GDC) / Imaging Data Commons (IDC)
- **Subjects**: 1,098
- **Access**: Open (high-level genomic, clinical, pathology)

## Data Types Available
| Type | Access | Source | Notes |
|------|--------|--------|-------|
| Clinical (demographics, staging, outcomes) | Open | GDC API | Includes vital status, days to death/follow-up |
| Gene expression (STAR-Counts) | Open | GDC | FPKM-UQ quantification |
| Copy number segments | Open | GDC | Masked copy number segments |
| Whole-slide images (H&E) | Open | IDC | DICOM format via idc-index |
| Nuclei segmentations | Open | IDC | Pre-computed cell detection |
| TIL maps | Open | IDC | Tumor-infiltrating lymphocyte density maps |
| PAM50 subtype labels | Open | TCGA publications | From supplementary tables |
| Low-level sequencing (BAM) | Controlled | GDC/dbGaP | Requires dbGaP authorization |
| Germline variants | Controlled | GDC/dbGaP | Requires dbGaP authorization |

## Role in TissueShift
Primary training cohort. Provides the histopathology–genomics backbone for:
- Pathology encoder pretraining (Stage 1)
- Molecular encoder training (Stage 2)
- Multimodal fusion training (Stage 3)
- Static subtype benchmark (SubtypeCall track)
- Survival prediction benchmark (Survival track)
- Morphology-to-molecule benchmark (Morph2Mol track)

## Splits
- Train: 70% (~769 subjects), stratified by PAM50 subtype
- Validation: 15% (~165 subjects)
- Test: 15% (~164 subjects) — **FROZEN, never used during development**

## Known Limitations
- Single timepoint per patient (no longitudinal follow-up)
- Over-representation of certain demographics and institutions
- PAM50 labels derived computationally, subject to batch effects
- IHC receptor status from pathology reports, with inter-observer variability
