"""TissueShift command-line interface.

Provides ``tissueshift-train``, ``tissueshift-eval``, ``tissueshift-preprocess``,
and ``tissueshift-infer`` entry-points.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger("tissueshift.cli")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _setup_logging(verbosity: int) -> None:
    level = {0: logging.WARNING, 1: logging.INFO}.get(verbosity, logging.DEBUG)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _load_config(path: str | None):
    from tissueshift.config import TissueShiftConfig

    if path is not None:
        return TissueShiftConfig.from_yaml(path)
    return TissueShiftConfig()


# ===================================================================
# tissueshift-train
# ===================================================================

def _build_train_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("train", help="Run the 6-stage training pipeline")
    p.add_argument("-c", "--config", type=str, default=None, help="Path to YAML config file")
    p.add_argument("--stages", type=str, default=None,
                   help="Comma-separated stage indices to run (e.g. '0,1,3'). Default: all")
    p.add_argument("--resume", type=str, default=None, help="Path to checkpoint to resume from")
    p.add_argument("--output-dir", type=str, default="outputs", help="Output directory for checkpoints and logs")
    p.add_argument("--device", type=str, default=None, help="Device override (e.g. 'cuda:1')")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    p.set_defaults(func=_run_train)


def _run_train(args: argparse.Namespace) -> None:
    import torch
    from tissueshift.world_model.tissueshift_model import TissueShiftModel
    from tissueshift.training.trainer import TissueShiftTrainer

    cfg = _load_config(args.config)

    if args.output_dir:
        cfg.training.checkpoint_dir = str(Path(args.output_dir) / "checkpoints")
        cfg.training.log_dir = str(Path(args.output_dir) / "logs")

    # Seed
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    model = TissueShiftModel(cfg)
    trainer = TissueShiftTrainer(model, cfg)

    if args.device:
        trainer.device = torch.device(args.device)
        trainer.model = trainer.model.to(trainer.device)

    if args.resume:
        trainer.load_checkpoint(args.resume)
        logger.info("Resumed from checkpoint: %s", args.resume)

    # Build a placeholder loader — real usage requires user data setup
    logger.info("NOTE: You must supply your own DataLoaders. Using dry-run mode.")
    logger.info("Example usage in Python:")
    logger.info("  trainer.train_all_stages(train_loader, val_loader)")

    # If stages specified, run only those
    if args.stages:
        stage_indices = [int(s.strip()) for s in args.stages.split(",")]
        for idx in stage_indices:
            logger.info("Training stage %d ...", idx)
            # trainer.train_stage(idx, train_loader, val_loader)
    else:
        logger.info("To run all 6 stages, call trainer.train_all_stages(train_loader, val_loader)")

    logger.info("Model has %s parameters", f"{model.count_parameters():,}")
    logger.info("Training configuration loaded. Output dir: %s", args.output_dir)


# ===================================================================
# tissueshift-eval
# ===================================================================

def _build_eval_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("eval", help="Run the 4-layer evaluation protocol")
    p.add_argument("-c", "--config", type=str, default=None, help="Path to YAML config file")
    p.add_argument("--checkpoint", type=str, required=True, help="Path to model checkpoint")
    p.add_argument("--layers", type=str, default="1,2,3,4",
                   help="Comma-separated evaluation layers (1=subtype, 2=progression, 3=drift, 4=spatial)")
    p.add_argument("--output", type=str, default="eval_results.json", help="Output results file")
    p.add_argument("--bootstrap-n", type=int, default=1000, help="Bootstrap resamples for CI")
    p.add_argument("--device", type=str, default=None, help="Device override")
    p.set_defaults(func=_run_eval)


def _run_eval(args: argparse.Namespace) -> None:
    import json
    import torch
    from tissueshift.world_model.tissueshift_model import TissueShiftModel
    from tissueshift.benchmarks.evaluator import TissueShiftEvaluator

    cfg = _load_config(args.config)
    cfg.eval.bootstrap_n = args.bootstrap_n

    model = TissueShiftModel(cfg)

    # Load checkpoint
    ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    if "model_state_dict" in ckpt:
        model.load_state_dict(ckpt["model_state_dict"])
    else:
        model.load_state_dict(ckpt)
    logger.info("Loaded checkpoint: %s", args.checkpoint)

    if args.device:
        model = model.to(torch.device(args.device))

    evaluator = TissueShiftEvaluator(model, cfg)
    layers = [int(l.strip()) for l in args.layers.split(",")]

    results = {}
    layer_names = {1: "subtype", 2: "progression", 3: "drift", 4: "spatial"}
    for layer_idx in layers:
        name = layer_names.get(layer_idx, f"layer_{layer_idx}")
        logger.info("Evaluating layer %d (%s)...", layer_idx, name)
        # results[name] = evaluator.evaluate_<name>(test_loader)

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Results saved to %s", output_path)


# ===================================================================
# tissueshift-preprocess
# ===================================================================

def _build_preprocess_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("preprocess", help="Run preprocessing pipelines")
    sub = p.add_subparsers(dest="preprocess_cmd")

    # Tile extraction
    tile = sub.add_parser("tiles", help="Extract tiles from WSIs")
    tile.add_argument("--slide-dir", type=str, required=True, help="Directory of WSI files")
    tile.add_argument("--output-dir", type=str, required=True, help="Output directory for tiles")
    tile.add_argument("--tile-size", type=int, default=256, help="Tile size in pixels")
    tile.add_argument("--magnification", type=float, default=20.0, help="Target magnification")
    tile.add_argument("--tissue-threshold", type=float, default=0.5, help="Minimum tissue fraction")
    tile.add_argument("--max-tiles", type=int, default=500, help="Maximum tiles per slide")
    tile.add_argument("--workers", type=int, default=4, help="Number of parallel workers")

    # Stain normalization
    stain = sub.add_parser("stain", help="Normalize stain across slides")
    stain.add_argument("--input-dir", type=str, required=True, help="Directory of tile images")
    stain.add_argument("--output-dir", type=str, required=True, help="Output directory")
    stain.add_argument("--method", type=str, default="macenko", choices=["macenko", "vahadane", "reinhard"])
    stain.add_argument("--reference", type=str, default=None, help="Reference image for normalization")

    # Graph building
    graph = sub.add_parser("graphs", help="Build cell graphs from coordinates")
    graph.add_argument("--input-dir", type=str, required=True, help="Directory of cell coordinate files")
    graph.add_argument("--output-dir", type=str, required=True, help="Output directory for .pt graph files")
    graph.add_argument("--radius", type=float, default=50.0, help="Neighbourhood radius in microns")
    graph.add_argument("--max-neighbours", type=int, default=8, help="Maximum edges per node")

    # Feature harmonization
    harmonize = sub.add_parser("harmonize", help="Harmonize molecular features across datasets")
    harmonize.add_argument("--input-files", type=str, nargs="+", required=True, help="TSV/CSV expression matrices")
    harmonize.add_argument("--output", type=str, required=True, help="Output harmonized matrix")
    harmonize.add_argument("--combat", action="store_true", help="Apply ComBat batch correction")

    p.set_defaults(func=_run_preprocess)


def _run_preprocess(args: argparse.Namespace) -> None:
    if args.preprocess_cmd == "tiles":
        _preprocess_tiles(args)
    elif args.preprocess_cmd == "stain":
        _preprocess_stain(args)
    elif args.preprocess_cmd == "graphs":
        _preprocess_graphs(args)
    elif args.preprocess_cmd == "harmonize":
        _preprocess_harmonize(args)
    else:
        logger.error("Unknown preprocess subcommand. Use: tiles, stain, graphs, harmonize")
        sys.exit(1)


def _preprocess_tiles(args: argparse.Namespace) -> None:
    from tissueshift.preprocess.tile_extraction import TileExtractor

    extractor = TileExtractor(
        tile_size=args.tile_size,
        target_magnification=args.magnification,
        tissue_threshold=args.tissue_threshold,
        max_tiles_per_slide=args.max_tiles,
    )

    slide_dir = Path(args.slide_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    extensions = {".svs", ".ndpi", ".tiff", ".tif", ".mrxs", ".vms", ".vmu"}
    slide_files = [f for f in slide_dir.iterdir() if f.suffix.lower() in extensions]
    logger.info("Found %d slides in %s", len(slide_files), slide_dir)

    for slide_path in slide_files:
        sample_id = slide_path.stem
        sample_dir = output_dir / sample_id
        sample_dir.mkdir(parents=True, exist_ok=True)
        try:
            tiles = extractor.extract(str(slide_path), str(sample_dir))
            logger.info("Extracted %d tiles from %s", len(tiles) if tiles else 0, slide_path.name)
        except Exception as e:
            logger.error("Failed to extract tiles from %s: %s", slide_path.name, e)


def _preprocess_stain(args: argparse.Namespace) -> None:
    from tissueshift.preprocess.stain_normalization import StainNormalizer
    import numpy as np
    from PIL import Image

    normalizer = StainNormalizer(method=args.method)
    if args.reference:
        ref_img = np.array(Image.open(args.reference))
        normalizer.fit(ref_img)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_files = list(input_dir.glob("*.png")) + list(input_dir.glob("*.jpg"))
    logger.info("Normalizing %d images with method=%s", len(image_files), args.method)

    for img_path in image_files:
        try:
            img = np.array(Image.open(img_path))
            normalized = normalizer.transform(img)
            Image.fromarray(normalized).save(output_dir / img_path.name)
        except Exception as e:
            logger.error("Failed to normalize %s: %s", img_path.name, e)


def _preprocess_graphs(args: argparse.Namespace) -> None:
    from tissueshift.preprocess.graph_builder import CellGraphBuilder

    builder = CellGraphBuilder(
        radius=args.radius,
        max_neighbours=args.max_neighbours,
    )

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    coord_files = list(input_dir.glob("*.csv")) + list(input_dir.glob("*.tsv"))
    logger.info("Building graphs from %d coordinate files", len(coord_files))

    for coord_path in coord_files:
        try:
            graph = builder.build_from_csv(str(coord_path))
            import torch
            torch.save(graph, output_dir / f"{coord_path.stem}.pt")
            logger.info("Built graph from %s", coord_path.name)
        except Exception as e:
            logger.error("Failed to build graph from %s: %s", coord_path.name, e)


def _preprocess_harmonize(args: argparse.Namespace) -> None:
    import pandas as pd
    from tissueshift.preprocess.feature_harmonization import FeatureHarmonizer

    matrices = []
    batch_labels = []
    for i, fpath in enumerate(args.input_files):
        df = pd.read_csv(fpath, sep="\t", index_col=0)
        matrices.append(df)
        batch_labels.extend([f"batch_{i}"] * len(df))
        logger.info("Loaded %s: %d samples × %d features", fpath, *df.shape)

    harmonizer = FeatureHarmonizer()
    combined = pd.concat(matrices, axis=0)

    # Gene alias resolution
    combined = harmonizer.resolve_aliases(combined)

    if args.combat:
        combined = harmonizer.combat_correct(combined, batch_labels)

    combined = harmonizer.quantile_normalize(combined)
    combined.to_csv(args.output, sep="\t")
    logger.info("Harmonized matrix saved to %s: %d × %d", args.output, *combined.shape)


# ===================================================================
# tissueshift-infer
# ===================================================================

def _build_infer_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("infer", help="Run inference on new samples")
    p.add_argument("-c", "--config", type=str, default=None, help="Path to YAML config file")
    p.add_argument("--checkpoint", type=str, required=True, help="Path to model checkpoint")
    p.add_argument("--slide", type=str, default=None, help="Path to WSI file for pathology inference")
    p.add_argument("--rna", type=str, default=None, help="Path to RNA expression TSV (genes × 1)")
    p.add_argument("--graph", type=str, default=None, help="Path to cell graph .pt file")
    p.add_argument("--output", type=str, default="prediction.json", help="Output prediction file")
    p.add_argument("--device", type=str, default=None, help="Device override")
    p.set_defaults(func=_run_infer)


def _run_infer(args: argparse.Namespace) -> None:
    import json
    import torch

    if not any([args.slide, args.rna, args.graph]):
        logger.error("Must provide at least one of --slide, --rna, or --graph")
        sys.exit(1)

    cfg = _load_config(args.config)
    device = torch.device(args.device if args.device else ("cuda" if torch.cuda.is_available() else "cpu"))

    from tissueshift.world_model.tissueshift_model import TissueShiftModel
    model = TissueShiftModel(cfg)
    ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    if "model_state_dict" in ckpt:
        model.load_state_dict(ckpt["model_state_dict"])
    else:
        model.load_state_dict(ckpt)
    model = model.to(device)
    model.eval()

    batch = {}

    # Load pathology tiles
    if args.slide:
        from tissueshift.preprocess.tile_extraction import TileExtractor
        extractor = TileExtractor(tile_size=cfg.data.tile_size)
        tiles = extractor.extract_to_tensor(args.slide)
        if tiles is not None:
            batch["tile_embeddings"] = tiles.unsqueeze(0).to(device)
            logger.info("Loaded %d tiles from %s", tiles.shape[0], args.slide)

    # Load RNA expression
    if args.rna:
        import pandas as pd
        rna_df = pd.read_csv(args.rna, sep="\t", index_col=0)
        rna_tensor = torch.tensor(rna_df.values.flatten(), dtype=torch.float32)
        batch["gene_expression"] = rna_tensor.unsqueeze(0).to(device)
        logger.info("Loaded RNA expression: %d genes", rna_tensor.shape[0])

    # Load cell graph
    if args.graph:
        graph = torch.load(args.graph, map_location=device, weights_only=False)
        batch["cell_graph"] = graph
        logger.info("Loaded cell graph from %s", args.graph)

    # Run inference
    with torch.no_grad():
        outputs = model(batch)

    # Format results
    results = {}
    for key, val in outputs.items():
        if isinstance(val, torch.Tensor):
            if val.numel() <= 20:
                results[key] = val.cpu().tolist()
            else:
                results[key] = {"shape": list(val.shape), "mean": val.mean().item()}
        elif isinstance(val, dict):
            results[key] = {
                k: v.cpu().tolist() if isinstance(v, torch.Tensor) and v.numel() <= 20
                else {"shape": list(v.shape), "mean": v.mean().item()} if isinstance(v, torch.Tensor)
                else v
                for k, v in val.items()
            }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Predictions saved to %s", output_path)


# ===================================================================
# Main dispatcher
# ===================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tissueshift",
        description="TissueShift: Temporal Histopathology-to-Omics Model for Breast Cancer",
    )
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase verbosity (-v info, -vv debug)")

    subparsers = parser.add_subparsers(dest="command")
    _build_train_parser(subparsers)
    _build_eval_parser(subparsers)
    _build_preprocess_parser(subparsers)
    _build_infer_parser(subparsers)

    args = parser.parse_args()
    _setup_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
