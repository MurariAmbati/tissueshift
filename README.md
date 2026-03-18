# tissue shift

multimodal temporal model for breast cancer subtype emergence and progression. fuses histopathology, transcriptomics, proteomics, and spatial context into a shared tissue-state manifold.

predicts subtype identity, subtype drift, progression stage, morphology-to-molecule mapping, survival risk, and spatial phenotype -- from a single H&E slide plus optional molecular data.

## install

```bash
pip install -e .
```

or with docker:

```bash
git clone https://github.com/MurariAmbati/tissueshift.git
cd tissueshift
cp .env.example .env
docker compose up
```

## cli

after install, the `tissueshift` command is available:

```bash
tissueshift                     # show banner + commands
tissueshift info                # system and environment check
tissueshift train -c configs/stage1_pretrain.yaml
tissueshift evaluate -t SubtypeCall -p predictions.json -l labels.json
tissueshift preprocess tile -s ./data/slides -o ./data/tiles
tissueshift preprocess extract-features -s ./data/slides -c ./data/tiles -o ./data/features
tissueshift download --subset clinical
tissueshift serve               # start api server on :8000
```

## train

```bash
# stage 1: pretrain pathology encoder + subtype head
tissueshift train -c configs/stage1_pretrain.yaml

# stage 2: finetune all heads
tissueshift train -c configs/stage2_finetune.yaml

# override from cli
tissueshift train -c configs/stage1_pretrain.yaml --epochs 10 --lr 1e-3 --device cpu
```

## evaluate

six benchmark tracks:

| track | task | metric |
|-------|------|--------|
| SubtypeCall | PAM50 subtype from H&E | macro-f1 |
| SubtypeDrift | predict subtype change primary to met | auroc |
| ProgressionStage | pre-invasive to metastatic stage | qwk |
| Morph2Mol | predict expression from morphology | r2 |
| Survival | overall survival risk | c-index |
| SpatialPhenotype | spatial cell neighborhood prediction | r2-til |

```bash
tissueshift evaluate -t SubtypeCall -p predictions.json -l labels.json -o results.json
```

## preprocess

```bash
# tile whole-slide images
tissueshift preprocess tile -s ./data/slides -o ./data/tiles --patch-size 256

# extract features with UNI encoder
tissueshift preprocess extract-features -s ./data/slides -c ./data/tiles -o ./data/features --backbone uni
```

## data

public-data-first approach:

| source | subjects | role |
|--------|----------|------|
| TCGA-BRCA | 1,098 | primary training |
| CPTAC-BRCA | 198 | external validation |
| Human Protein Atlas | -- | protein grounding |
| HTAN Breast | 60+ | spatial atlases |

```bash
tissueshift download --cohort tcga_brca --subset all
```

## structure

```
tissueshift/
  cli/              # click-based cli
  datasets/         # data loaders and manifests
  preprocess/       # tiling, stain norm, feature extraction
  encoders/         # pathology, molecular, spatial encoders
  world_model/      # cross-attention fusion + manifold
  heads/            # prediction heads (6 tracks)
  training/         # training loop and configs
  benchmarks/       # evaluation and baselines
  app/backend/      # fastapi server
  frontend/         # next.js website
  configs/          # yaml training configs
  tests/            # tests
```

## license

apache 2.0
