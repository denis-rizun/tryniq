# Tryniq evaluations

Tryniq evaluations run as Langfuse Experiments. Langfuse owns immutable datasets, item
traces, scores, run comparisons, and approved baselines. DeepEval is used only as an
embedded semantic metric engine; jiwer, pyannote.metrics, ranx, SciPy, and scikit-learn
provide maintained deterministic metrics.

The package intentionally has no evaluation CLI, registry, scheduler, result directory,
or report generator. Every suite module exports:

```python
def experiment(context: RunnerContext): ...
```

and calls `context.run_experiment(...)` directly. This is compatible with the Langfuse
experiment action while supporting local and scheduled-host execution now.

## Quick start

1. Copy `.env.example` to `.env` and provide Langfuse credentials.
2. Start isolated application dependencies with `make eval-infra-up`.
3. Install the pinned Python 3.13 environments with `make env`.
4. Sync the immutable smoke dataset with `make dataset-foundation`.
5. Set `EVAL_DATASET_CHECKSUM` to the manifest content checksum.
6. Run `make eval-smoke`.

The target prints the immutable Langfuse run URL and writes no local canonical result
file. `make eval-release` returns nonzero for missing baselines, failed hard invariants,
threshold/regression failures, expired exceptions, missing metrics, and inconclusive
confidence intervals.

## Layout

```text
evals/
├── compose.yml                 isolated EVAL application infrastructure
├── datasets/
│   ├── manifests/              Git-authored immutable source manifests
│   └── items/                  small, safe golden fixtures
├── gates/                      thresholds and expiring exceptions
├── src/tryniq_evals/
│   ├── adapters/               production/DeepEval conversion only
│   ├── datasets/               validation and immutable Langfuse sync
│   ├── evaluators/             provider-backed and invariant evaluators
│   ├── gates/                  release qualification
│   └── suites/                 one Langfuse experiment per product area
└── tests/                      contract and evaluator tests
```

`src/eval/`, `envs/`, `RESULTS.md`, and the original speech model-card material are a
read-only migration archive. They remain until replacement speech baselines are approved.
Their Typer command and report generator are no longer installed or exposed by Make.

## Dependency isolation

The base package contains Langfuse, statistics, ranking, and contracts. Extras isolate:

- `llm`: DeepEval 4.1.4.
- `speech`: jiwer 4.0.0, pyannote.metrics 4.1, and text/audio support.
- `dev`: pytest and Ruff.

Model runtimes remain on their production hosts. Each host runs its own Langfuse
experiment directly; there is no subprocess sentinel protocol or central model scheduler.
The SDK/server compatibility evidence and exact self-hosted image digests are recorded in
[COMPATIBILITY.md](./COMPATIBILITY.md).

## Safety and privacy

Application-backed suites refuse to start unless Postgres, MinIO, Redis, and the Langfuse
environment are visibly evaluation-scoped. Fixture IDs and object prefixes are derived
from run ID plus stable item ID; cleanup validates the resolved run prefix.

Dataset items may contain logical object-store URIs and immutable hashes, but never local
paths, signed URLs, secrets, or raw production identifiers. See [DATASETS.md](./DATASETS.md)
and [ANNOTATION_GUIDE.md](./ANNOTATION_GUIDE.md).
