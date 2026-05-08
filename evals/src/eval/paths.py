"""Filesystem paths used by the harness.

Datasets live under ``<repo>/datasets/`` by default — co-located with the
evals/ source tree so a fresh clone can put audio next to the code rather than
hidden in the user's home cache. ``TRYNIQ_EVALS_CACHE`` overrides the location.
The whole ``datasets/`` directory is in ``.gitignore`` (large binary audio +
restrictive licenses).
"""

import os
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = EVALS_ROOT.parent
ENVS_ROOT = EVALS_ROOT / "envs"
RESULTS_ROOT = EVALS_ROOT / "results"

CACHE_ROOT = Path(os.environ.get("TRYNIQ_EVALS_CACHE", REPO_ROOT / "datasets"))


def dataset_cache(name: str) -> Path:
    return CACHE_ROOT / name


def env_dir(family: str) -> Path:
    return ENVS_ROOT / family
