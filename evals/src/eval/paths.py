
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
