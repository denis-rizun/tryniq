# Evaluation runbook

## One-time setup

Use Python 3.13 and install all metric extras:

```bash
cd evals
make env
cp .env.example .env
```

Configure `LANGFUSE_BASE_URL`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY`. Semantic
suites also require an explicit `EVAL_JUDGE_MODEL`; there is no default. Release
qualification rejects self-judging when the judge matches the model under test.

Start the isolated application stack:

```bash
make eval-infra-up
```

The stack uses database `tryniq_eval`, bucket `tryniq-eval`, object prefix `eval-runs/`,
Redis database 15 with namespace `tryniq-eval`, and Langfuse environment `evaluation`.
The startup guard rejects production-like values.

## Dataset synchronization

For the foundation contract:

```bash
make dataset-foundation
export EVAL_DATASET_CHECKSUM=819ce3cda4d8411f29dcaa359095647eb2db5e700909f4d0fb1a83581450493f
```

Synchronization preflights an existing dataset and aborts on checksum or item-count
mismatch. Published datasets are never edited. Corrections require a new semantic version.

## Running suites

```bash
make eval-smoke
make eval-nightly
make eval-speech-final
make eval-speech-diarization
make eval-release
```

Run speech targets on the host that provides the production runtime. Local and scheduled
targets use the same suite modules as the future GitHub experiment action.

Every successful target prints `dataset_run_url`. Use that URL to inspect items, linked
traces, score reasons, failures, run-level percentiles, confidence intervals, and slices.
No local JSON/Markdown output is authoritative.

Schedule `make eval-online-once` separately from benchmark jobs. It only accepts
`staging` or `production`, samples at the hard-capped 5%/1% rates, redacts trace payloads
before judging, stops at the configured monthly cost cap, and writes the DeepEval score
to the original trace.

## Approving a baseline

1. Run the complete immutable test dataset.
2. Inspect failures, required slices, trace metadata, and judge reasoning in Langfuse.
3. Obtain engineering-lead approval.
4. Pin the immutable dataset run ID in `gates/suites.yaml`.
5. Record the run URL in the suite documentation/model card.

Until a baseline ID is pinned, release qualification fails closed.

## Exceptions

Add an exception to `gates/exceptions.yaml` only with:

- one suite and metric;
- failing slices;
- an owner and reason;
- the immutable Langfuse run URL;
- an expiry date.

Expired exceptions do not apply. Hard-invariant exceptions require the same review as a
baseline change.

## Failure handling

Task adapters catch production-boundary failures and return a typed outcome. Unexpected
failures remain visible, increment failure rate, and receive zero for release-gated
quality metrics. Latency remains absent when it was not measured. Only declared hardware
or license preconditions may skip an item.

## Troubleshooting

- Safety guard failure: compare `.env` with `.env.example`; do not weaken the guard.
- Dataset mismatch: publish a new patch/minor/major dataset name based on the change.
- Missing judge: set `EVAL_JUDGE_MODEL` to an approved model distinct from the candidate.
- Inconclusive release: increase sample size or reduce variance; do not waive by rerunning
  until a favorable random sample appears.
- Missing run URL: the experiment used local data instead of a Langfuse dataset.

Stop the isolated stack with `make eval-infra-down`.
