# TissueShift Data Governance

## Data Access Matrix

| Source | Access Level | License | Auth Required | Notes |
|--------|-------------|---------|---------------|-------|
| TCGA-BRCA (IDC/GDC) | **Open** | Open Access | None for high-level data | Clinical, genomic (FPKM-UQ), histopathology |
| CPTAC-BRCA (IDC/PDC) | **Open** | Open Access | None | Proteogenomic cohort, pathology + protein |
| Human Protein Atlas | **Open** | CC BY-SA 3.0 | None | IHC images, expression, survival |
| HTAN (Synapse/IDC) | **Open** (L3/L4) | CC BY 4.0 | Synapse account | Open processed + open imaging; controlled sequencing |
| GEO Progression | **Open** | Public | None | GSE214093/GSE214094 DCIS→invasive |
| GDC Controlled | **Controlled** | dbGaP | dbGaP authorization | Low-level sequencing, germline, some clinical |
| AURORA | **Request-based** | Custom | Research proposal | *Currently not accepting new proposals* |

## Principles

1. **Public-data-first**: The default data path uses only open-access resources. No controlled or request-based data is required for the core pipeline.

2. **Honest disclosure**: We clearly label which data sources require authentication, authorization, or special access. We do not pretend all data is freely downloadable.

3. **No bundled patient data**: This repository never contains patient-level data. All data is accessed through official APIs and documented download procedures.

4. **Reproducible manifests**: Every cohort has a manifest file (`datasets/manifests/`) listing exactly which samples are used, enabling independent verification.

5. **License compliance**: We track and respect the license of every data source. Derivative data products inherit the most restrictive upstream license.

## GDC Open vs. Controlled Data

GDC categorizes data into open and controlled tiers:
- **Open access**: High-level genomic data (gene expression quantification, copy number segments), most clinical data, biospecimen data
- **Controlled access**: Low-level sequencing (BAM/FASTQ), germline variants, certain clinical fields

TissueShift uses only open-access GDC data for its default pipeline. Controlled data can optionally enhance molecular features for users with dbGaP authorization.

## HTAN Data Access

HTAN splits data into:
- **Open processed** (Level 3/4): Cell-type annotations, spatial features, processed expression — available through Synapse under CC BY 4.0
- **Open imaging**: Whole-slide images available through IDC
- **Controlled sequencing**: Raw sequencing data requires dbGaP authorization

TissueShift uses open processed and open imaging data. Controlled sequencing is not required.

## AURORA Status

The AURORA US Metastatic Breast Cancer study is scientifically ideal for TissueShift (617 samples, 371 patients, paired primary–metastatic subtypes). However, the AURORA data-sharing page currently states that research proposals are no longer being accepted, pending a decision by a new sponsor.

TissueShift is architectured to integrate AURORA data when access becomes available, but the core pipeline works without it.
