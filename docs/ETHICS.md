# TissueShift — Ethics Statement

## Purpose

This document outlines the ethical considerations, potential risks, and
mitigation strategies associated with the TissueShift breast cancer
histopathology-to-omics model.

---

## 1. Intended Scope and Boundaries

TissueShift is a **research-only** tool. It is designed to:

- Advance scientific understanding of breast cancer subtype emergence and
  disease progression.
- Provide an open, reproducible benchmark for multimodal temporal pathology
  models.
- Enable researchers to explore morphology-molecule relationships through an
  interactive atlas.

**TissueShift is NOT intended for**:

- Clinical diagnosis, prognosis, or treatment selection.
- Regulatory submission as a Software-as-a-Medical-Device (SaMD).
- Deployment in electronic health record (EHR) pipelines without independent
  prospective validation and regulatory clearance.

---

## 2. Demographic Bias and Fairness

### Known Representation Gaps

| Demographic | TCGA-BRCA Proportion | Population Incidence |
|---|---|---|
| White | ~73 % | ~62 % (US) |
| Black | ~16 % | ~15 % (US) |
| Asian | ~6 % | ~7 % (US) |
| Hispanic | ~4 % | ~14 % (US) |
| Male | < 1 % | ~1 % |

The training data substantially under-represents Hispanic patients and male
breast cancer cases. Model performance **must** be reported with stratified
metrics per demographic subgroup. Any downstream application should investigate
potential disparities.

### Subtype Imbalance

Luminal A cases dominate TCGA-BRCA (~46 %), while rare subtypes
(metaplastic, mixed) are critically under-represented (< 2 %). The model's
transition predictions for rare subtypes carry higher uncertainty.

### Mitigation Strategies

- Stratified evaluation with bootstrap confidence intervals per subgroup.
- Class-weighted loss functions during training.
- Explicit reporting of per-subgroup calibration (ECE) and balanced accuracy.
- The interactive atlas surfaces subgroup breakdowns in the Benchmarks page.

---

## 3. Data Privacy and Governance

### De-identification

All datasets used by TissueShift provide de-identified tissue and genomic
data under HIPAA Safe Harbor. No patient identifiers are stored, transmitted,
or inferable from the model's outputs.

### Controlled-Access Data

HTAN datasets require dbGaP Data Access Requests. Users **must**:

1. Obtain their own dbGaP access approval.
2. Comply with the Data Use Certification (DUC) terms.
3. Store controlled data in secure, access-controlled environments.
4. NOT redistribute controlled data through the TissueShift repository.

### Re-identification Risk

Whole-slide images and genomic profiles are theoretically re-identifiable
(especially for patients with rare mutations or unusual morphology). Users
should:

- Never publish individual-level model outputs alongside clinical details.
- Apply differential privacy techniques if releasing per-sample embeddings.
- Follow institutional IRB guidelines for secondary data analysis.

---

## 4. Potential Harms

### Over-reliance on Predictions

- Subtype and progression predictions should not replace pathologist review
  or molecular testing.
- Survival head outputs are population-level statistical estimates, not
  individual prognostic guarantees.

### Automation Bias

If integrated into clinical decision-support workflows (not recommended
without validation), there is a risk that clinicians may defer to model
predictions without adequate scrutiny, especially for confident but incorrect
outputs.

### Dual Use

- The model could theoretically be adapted to other cancer types, which may
  transfer biases without appropriate recalibration.
- Latent tissue-state embeddings could be misused for unsanctioned research
  on identifiable populations if combined with external clinical registries.

---

## 5. Responsible Development Practices

### Transparency

- All model weights, training code, and configuration are open-source.
- Model Card (see `docs/MODEL_CARD.md`) documents intended use, performance,
  and limitations.
- Data Card (see `docs/DATA_CARD.md`) documents sources, access tiers, and
  known biases.

### Reproducibility

- Deterministic data splits with fixed seeds.
- Configurable training pipeline with YAML-serialisable configuration.
- Baseline comparisons against established methods (RF on RNA, PAM50 caller,
  logistic regression on clinical features).

### Accountability

- Training logs and evaluation metrics are saved for auditability.
- Users who publish findings with TissueShift should cite the model card and
  report performance on the standardised benchmark protocol (4-layer
  evaluation).

---

## 6. Environmental Impact

Large-scale histopathology model training is computationally expensive. We
recommend:

- Using the 6-stage curriculum to avoid unnecessary full-model training.
- Leveraging frozen pre-trained backbones (UNI, CTransPath) to reduce compute.
- Reporting GPU hours and carbon footprint in publications (e.g., via
  ML CO2 Impact calculator).

---

## 7. Community Guidelines

Contributors and users of TissueShift are expected to:

1. **Acknowledge limitations** — do not present research outputs as clinical
   evidence without appropriate caveats.
2. **Report biases** — if subgroup performance gaps are discovered, report them
   as issues in the repository.
3. **Respect data governance** — never redistribute controlled-access data.
4. **Collaborate responsibly** — contributions should be reviewed for ethical
   implications alongside code quality.

---

## 8. Contact

For ethical concerns, data governance questions, or bias reports, please open
an issue in the project repository tagged `[ethics]`.
