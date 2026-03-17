"""Semi-automated region annotation for WSI patches using feature clustering."""

from __future__ import annotations

import logging
from pathlib import Path

import h5py
import numpy as np

logger = logging.getLogger(__name__)

# Region type labels
REGION_TYPES = [
    "tumor_epithelium",
    "stroma",
    "necrosis",
    "immune_rich",
    "ductal_structure",
    "invasive_front",
    "adipose",
]


def annotate_regions_by_clustering(
    features_file: str | Path,
    n_clusters: int = 7,
    method: str = "kmeans",
) -> np.ndarray:
    """Assign region labels to patches by clustering their feature vectors.

    Args:
        features_file: Path to HDF5 file with patch features
        n_clusters: Number of region clusters
        method: Clustering method ("kmeans" or "spectral")

    Returns:
        Array of cluster labels (n_patches,)
    """
    from sklearn.cluster import KMeans, MiniBatchKMeans

    with h5py.File(features_file, "r") as f:
        features = f["features"][:]
        n_patches = features.shape[0]

    if n_patches == 0:
        return np.array([], dtype=np.int64)

    logger.info(f"Clustering {n_patches} patches into {n_clusters} regions...")

    # Use MiniBatchKMeans for large feature sets
    if n_patches > 10000:
        clusterer = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=1024)
    else:
        clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)

    labels = clusterer.fit_predict(features)

    # Log cluster sizes
    unique, counts = np.unique(labels, return_counts=True)
    for u, c in zip(unique, counts):
        logger.info(f"  Cluster {u}: {c} patches ({100 * c / n_patches:.1f}%)")

    return labels


def save_region_annotations(
    features_file: str | Path,
    labels: np.ndarray,
    region_names: list[str] | None = None,
) -> None:
    """Save region annotations into the existing HDF5 feature file."""
    if region_names is None:
        region_names = REGION_TYPES[:len(np.unique(labels))]

    with h5py.File(features_file, "a") as f:
        if "region_labels" in f:
            del f["region_labels"]
        f.create_dataset("region_labels", data=labels)
        f.attrs["region_types"] = region_names

    logger.info(f"Saved region annotations to {features_file}")


def annotate_cohort(
    features_dir: str | Path,
    n_clusters: int = 7,
) -> None:
    """Annotate regions for all slides in a features directory."""
    features_dir = Path(features_dir)
    h5_files = sorted(features_dir.glob("*.h5"))

    logger.info(f"Annotating regions for {len(h5_files)} slides...")

    for h5_file in h5_files:
        try:
            labels = annotate_regions_by_clustering(h5_file, n_clusters=n_clusters)
            save_region_annotations(h5_file, labels)
        except Exception as e:
            logger.error(f"Failed to annotate {h5_file.name}: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Region annotation for WSI patches")
    parser.add_argument("--features-dir", required=True)
    parser.add_argument("--n-clusters", type=int, default=7)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    annotate_cohort(args.features_dir, n_clusters=args.n_clusters)
