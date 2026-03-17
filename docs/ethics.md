# TissueShift — Ethics & Responsible Use

## Intended Use

TissueShift is a **research tool** for studying breast cancer subtype dynamics and progression. It is designed for:
- Computational pathology research
- Tumor evolution and subtype transition studies
- Benchmarking multimodal tissue-state models
- Educational demonstrations of breast cancer biology

## NOT Intended For

- **Clinical diagnosis or treatment decisions**: TissueShift is not a validated diagnostic device. It has not undergone regulatory review (FDA, CE-IVDR, or equivalent). Clinical decisions must not be based on its predictions.
- **Individual patient prognosis without clinical oversight**: Survival and drift predictions are population-level statistical estimates, not individual guarantees.
- **Automated clinical workflows**: The system should not be embedded in clinical pipelines without extensive validation and regulatory approval.

## Known Limitations

1. **Training data bias**: TCGA-BRCA over-represents certain demographics and institutions. Performance may degrade on underrepresented populations.
2. **Static snapshots, not true longitudinal**: Most training data consists of single-timepoint biopsies. Temporal modeling relies on pseudo-temporal ordering and cross-patient inference, not true within-patient longitudinal follow-up.
3. **Subtype labels are imperfect**: PAM50 and IHC classifications have known inter-observer variability and technical batch effects. The model inherits these label noise characteristics.
4. **Missing modalities**: When molecular data is unavailable (pathology-only inference), predictions rely entirely on morphological features, which carry less information than multimodal inputs.
5. **Subtype drift predictions are probabilistic**: The drift engine predicts tendencies, not certainties. Actual subtype evolution depends on treatment, biology, and factors not captured in the model.

## Fairness Considerations

- Performance should be evaluated across demographic subgroups (age, race, ethnicity) when such metadata is available
- We track per-subtype and per-stage performance to identify systematic gaps
- We encourage contributors to report subgroup results in leaderboard submissions

## Data Privacy

- TissueShift uses only de-identified public research data
- No personally identifiable information (PII) is processed
- All data access follows institutional data governance frameworks
- See [data_governance.md](data_governance.md) for source-specific access details

## Reporting Issues

If you identify a bias, safety concern, or ethical issue with TissueShift, please open a GitHub issue with the `ethics` label or contact the maintainers directly.
