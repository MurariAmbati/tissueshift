# CPTAC-BRCA Data Card

## Overview
- **Name**: CPTAC Breast Invasive Carcinoma (CPTAC-BRCA)
- **Source**: Proteomic Data Commons (PDC) / IDC / GDC
- **Subjects**: 198
- **Access**: Open

## Data Types Available
| Type | Access | Source |
|------|--------|--------|
| Clinical | Open | GDC |
| Gene expression | Open | GDC |
| Proteomics (global) | Open | PDC |
| Phosphoproteomics | Open | PDC |
| Whole-slide images | Open | IDC |

## Role in TissueShift
**External validation cohort — never trained on.**

Used for:
- Cross-cohort generalization testing (train TCGA → evaluate CPTAC)
- Morphology-to-protein validation
- Proteogenomic fusion validation

## Known Limitations
- Smaller cohort (198 vs 1,098 TCGA)
- Different institution and processing protocols than TCGA
- Domain shift expected between TCGA and CPTAC histopathology
