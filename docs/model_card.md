# TissueShift Model Card

Following the framework of Mitchell et al. (2019), "Model Cards for Model Reporting."

## Model Details

- **Name**: TissueShift-BRCA v0.1
- **Type**: Multimodal temporal tissue-state model
- **Architecture**: UNI ViT-L pathology encoder → region tokenizer → ABMIL aggregator → cross-attention fusion (8 tissue-state queries) → shared manifold → 6 prediction heads
- **Input**: H&E whole-slide images, gene expression (optional), proteomic data (optional), spatial context (optional)
- **Output**: Subtype probabilities, drift scores, progression stage, survival risk, gene expression predictions, microenvironment remodeling score
- **Training data**: TCGA-BRCA (1,098 subjects, open access)
- **Validation data**: CPTAC-BRCA (198 subjects, held out)
- **License**: Apache 2.0
- **Version**: 0.1.0 (initial release)

## Intended Use

Research tool for breast cancer subtype dynamics. See [ethics.md](ethics.md) for full intended use statement.

## Metrics

| Task | Metric | Target | Baseline |
|------|--------|--------|----------|
| PAM50 Subtype | Balanced Accuracy | ≥82% | ~78-90% (published) |
| Survival | C-index | ≥0.60 | ~0.55-0.65 (published) |
| Morph2Mol | Mean Pearson | ≥0.30 | ~0.20-0.40 (published) |
| Progression | Ordinal Accuracy | ≥70% | TBD |
| Drift | AUROC | TBD | TBD |
| Microenvironment | Remodeling score correlation | TBD | TBD |

## Limitations

See [ethics.md](ethics.md).

## Training Details

- **Stage 1**: Pathology encoder + subtype head (frozen UNI features, ~2-4 hrs on single GPU)
- **Stage 2**: Molecular encoder (auxiliary subtype prediction, <1 hr)
- **Stage 3**: Multimodal fusion + manifold + all heads (4-8 hrs)
- **Stage 4**: Transition model (pseudo-temporal ordering, 1-2 hrs)
- **Stage 5**: Calibration and robustness audit (<1 hr)
- **Optimizer**: AdamW, lr=1e-4, cosine schedule, weight decay=0.01
- **Precision**: Mixed precision (AMP)
