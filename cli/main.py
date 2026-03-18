"""TissueShift CLI — pip install tissueshift && tissueshift --help"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from cli.display import (
    VERSION,
    print_banner,
    print_done,
    print_err,
    print_footer,
    print_header,
    print_kv,
    print_ok,
    print_step,
    print_warn,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resolve(p: str) -> Path:
    return Path(p).expanduser().resolve()


# ── Root group ────────────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.version_option(VERSION, prog_name="tissueshift")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """TissueShift -- Open Temporal Histopathology-to-Omics Model."""
    if ctx.invoked_subcommand is None:
        print_banner()
        click.echo(ctx.get_help())
        print_footer()


# ── info ──────────────────────────────────────────────────────────────────────


@cli.command()
def info() -> None:
    """Display system and environment information."""
    import platform

    print_banner()
    print_header("SYSTEM INFORMATION")

    print_kv("Python", f"{platform.python_version()}  ({sys.executable})")
    print_kv("Platform", platform.platform())

    try:
        import torch

        print_kv("PyTorch", torch.__version__)
        if torch.cuda.is_available():
            print_kv("CUDA", torch.version.cuda or "n/a")
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                mem = torch.cuda.get_device_properties(i).total_mem / (1024**3)
                print_kv(f"  GPU {i}", f"{name}  ({mem:.1f} GB)")
        else:
            print_kv("CUDA", "not available")
    except ImportError:
        print_kv("PyTorch", "not installed")

    optional = [
        ("timm", "timm"),
        ("monai", "monai"),
        ("tiatoolbox", "tiatoolbox"),
        ("torch_geometric", "torch-geometric"),
        ("sksurv", "scikit-survival"),
        ("openslide", "openslide-python"),
        ("h5py", "h5py"),
        ("wandb", "wandb"),
    ]

    print_header("INSTALLED PACKAGES")
    for mod, label in optional:
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "ok")
            print_kv(label, ver)
        except ImportError:
            print_kv(label, "-- not installed --")

    print_footer()


# ── train ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--config", "-c", required=True, type=click.Path(exists=True), help="Path to YAML config file.")
@click.option("--data-dir", "-d", type=click.Path(), default=None, help="Override data directory.")
@click.option("--epochs", "-e", type=int, default=None, help="Override number of epochs.")
@click.option("--batch-size", "-b", type=int, default=None, help="Override batch size.")
@click.option("--lr", type=float, default=None, help="Override learning rate.")
@click.option("--device", type=click.Choice(["cuda", "cpu"]), default=None, help="Device.")
def train(config: str, data_dir: str | None, epochs: int | None, batch_size: int | None, lr: float | None, device: str | None) -> None:
    """Train the TissueShift model from a YAML configuration."""
    print_banner()
    print_header("TRAINING")

    print_step(1, 3, "Loading configuration")
    from training.train import TrainConfig, train as run_train

    cfg = TrainConfig.from_yaml(config)
    print_kv("Config file", config)
    print_kv("Stage", cfg.stage)

    if data_dir is not None:
        cfg.data_dir = data_dir
    if epochs is not None:
        cfg.epochs = epochs
    if batch_size is not None:
        cfg.batch_size = batch_size
    if lr is not None:
        cfg.lr = lr
    if device is not None:
        cfg.device = device

    print_kv("Data directory", cfg.data_dir)
    print_kv("Epochs", str(cfg.epochs))
    print_kv("Batch size", str(cfg.batch_size))
    print_kv("Learning rate", f"{cfg.lr:.2e}")
    print_kv("Device", cfg.device)
    print_kv("Mixed precision", str(cfg.mixed_precision))
    print_kv("Checkpoint dir", cfg.checkpoint_dir)

    print_step(2, 3, "Initialising model and data loaders")
    print_step(3, 3, "Starting training loop")

    try:
        run_train(cfg)
        print_ok("Training complete")
    except KeyboardInterrupt:
        print_warn("Training interrupted by user")
        sys.exit(130)
    except Exception as exc:
        print_err(str(exc))
        sys.exit(1)

    print_footer()


# ── evaluate ──────────────────────────────────────────────────────────────────


TRACKS = [
    "SubtypeCall",
    "SubtypeDrift",
    "ProgressionStage",
    "Morph2Mol",
    "Survival",
    "SpatialPhenotype",
]


@cli.command()
@click.option("--track", "-t", required=True, type=click.Choice(TRACKS), help="Benchmark track.")
@click.option("--predictions", "-p", required=True, type=click.Path(exists=True), help="Predictions JSON.")
@click.option("--labels", "-l", required=True, type=click.Path(exists=True), help="Ground-truth labels JSON.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Save results to JSON.")
def evaluate(track: str, predictions: str, labels: str, output: str | None) -> None:
    """Evaluate predictions on a TissueShift benchmark track."""
    import json

    print_banner()
    print_header(f"EVALUATE -- {track}")

    print_step(1, 3, "Loading data")
    from benchmarks.evaluate import evaluate_track, load_labels, load_predictions, validate_submission

    preds = load_predictions(predictions)
    lbls = load_labels(labels)
    print_kv("Predictions", predictions)
    print_kv("Labels", labels)

    print_step(2, 3, "Validating submission")
    errors = validate_submission(preds, track)
    if errors:
        for e in errors:
            print_err(e)
        sys.exit(1)
    print_ok("Submission valid")

    print_step(3, 3, "Computing metrics")
    results = evaluate_track(track, preds, lbls)

    print_header("RESULTS")
    for metric, value in results.items():
        print_kv(metric, f"{value:.6f}")

    if output:
        out = _resolve(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, indent=2))
        print_ok(f"Results saved to {out}")

    print_footer()


# ── preprocess ────────────────────────────────────────────────────────────────


@cli.group()
def preprocess() -> None:
    """Preprocessing utilities (tile, extract-features, stain-normalise)."""


@preprocess.command("tile")
@click.option("--slides-dir", "-s", required=True, type=click.Path(exists=True), help="Directory of whole-slide images.")
@click.option("--output-dir", "-o", required=True, type=click.Path(), help="Output directory for tile coordinates.")
@click.option("--patch-size", type=int, default=256, show_default=True, help="Patch size in pixels.")
@click.option("--min-tissue", type=float, default=0.30, show_default=True, help="Minimum tissue fraction per patch.")
@click.option("--save-patches", is_flag=True, default=False, help="Also save patch images to disk.")
def tile(slides_dir: str, output_dir: str, patch_size: int, min_tissue: float, save_patches: bool) -> None:
    """Tile whole-slide images into patch coordinates."""
    print_banner()
    print_header("TILING")

    print_kv("Slides directory", slides_dir)
    print_kv("Output directory", output_dir)
    print_kv("Patch size", f"{patch_size} px")
    print_kv("Min tissue fraction", f"{min_tissue:.0%}")
    print_kv("Save patches", str(save_patches))

    from preprocess.tiling import tile_cohort

    results = tile_cohort(
        slides_dir=slides_dir,
        output_dir=output_dir,
        patch_size=patch_size,
        min_tissue_fraction=min_tissue,
    )
    print_ok(f"Tiled {len(results)} slides")
    print_footer()


@preprocess.command("extract-features")
@click.option("--slides-dir", "-s", required=True, type=click.Path(exists=True), help="Directory of whole-slide images.")
@click.option("--coords-dir", "-c", required=True, type=click.Path(exists=True), help="Directory of tile coordinate CSVs.")
@click.option("--output-dir", "-o", required=True, type=click.Path(), help="Output directory for HDF5 features.")
@click.option("--backbone", type=click.Choice(["uni", "ctranspath"]), default="uni", show_default=True, help="Feature extractor backbone.")
@click.option("--batch-size", "-b", type=int, default=64, show_default=True, help="Extraction batch size.")
@click.option("--num-workers", "-w", type=int, default=4, show_default=True, help="Data loader workers.")
def extract_features(slides_dir: str, coords_dir: str, output_dir: str, backbone: str, batch_size: int, num_workers: int) -> None:
    """Extract patch-level features from tiled slides."""
    print_banner()
    print_header("FEATURE EXTRACTION")

    print_kv("Slides directory", slides_dir)
    print_kv("Coords directory", coords_dir)
    print_kv("Output directory", output_dir)
    print_kv("Backbone", backbone)
    print_kv("Batch size", str(batch_size))
    print_kv("Workers", str(num_workers))

    from preprocess.feature_extract import (
        CTransPathExtractor,
        UNIExtractor,
        extract_features_for_cohort,
    )

    extractor = UNIExtractor() if backbone == "uni" else CTransPathExtractor()
    print_kv("Feature dim", str(extractor.feature_dim))

    results = extract_features_for_cohort(
        slides_dir=slides_dir,
        coords_dir=coords_dir,
        output_dir=output_dir,
        extractor=extractor,
        batch_size=batch_size,
        num_workers=num_workers,
    )
    print_ok(f"Extracted features for {len(results)} slides")
    print_footer()


# ── download ──────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--cohort", type=click.Choice(["tcga_brca"]), default="tcga_brca", show_default=True, help="Dataset cohort.")
@click.option("--data-dir", "-d", type=click.Path(), default="./data/tcga_brca", show_default=True, help="Download destination.")
@click.option("--subset", type=click.Choice(["clinical", "expression", "slides", "all"]), default="all", show_default=True, help="Which data subset to download.")
def download(cohort: str, data_dir: str, subset: str) -> None:
    """Download datasets from public repositories."""
    print_banner()
    print_header(f"DOWNLOAD -- {cohort.upper()}")

    print_kv("Cohort", cohort)
    print_kv("Data directory", data_dir)
    print_kv("Subset", subset)

    from datasets.tcga_brca import TCGABRCADataset

    ds = TCGABRCADataset(data_dir=data_dir)

    if subset == "all":
        for part in ["clinical", "expression", "slides"]:
            print_step(["clinical", "expression", "slides"].index(part) + 1, 3, f"Downloading {part}")
            try:
                ds.download(subset=part)
                print_ok(f"{part} complete")
            except Exception as exc:
                print_warn(f"{part} failed: {exc}")
    else:
        print_step(1, 1, f"Downloading {subset}")
        ds.download(subset=subset)
        print_ok(f"{subset} complete")

    print_footer()


# ── serve ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--host", type=str, default="0.0.0.0", show_default=True, help="Bind host.")
@click.option("--port", "-p", type=int, default=8000, show_default=True, help="Bind port.")
@click.option("--reload", "do_reload", is_flag=True, default=False, help="Auto-reload on code changes.")
@click.option("--workers", "-w", type=int, default=1, show_default=True, help="Number of workers.")
def serve(host: str, port: int, do_reload: bool, workers: int) -> None:
    """Start the TissueShift API server."""
    print_banner()
    print_header("API SERVER")

    print_kv("Host", host)
    print_kv("Port", str(port))
    print_kv("Workers", str(workers))
    print_kv("Auto-reload", str(do_reload))
    print_kv("Docs", f"http://{host}:{port}/docs")

    import uvicorn

    print_ok("Starting server")
    uvicorn.run(
        "app.backend.main:app",
        host=host,
        port=port,
        reload=do_reload,
        workers=workers,
    )


# ── entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
