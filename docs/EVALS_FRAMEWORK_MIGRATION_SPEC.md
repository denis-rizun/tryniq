# Evaluation Framework Migration Specification

**Status:** Proposed

**Audience:** Backend, AI/ML, platform, and QA engineers

**Scope:** Complete replacement of the current `evals/` implementation

**Last updated:** 2026-07-29

## 1. Executive summary

Replace the self-built evaluation harness in `evals/` with a deliberately layered stack:

- **Langfuse Experiments** is the evaluation platform, experiment runner, and single system of record for datasets, runs, traces, and scores.
- **DeepEval** is the LLM and RAG metric engine executed inside Langfuse evaluator functions.
- **jiwer** is the ASR metric engine.
- **pyannote.metrics** is the diarization metric engine.

The project already self-hosts Langfuse v3 and sends OpenAI-compatible model calls through the Langfuse client. Reusing it provides datasets, experiment runs, per-item results, traces, scores, comparisons, dashboards, and production monitoring without maintaining another runner, registry, results format, or report generator.

DeepEval adds a purpose-built evaluation layer for faithfulness, answer relevancy, contextual precision/recall, summarization, G-Eval rubrics, and other semantic quality metrics. It does not own datasets, traces, experiment history, or a second result UI in this project.

The replacement must evaluate the production paths for:

- Live ASR.
- Final ASR.
- Uploaded-recording diarization.
- Graph extraction and graph deduplication.
- Post-meeting metadata extraction.
- Utterance and graph retrieval for chat.
- Chat answer generation and citations.
- Related-meeting ranking.
- Embeddings and similarity thresholds.
- AI inference reliability, latency, usage, and cost.
- End-to-end meeting intelligence quality.

The current public speech datasets remain useful. QMSum and the full AMI annotations are added for meeting RAG, summarization, topic, decision, and action-item evaluation.

## 2. Decision

### 2.1 Selected stack

| Responsibility | Selected component | Reason |
|---|---|---|
| Dataset catalog and experiment orchestration | Langfuse Experiments | Already deployed; provides concurrent execution, error isolation, traces, item-level evaluators, run-level evaluators, and run comparisons |
| Evaluation result storage and dashboards | Langfuse scores and dataset runs | Removes custom `summary.json`, result collection, and Markdown table generation |
| LLM and RAG semantic metrics | DeepEval | Purpose-built evaluation metrics, thresholds, score reasoning, G-Eval, DAG metrics, and component-level RAG evaluation |
| ASR scoring | jiwer | Standard WER/MER/WIL/WIP computation |
| Diarization scoring | pyannote.metrics | Standard DER/JER and error decomposition |
| Retrieval scoring | Standard deterministic IR formulas | Precision@k, Recall@k, Hit Rate@k, MRR, MAP, and nDCG@k |
| Project-specific semantic scoring | DeepEval G-Eval or DAG metrics | Versioned, human-calibrated rubrics for correctness, factuality, coverage, and unsupported claims |
| Human review | Langfuse annotations | Calibration, disputed cases, and golden-set maintenance |
| Runtime telemetry | Langfuse traces and metrics | Existing integration already captures model calls; extend it to retrieval and pipeline spans |

Official references:

- [Langfuse evaluation concepts](https://langfuse.com/docs/evaluation/core-concepts)
- [Langfuse Experiments via SDK](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk)
- [Langfuse observability](https://langfuse.com/docs/observability/overview)
- [Official Langfuse guide for using DeepEval](https://langfuse.com/resources/engineering/deepeval)
- [DeepEval metric catalog](https://deepeval.com/docs/metrics-introduction)
- [DeepEval RAG evaluation](https://deepeval.com/docs/getting-started-rag)
- [DeepEval CI/CD evaluation](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd)

### 2.2 Architectural rule

Langfuse is the authoritative store for:

- Dataset identity.
- Experiment identity.
- Per-item inputs, outputs, expected outputs, metadata, and errors.
- Item-level scores.
- Run-level aggregate scores.
- Model, prompt, application, and environment metadata.
- Links between an experiment item and its execution trace.

Files in Git are authoritative for:

- Dataset source declarations and licenses.
- Immutable golden labels that are safe to commit.
- Evaluation suite definitions.
- Evaluator rubrics.
- Thresholds and release gates.
- Dataset import and normalization rules.

Large audio, restricted corpora, and production data must not be committed. They remain in the existing ignored dataset cache or an evaluation-only MinIO bucket.

### 2.3 Framework ownership boundaries

The tools must not compete for ownership:

| Concern | Sole owner |
|---|---|
| Dataset identity and version | Langfuse |
| Experiment execution and concurrency | Langfuse Experiments |
| Trace and observation storage | Langfuse |
| Item-level and run-level score storage | Langfuse |
| Comparison UI and dashboards | Langfuse |
| LLM/RAG semantic score calculation | DeepEval |
| ASR score calculation | jiwer |
| Diarization score calculation | pyannote.metrics |
| Deterministic project invariants and IR calculations | Small evaluator functions using maintained standard libraries |

DeepEval runs in the project’s evaluation process and returns a score, success status, and reason. A thin Langfuse evaluator adapter converts that result into a Langfuse score attached to the experiment item and trace.

The project must not:

- Use Confident AI as a second result store or dashboard.
- Upload official runs to both Langfuse and Confident AI.
- Maintain canonical datasets in both Langfuse and DeepEval.
- Use DeepEval tracing in production alongside Langfuse tracing.
- Use `deepeval test run` as a second official experiment runner.
- Give DeepEval responsibility for run comparison or release history.

DeepEval’s pytest integration may be used to test evaluator adapters themselves, but official smoke, nightly, benchmark, and release suites must be Langfuse dataset runs.

### 2.4 Why not introduce another complete platform

MLflow and other complete evaluation/tracking products can solve parts of this problem, but a second experiment database and UI would duplicate the Langfuse deployment already present in `backend/compose.yml`. DeepEval is deliberately embedded as a metric engine rather than deployed as a competing platform.

### 2.5 What must not be rebuilt

The new module must not contain:

- A custom experiment runner.
- A custom model or dataset registry.
- A custom subprocess sentinel protocol.
- A custom result directory format.
- A custom aggregation engine.
- A custom dashboard.
- A custom Markdown table generator.
- Reimplementations of WER, DER, JER, precision, recall, F1, MRR, MAP, nDCG, ROUGE, or metrics already provided by DeepEval.

Small adapters are permitted only to convert production outputs into a framework or metric-provider input contract.

## 3. Current-state findings

The existing `evals/` package is limited to an ASR and diarization model bake-off. It contains approximately 1,800 lines of custom framework code in:

- `src/eval/cli.py`
- `src/eval/registry.py`
- `src/eval/runner.py`
- `src/eval/diar_runner.py`
- `src/eval/report.py`
- `src/eval/types.py`
- `src/eval/metrics/`

It also maintains:

- A custom Typer CLI.
- A hand-written model and dataset registry.
- Separate cold and warm subprocess runners.
- A sentinel-based JSON protocol between model environments.
- Custom memory and latency sampling.
- Custom bootstrap and WER aggregation.
- Custom result selection and Markdown report generation.

This design creates the following product gaps:

- It evaluates model candidates rather than the deployed application behavior.
- It does not evaluate graph extraction, metadata, retrieval, RAG answers, citations, embeddings, related meetings, or AI request reliability.
- Results are local files and cannot be compared or filtered in the existing Langfuse UI.
- Production failures cannot flow back into a golden dataset.
- Failed items may be counted separately from quality aggregates, which can make a failing model look better than it is.
- The same orchestration, scoring, storage, and reporting concepts must be maintained by the project.

## 4. Goals and non-goals

### 4.1 Goals

The migration must:

1. Replace the current evaluation orchestration with Langfuse Experiments and standardized metric engines.
2. Evaluate production services and clients instead of duplicate evaluation-only implementations.
3. Cover speech, structured extraction, metadata, retrieval, RAG generation, embeddings, and end-to-end quality.
4. Track accuracy, precision, recall, F1, ranking quality, grounding, latency, reliability, token usage, and cost where each metric is meaningful.
5. Support local development, pull-request smoke tests, nightly evaluation, release qualification, and sampled production monitoring.
6. Make every score traceable to a dataset item, application revision, model, prompt version, configuration, and execution trace.
7. Preserve the useful public datasets already documented by the project.
8. Add immediately accessible sources for missing meeting-understanding datasets.
9. Treat hard application invariants as release blockers.
10. Make adding a new suite mostly configuration, production-path invocation, and framework-native evaluators.
11. Use DeepEval for LLM/RAG semantic evaluation without introducing Confident AI or a second experiment lifecycle.

### 4.2 Non-goals

This migration does not:

- Train or fine-tune models.
- Change the production model selections.
- Replace ordinary unit, integration, or API tests.
- Move production application data into a public SaaS.
- Create an evaluation UI outside Langfuse.
- Guarantee that an LLM judge is correct without human calibration.
- Treat one aggregate score as sufficient evidence of product quality.
- Force incompatible ML runtimes into one Python environment.

## 5. Evaluation principles

### 5.1 Evaluate the production path

Each experiment task must call the same boundary used by the application:

| Evaluation area | Production boundary |
|---|---|
| Final ASR | Final ASR client/service used by the worker |
| Live ASR | Built Swift streamer and its real wire contract |
| Upload diarization | Upload diarization client used by `process_upload` |
| Graph extraction | Graph extractor and graph application services |
| Metadata | Metadata extractor and writer services |
| RAG retrieval | `ChatRetriever`, including utterance and graph retrieval |
| RAG answer | `ChatResponder` with the production prompt builder |
| Embeddings | Shared `AIClient.embed` path |
| Related meetings | `RelatedMeetingsFinder` |

An evaluation-only copy of prompts, schemas, retrieval SQL, post-processing, or citation handling is prohibited.

### 5.2 Use the correct metric for the task

“Accuracy” is not a universal AI metric:

- Use WER and related speech metrics for transcription.
- Use precision, recall, and F1 for extracted sets and classifications.
- Use Precision@k, Recall@k, MRR, MAP, and nDCG for ranked retrieval.
- Use citation precision and recall for grounding.
- Use exact schema and invariant checks for structured outputs.
- Use accuracy for binary or multiclass tasks such as answerability, speaker matching, status classification, and successful abstention.
- Use calibrated DeepEval LLM-backed scores only for semantic properties that lack an objective label.

### 5.3 Prefer deterministic evaluators

Evaluator priority is:

1. Exact deterministic check.
2. Standard maintained metric implementation.
3. Semantic similarity with a locked embedding model.
4. Versioned DeepEval LLM-backed metric or G-Eval/DAG rubric.
5. Human review.

A DeepEval LLM-backed metric must never replace a deterministic grounding, ID validity, schema, latency, cost, or ranking calculation.

### 5.4 Count failures honestly

Every dataset item ends in exactly one of:

- Completed and scored.
- Failed with a typed failure category.
- Skipped for a declared hardware or license constraint.

Unexpected failures must score zero for release-gated quality metrics and increment the failure rate. They must never disappear from aggregates. Declared skips are excluded only when the experiment metadata proves that the run was not intended for that hardware or dataset.

### 5.5 Separate offline evaluation from online monitoring

- **Offline experiments** compare controlled application versions on immutable datasets.
- **Online evaluation** scores sampled production or staging traces for drift and newly observed failures.
- A production trace promoted to a golden dataset must be reviewed, redacted, labeled, and assigned to a versioned dataset before it becomes a release gate.

## 6. Target architecture

### 6.1 Logical flow

1. A developer selects a named evaluation suite and immutable dataset version.
2. The suite loads the dataset from Langfuse.
3. Langfuse’s experiment runner executes the suite task for every item.
4. The task invokes the production application boundary.
5. The execution produces a Langfuse trace containing the full pipeline.
6. DeepEval metrics evaluate LLM/RAG outputs in the evaluation process and return scores with reasoning.
7. jiwer, pyannote.metrics, and deterministic evaluators score speech, diarization, retrieval, and application invariants.
8. Run-level evaluators aggregate micro, macro, percentile, failure, and confidence-interval results.
9. Langfuse stores the dataset run and provides the comparison view.
10. CI queries the completed run and applies version-controlled release gates.

### 6.2 Evaluation environments

| Environment | Purpose | Data |
|---|---|---|
| Developer local | Fast iteration on one or a few items | Smoke subsets and synthetic fixtures |
| CI | Deterministic regression gate | Small immutable golden sets |
| Nightly | Full application quality | Full golden test sets |
| Hardware benchmark | ASR/diarization model and performance comparison | Public speech corpora |
| Staging | End-to-end deployment validation | Sanitized meeting fixtures |
| Production | Drift, reliability, and sampled semantic monitoring | Redacted and access-controlled live traces |

Model dependencies may remain in separate `uv` environments or native binaries. Each supported host runs a Langfuse experiment directly for the model available on that host. The evaluation framework compares the resulting runs; the project must not recreate a central subprocess scheduler.

### 6.3 Isolation

Application-level experiments must use:

- A dedicated evaluation Postgres database.
- A dedicated evaluation MinIO bucket or prefix.
- A dedicated Redis namespace.
- A non-production Langfuse environment value.
- Stable fixture identifiers.
- Cleanup by run ID.

No experiment may read from or write to production application tables, buckets, queues, or chat sessions.

## 7. Standard experiment metadata

Every experiment run must record:

| Field | Requirement |
|---|---|
| Suite name and version | Required |
| Dataset name and immutable version | Required |
| Dataset content checksum | Required |
| Git commit SHA | Required |
| Dirty-worktree flag | Required |
| Application environment | Required |
| Model provider and model ID | Required for model-backed suites |
| Embedding model ID | Required for retrieval, similarity, and dedup suites |
| Prompt name and prompt version | Required for graph, metadata, chat, and judges |
| Judge model and rubric version | Required for judge scores |
| DeepEval version and metric configuration | Required for every DeepEval score |
| jiwer version and text-normalization policy | Required for ASR suites |
| pyannote.metrics version, collar, and overlap policy | Required for diarization suites |
| Retrieval configuration | Required for RAG and related-meeting suites |
| Decoding configuration | Required for ASR suites |
| Hardware profile | Required for performance comparisons |
| Dependency lock checksum | Required |
| Random seed | Required when applicable |
| Concurrency | Required |
| Run purpose | One of local, PR, nightly, release, benchmark, or online-backfill |

Hardware metadata must include OS, architecture, CPU, total RAM, accelerator model, accelerator memory, relevant driver/runtime versions, and whether the model was cold or warm.

## 8. Dataset model and governance

### 8.1 Versioning

Langfuse experiments currently operate on the latest contents of a named dataset. To guarantee reproducibility, dataset names must be immutable and versioned.

Naming convention:

`tryniq/<suite>/<major>.<minor>.<patch>/<split>`

Examples:

- `tryniq/rag-meeting/1.0.0/test`
- `tryniq/graph-extraction/1.2.0/test`
- `tryniq/asr-final/1.0.0/smoke`

Published datasets must never be edited in place. Corrections create a new patch version. Added compatible items create a minor version. Contract or label-policy changes create a major version.

### 8.2 Dataset item envelope

Every item has four logical sections:

| Section | Contents |
|---|---|
| Input | The exact request or fixture needed to execute the production boundary |
| Expected output | Human-approved answer, labels, IDs, spans, graph objects, or reference transcript |
| Metadata | Stable item ID, source, split, license, tags, difficulty, language, and annotation provenance |
| Attachments/references | Object-store URI or logical dataset URI for large audio and related assets |

Secrets, local absolute paths, expiring signed URLs, and production credentials are forbidden in dataset items.

### 8.3 Splits

Each suite must define:

- **Smoke:** 5–20 representative cases; fast enough for local and PR execution.
- **Development:** visible cases for prompt and pipeline iteration.
- **Test:** labels available to the evaluation system but not used during development.
- **Holdout:** release-only cases with access limited to the evaluation owner.
- **Adversarial:** noisy, ambiguous, empty, overlapping, long-context, and failure-inducing cases.

Items from one meeting must not be split across development and test sets. This prevents transcript, speaker, and topic leakage.

### 8.4 Annotation requirements

- Every golden item has an annotator identity or source annotation reference.
- Graph and RAG test labels receive a second review.
- Disagreements are retained and resolved according to a documented adjudication rule.
- Judge calibration sets contain human scores from at least two reviewers.
- Automatically generated QA or summaries are not release-gating gold until human-reviewed.
- Dataset metadata identifies whether a label is human, imported, synthetic, model-generated, or production-derived.
- Personally identifiable content is removed or pseudonymized before upload to Langfuse.

## 9. Evaluation suites

### 9.1 Final ASR

**Purpose:** Measure the transcript quality and processing performance of the final transcription path.

**Input contract:** Audio asset, language, optional vocabulary/context, and decoding profile.

**Expected output:** Reference transcript and, when present, timed reference segments.

**Required scores:**

| Score | Definition |
|---|---|
| `wer` | Word error rate using the locked normalization policy |
| `mer` | Match error rate |
| `wil` | Word information lost |
| `word_accuracy` | `max(0, 1 - WER)`; reported for readability but never used instead of WER |
| `substitution_rate` | Substitutions divided by reference words |
| `deletion_rate` | Deletions divided by reference words |
| `insertion_rate` | Insertions divided by reference words |
| `entity_wer` | WER restricted to annotated names, products, numbers, and domain entities |
| `timestamp_mae_ms` | Mean absolute timestamp error where word timing truth exists |
| `rtf` | Wall time divided by audio duration |
| `x_realtime` | Audio duration divided by wall time |
| `peak_memory_mb` | Peak process memory with platform limitations documented |
| `failure_rate` | Failed items divided by attempted items |

Report micro WER over the full word corpus and macro WER across recordings. Include p50, p90, and p95 per-recording WER.

**Hard gates inherited from the PRD:**

- Final ASR WER on clean English is below 5%.
- A 30-minute meeting completes within the product’s documented CPU/GPU time budget.
- No unexpected item failures in the release suite.

### 9.2 Live ASR

**Purpose:** Evaluate streaming transcript quality, responsiveness, stability, and final commitment.

**Additional required scores:**

| Score | Definition |
|---|---|
| `first_partial_latency_ms` | Speech availability to first non-empty partial |
| `final_commit_latency_ms` | End of spoken segment to committed final |
| `revision_rate` | Changed tokens across consecutive partial hypotheses |
| `stability` | Stable prefix retained across partial updates |
| `finalization_accuracy` | Proportion of committed segments that match the final emitted hypothesis |
| `drop_rate` | Audio frames or segments dropped divided by frames or segments sent |
| `concurrent_stream_success` | Successful streams divided by streams opened under load |

**Hard gates inherited from the PRD:**

- Live ASR WER on clean English is below 12%.
- End-to-end speech-to-UI latency is below 3 seconds at p95 in the end-to-end suite.

Live runs must include real-time pacing. Fast offline playback may be used for quality debugging but cannot satisfy latency gates.

### 9.3 Uploaded-recording diarization

**Purpose:** Evaluate the diarization fallback used for mixed uploaded recordings.

**Required scores:**

| Score | Definition |
|---|---|
| `der` | Diarization error rate with overlap |
| `der_no_overlap` | DER with overlap excluded |
| `missed_speech_rate` | Missed reference speech component |
| `false_alarm_rate` | Non-speech labeled as speech component |
| `speaker_confusion_rate` | Speech assigned to the wrong speaker component |
| `jer` | Jaccard error rate |
| `speaker_count_accuracy` | Exact predicted speaker-count matches divided by meetings |
| `speaker_count_mae` | Mean absolute speaker-count error |
| `speaker_turn_precision` | Correct matched turns divided by predicted turns |
| `speaker_turn_recall` | Correct matched turns divided by reference turns |
| `speaker_turn_f1` | Harmonic mean of speaker-turn precision and recall |
| `rtf` | Wall time divided by audio duration |
| `failure_rate` | Failed meetings divided by attempted meetings |

All results must state collar size and whether overlap is included. A DER number without these parameters is invalid.

### 9.4 Graph extraction

**Purpose:** Measure the structured graph builder’s ability to extract correct nodes, fields, statuses, and edges while preserving grounding.

**Input contract:** Ordered utterances with stable IDs, timestamps, participant IDs, and any pre-existing graph context supplied in production.

**Expected output:** Canonical typed nodes, fields, lifecycle statuses, edges, and one or more source utterance IDs.

Predicted and expected text nodes are matched one-to-one within the same node type. Matching uses exact normalized text first, then a locked semantic similarity model and threshold. Maximum-weight bipartite matching must be used so one prediction cannot satisfy multiple labels.

**Required scores:**

| Score | Definition |
|---|---|
| `node_precision_<type>` | Matched predicted nodes divided by predicted nodes for each type |
| `node_recall_<type>` | Matched expected nodes divided by expected nodes for each type |
| `node_f1_<type>` | Harmonic mean for each type |
| `node_macro_f1` | Macro mean across Decision, ActionItem, OpenQuestion, and Topic |
| `edge_precision_<type>` | Correct typed edges divided by predicted typed edges |
| `edge_recall_<type>` | Correct typed edges divided by expected typed edges |
| `source_precision` | Valid and correct source links divided by predicted source links |
| `source_recall` | Expected grounding links recovered divided by expected links |
| `grounding_validity` | Grounded nodes whose source IDs exist in the input divided by grounded nodes |
| `owner_precision` | Explicitly supported owners divided by predicted owners |
| `owner_recall` | Expected explicit owners recovered divided by expected owners |
| `due_date_accuracy` | Exact normalized due-date matches divided by labeled due dates |
| `status_accuracy` | Correct provisional/confirmed/superseded labels divided by labeled nodes |
| `schema_validity` | Structurally valid responses divided by responses |
| `duplicate_rate` | Semantically duplicate persisted nodes divided by persisted nodes |
| `unsupported_node_rate` | Predicted nodes without sufficient transcript support divided by predicted nodes |

**Hard gates:**

- Decision precision is at least 70%.
- Decision recall is at least 70%.
- `grounding_validity` is 100%.
- Every Decision, ActionItem, and OpenQuestion has at least one valid `SOURCE` edge.
- Owner precision is 100%; an omitted owner is preferable to a hallucinated owner.
- Schema validity is 100% after the production retry policy.
- A failed window does not partially mutate the graph.

### 9.5 Post-meeting metadata

**Purpose:** Evaluate final summary, topics, decisions, action items, open questions, references, and related-meeting projections.

Use the same typed extraction metrics as graph extraction where fields overlap.

**Additional scores:**

| Score | Definition |
|---|---|
| `summary_factuality` | Human-calibrated DeepEval score for claims supported by source utterances |
| `summary_coverage` | Proportion of reference key facts present |
| `summary_relevance` | DeepEval score for focus on important meeting content |
| `summary_conciseness` | Compliance with the production 5–25 word contract |
| `reference_validity` | References resolving to a supplied utterance divided by references |
| `retry_rate` | Items requiring a second model call divided by items |
| `empty_result_accuracy` | Correctly empty extraction on no-signal meetings |

Summary semantic scores must use DeepEval’s maintained summarization metric where its contract applies, or a versioned G-Eval/DAG rubric where project-specific criteria are required. The evaluator must receive the source transcript and human reference facts, not only a reference summary.

### 9.6 RAG retrieval

**Purpose:** Evaluate the retriever separately from answer generation.

Run separate slices for:

- Meeting-scoped chat.
- Cross-meeting chat.
- Utterance retrieval.
- Graph-node retrieval.
- Person-name boost behavior.
- Answerable and unanswerable queries.

**Expected output:** Relevant utterance IDs, optional graded relevance, relevant graph-node IDs, and answerability.

**Required deterministic scores:**

| Score | Definition |
|---|---|
| `precision_at_k` | Relevant retrieved items divided by the first k results |
| `recall_at_k` | Relevant retrieved items divided by all relevant items |
| `hit_rate_at_k` | Queries with at least one relevant result in the first k |
| `mrr` | Mean reciprocal rank of the first relevant result |
| `map_at_k` | Mean average precision through k |
| `ndcg_at_k` | Normalized discounted cumulative gain for graded relevance |
| `meeting_filter_accuracy` | Results respecting the requested scope divided by results |
| `retrieval_latency_ms` | Query embedding plus database retrieval latency |
| `context_token_count` | Tokens passed from retrieval into generation |

Report k at 1, 5, and the configured production limit. Cross-meeting utterance retrieval must also report k at 8 and 30 while those values remain product configurations.

**Required DeepEval scores:**

- Contextual precision.
- Contextual recall.
- Contextual relevancy.

The primary initial release targets are Recall@configured-k of at least 0.80, Precision@configured-k of at least 0.60, and scope-filter accuracy of 100%. These targets become final only after the first human-verified baseline establishes that dataset ambiguity is below 5%.

### 9.7 RAG answer generation and citations

**Purpose:** Evaluate the complete chat answer after retrieval.

**Required scores:**

| Score | Definition |
|---|---|
| `answer_correctness` | Human-calibrated DeepEval G-Eval/DAG score against reference facts |
| `faithfulness` | Claims supported by the retrieved context |
| `response_relevancy` | Directness and relevance to the question |
| `citation_precision` | Citations that support their associated claim divided by citations |
| `citation_recall` | Supported factual claims carrying a citation divided by supported factual claims |
| `citation_id_validity` | Citations resolving to retrieved utterances divided by citations |
| `citation_timestamp_accuracy` | Citations resolving to the correct source time span |
| `answerability_accuracy` | Correct answer-versus-abstain classification |
| `abstention_recall` | Unanswerable questions correctly declined divided by unanswerable questions |
| `unsupported_claim_rate` | Unsupported factual claims divided by factual claims |
| `time_to_first_token_ms` | Request start to first streamed answer token |
| `answer_latency_ms` | Request start to completed answer |

Use DeepEval Faithfulness and Answer Relevancy metrics where their test-case contracts match the dataset. Use a versioned DeepEval G-Eval or DAG metric for answer correctness and unsupported-claim assessment after human calibration. Keep citation metrics deterministic and project-specific because Tryniq citations resolve to stable utterance IDs and timestamps.

**Hard gates:**

- Citation ID validity is 100%.
- Citation precision is at least 95%.
- Citation recall is at least 90%.
- Unsupported claim rate is at most 5%.
- Abstention recall is at least 90%.
- The system does not cite graph nodes as user-facing evidence.

### 9.8 Embeddings, deduplication, and related meetings

**Purpose:** Validate similarity-based decisions and their configured thresholds.

Create human-labeled positive and negative pairs for:

- Duplicate graph nodes of the same type.
- Similar but distinct graph nodes.
- Same topic across meetings.
- Generic topics that must not be linked.
- Related and unrelated meeting summaries.
- Same and different speakers when speaker memory is implemented.

**Required scores:**

| Score | Definition |
|---|---|
| `pair_accuracy` | Correct similar/dissimilar classifications divided by labeled pairs |
| `pair_precision` | True positive similarity matches divided by predicted matches |
| `pair_recall` | True positive matches divided by expected matches |
| `pair_f1` | Harmonic mean of pair precision and recall |
| `roc_auc` | Threshold-independent receiver operating characteristic area |
| `pr_auc` | Threshold-independent precision-recall area |
| `false_positive_rate` | Incorrect matches divided by actual negatives |
| `false_negative_rate` | Missed matches divided by actual positives |
| `precision_at_5` | Relevant related meetings among the top five |
| `recall_at_5` | Relevant related meetings recovered among the top five |
| `ndcg_at_5` | Graded ranking quality among the top five |

Threshold selection must be based on the development split. Report results once on the test split. Never tune the graph dedup threshold, topic distance, or related-meeting threshold on the test set.

### 9.9 AI inference reliability and efficiency

**Purpose:** Track operational behavior for every model-backed feature.

The following scores and metrics apply to graph extraction, metadata, chat, and embeddings:

| Metric | Requirement |
|---|---|
| Request success rate | By feature, model, provider, and application version |
| Empty response rate | By feature |
| Schema validity | Structured generation only |
| First-attempt validity | Structured generation only |
| Retry rate | By failure category |
| Timeout rate | By feature |
| Rate-limit rate | By provider/model |
| p50/p95/p99 latency | End-to-end and model-call observations |
| Time to first token | Streaming chat |
| Input/output/total tokens | Per request and aggregate |
| Cost | Per request, successful item, meeting, and feature |
| Embedding batch throughput | Texts per second |
| Tokens per correct answer | RAG efficiency metric |
| Cost per correct answer | RAG efficiency metric |
| Cost per valid graph window | Graph efficiency metric |

Quality and cost must be compared together. A cheaper run is not an improvement if it fails a quality gate.

### 9.10 End-to-end meeting intelligence

**Purpose:** Detect integration failures that component suites cannot see.

Each end-to-end fixture includes per-speaker audio or a mixed uploaded recording, participant identities, a meeting script/reference transcript, expected decisions, actions, questions, topics, and RAG questions.

The experiment executes:

1. Ingest or upload.
2. Live transcription when applicable.
3. Final transcription.
4. Graph extraction and persistence.
5. Metadata reconciliation.
6. Embedding generation.
7. Related-meeting ranking where fixtures include meeting history.
8. Chat retrieval and answer generation.

Required end-to-end scores include:

- Pipeline completion rate.
- Speech-to-UI p95 latency.
- Final transcript WER.
- Speaker attribution accuracy.
- Decision and action-item precision/recall/F1.
- Grounding validity.
- Citation precision and recall.
- RAG answer correctness and faithfulness.
- Total meeting processing time.
- Total AI cost per meeting.
- Idempotency: rerunning finalization produces no duplicate durable records.

## 10. Metric aggregation and statistics

Every run must publish:

- Sample count, completed count, failed count, and skipped count.
- Micro average where individual events or words should carry equal weight.
- Macro average where meetings or queries should carry equal weight.
- Median, p90, and p95 for per-item quality and latency.
- 95% bootstrap confidence intervals for primary quality metrics.
- Results by required slice.

Required slices include:

- Dataset source.
- Clean versus noisy audio.
- Single versus multiple speakers.
- Overlap versus no overlap.
- Short, medium, and long meetings.
- Meeting-scoped versus cross-meeting chat.
- Answerable versus unanswerable questions.
- Query type: entity, topic, detail, decision, action, owner, and temporal.
- Model and prompt version.
- Hardware profile.

A run must be marked inconclusive if the confidence interval is too wide to establish the configured gate or regression limit.

## 11. Judge governance

### 11.1 Judge configuration

Each DeepEval LLM-backed metric or project-specific judge must have:

- A stable evaluator name.
- A versioned DeepEval metric configuration or G-Eval/DAG rubric stored in Git.
- A pinned judge model.
- Deterministic settings where supported.
- A defined numeric, boolean, or categorical output.
- Required score reasoning.
- Examples of passing, partial, failing, and ambiguous cases.
- An explicit instruction to use only supplied evidence.
- A thin adapter that persists its score, success status, and reason to the matching Langfuse experiment item or observation.

The model under test must not judge its own output for release qualification.

### 11.2 Calibration

Before a judge score becomes release-gating:

1. At least 50 representative outputs are independently labeled by two humans.
2. Human disagreements are adjudicated.
3. Judge-versus-human agreement is reported.
4. Pass/fail agreement must reach at least 85%.
5. False-pass rate must be at most 5% for grounding and factuality rubrics.
6. Calibration is repeated after a judge model or rubric change.

Until calibrated, judge metrics are informational.

## 12. CI, scheduled runs, and release policy

### 12.1 Pull requests

Run:

- Dataset and evaluator contract validation.
- DeepEval adapter and deterministic scorer tests.
- Graph extraction smoke set.
- RAG retrieval smoke set.
- RAG citation post-processing smoke set.
- Final ASR smoke set only when relevant speech code changes.

PR checks should complete in 15 minutes or less. Expensive DeepEval metrics may be omitted from unrelated PRs. Official PR results still belong to a Langfuse experiment run; standalone DeepEval test output is not an official benchmark.

### 12.2 Nightly

Run:

- Full graph and metadata test sets.
- Full meeting and cross-meeting RAG test sets.
- DeepEval LLM-backed metric scores.
- Final ASR public test subsets.
- AI reliability and cost aggregation.
- Regression comparison against the approved baseline.

### 12.3 Weekly or hardware-triggered

Run:

- Full public ASR corpora.
- Live ASR real-time pacing and concurrency.
- Full diarization corpora.
- Candidate model comparisons on the declared Mac and CUDA hardware profiles.

### 12.4 Release qualification

A release is blocked when:

- Any hard invariant fails.
- Any PRD threshold fails.
- Failure rate exceeds the suite threshold.
- A primary quality metric regresses by more than 3% relative without an approved exception.
- p95 latency regresses by more than 10% without an approved exception.
- Cost per successful item regresses by more than 15% without a documented quality gain.
- The dataset, prompt, model, application revision, or judge version is missing.
- The run is statistically inconclusive.

Approved exceptions must link to the Langfuse run, identify the failing slices, name an owner, and have an expiry date.

## 13. Online monitoring

### 13.1 Trace structure

Use stable trace and observation names:

- `meeting.finalize`
- `asr.final`
- `graph.extract`
- `graph.persist`
- `metadata.extract`
- `embedding.generate`
- `rag.retrieve.utterances`
- `rag.retrieve.graph`
- `chat.answer`
- `related_meetings.rank`

Each trace must include application version, environment, feature, model, prompt version, meeting scope, retrieval configuration, and retry count.

### 13.2 Sampling

- Deterministic validity, error, latency, token, and cost metrics: 100%.
- DeepEval RAG and metadata semantic scoring: begin at 5% of eligible staging traffic and at most 1% of eligible production traffic.
- Human review: stratified sample of low scores, disagreements, high-cost traces, and novel queries.

Sampling rates are configurable and must have monthly cost caps.

DeepEval must not instrument production requests directly. A separate evaluation worker selects eligible Langfuse traces, constructs ephemeral DeepEval test cases, computes metrics, and writes the resulting scores and reasons back to the original Langfuse traces or observations.

### 13.3 Privacy

- Keep Langfuse self-hosted for evaluation of real meetings.
- Do not send meeting content to a judge provider not already approved for application inference.
- Redact email addresses, phone numbers, access tokens, and other secrets before dataset promotion.
- Restrict dataset and trace access by role.
- Define retention separately for raw production traces and curated golden datasets.
- Record participant consent requirements before using production audio or transcripts for evaluation.

## 14. Public datasets and download sources

### 14.1 Existing datasets to retain

| Dataset | Suites | License/access | Source |
|---|---|---|---|
| LibriSpeech test-clean | Final/live ASR | CC BY 4.0 | [Dataset page](https://www.openslr.org/12) · [Direct test-clean archive](https://www.openslr.org/resources/12/test-clean.tar.gz) |
| LibriSpeech test-other | Final/live ASR | CC BY 4.0 | [Dataset page](https://www.openslr.org/12) · [Direct test-other archive](https://www.openslr.org/resources/12/test-other.tar.gz) |
| AMI Meeting Corpus | ASR, diarization, graph, metadata | Free registration; Creative Commons terms vary by release | [Official corpus](https://groups.inf.ed.ac.uk/ami/corpus/) · [Annotations](https://groups.inf.ed.ac.uk/ami/corpus/annotation.shtml) · [Hugging Face mirror](https://huggingface.co/datasets/edinburghcstr/ami) |
| Earnings-21 | Final/live ASR, long-form robustness | CC BY 4.0 | [Source repository](https://github.com/revdotcom/speech-datasets/tree/main/earnings21) · [Repository ZIP](https://github.com/revdotcom/speech-datasets/archive/refs/heads/main.zip) |
| CHiME-6/CHiME-5 | Diarization and far-field ASR | Restricted; manual acquisition and commercial licensing may be required | [Official download instructions](https://chimechallenge.github.io/chime6/download.html) |

The existing prepared dataset cache may be reused after its manifest is converted to the new dataset contracts. Audio must remain outside Git.

### 14.2 New required datasets

| Dataset | Suites | Why required | License/access | Download |
|---|---|---|---|---|
| QMSum | RAG retrieval, answer generation, topics, summarization | 1,808 human-annotated query/summary pairs over 232 meetings; specific queries include relevant transcript spans | MIT | [Repository](https://github.com/Yale-LILY/QMSum) · [Direct ZIP](https://github.com/Yale-LILY/QMSum/archive/refs/heads/main.zip) |
| Full AMI annotations | Graph extraction, metadata, decision/action extraction | Human summaries contain `DECISIONS`, `PROBLEMS/ISSUES`, and `ACTIONS`; extractive summaries link facts to dialogue acts | AMI corpus terms | [Annotation catalog and downloads](https://groups.inf.ed.ac.uk/ami/corpus/annotation.shtml) |

### 14.3 Recommended optional dataset

| Dataset | Suites | License/access | Source |
|---|---|---|---|
| NOTSOFAR-1 | Modern meeting ASR and diarization stress testing | CC BY 4.0; very large, so download selected recorded-meeting subsets only | [Hugging Face dataset and download instructions](https://huggingface.co/datasets/microsoft/NOTSOFAR) · [Challenge repository](https://github.com/microsoft/NOTSOFAR1-Challenge) |

### 14.4 Dataset exclusions

- Do not use training splits as release test sets.
- Do not redistribute CHiME audio.
- Do not make automatically generated labels release-gating without human review.
- NSF-QA is not part of the default plan because its answers are model-generated and its CC BY-NC 4.0 and upstream generated-content terms may conflict with commercial use.
- Generic BEIR corpora may be used to compare embedding models, but they do not replace meeting-domain golden retrieval data.

## 15. Initial golden-dataset plan

### 15.1 Graph and metadata gold

Build the first version from:

- AMI scenario and non-scenario meetings with abstractive and extractive summaries.
- Existing scripted Tryniq demo meetings.
- Synthetic no-signal, hypothetical, ambiguous-owner, duplicate-window, contradiction, and malformed-output cases.

Minimum version 1.0 test size:

- 30 meetings or transcript windows.
- At least 50 decisions.
- At least 50 action items.
- At least 30 open questions.
- At least 50 topics.
- At least 20 explicit owners and 20 intentionally ownerless items.
- At least 20 duplicate or near-duplicate node pairs.

### 15.2 RAG gold

Build the first version from QMSum test meetings and Tryniq scripted fixtures.

Minimum version 1.0 test size:

- 150 answerable queries.
- 50 unanswerable queries.
- At least 30 queries each for entity, detail, topic, decision/action, and temporal/owner slices.
- Stable relevant utterance or span labels.
- Reference facts rather than only free-form reference answers.
- At least 25 cross-meeting queries spanning a fixture corpus of ten or more meetings.

### 15.3 Similarity and related-meeting gold

Minimum version 1.0 test size:

- 100 positive duplicate/similar pairs.
- 100 hard negative pairs.
- 50 related-meeting queries with graded relevance.
- Dedicated hard negatives for generic topics such as “deployment,” “timeline,” and “budget.”

## 16. Proposed replacement module boundaries

The replacement `evals/` package should be thin and organized by framework concepts:

| Area | Responsibility |
|---|---|
| Suite definitions | Select a Langfuse dataset, invoke one production boundary, and attach evaluators |
| Task adapters | Convert a dataset item into a production service call |
| DeepEval adapters | Convert production LLM/RAG outputs into ephemeral DeepEval test cases and convert metric results into Langfuse scores |
| Speech evaluators | Call jiwer or pyannote.metrics and convert their results into Langfuse scores |
| Deterministic evaluators | Apply maintained IR/statistical functions or enforce Tryniq invariants |
| Dataset importers | Normalize public annotations and synchronize immutable Langfuse datasets |
| Rubrics | Versioned DeepEval G-Eval/DAG semantic judging criteria |
| Gates | Version-controlled thresholds and regression policies |
| Fixtures | Small, safe, deterministic test assets |
| Documentation | Setup, dataset licenses, annotation guide, and operator runbook |

Shared DTOs and business logic belong in production modules, not in `evals/`. If production code cannot be called without copying logic, refactor the production boundary first.

DeepEval test cases are ephemeral adapter objects. They must not be serialized as a second canonical dataset format. DeepEval metric results must be persisted only through Langfuse scores.

## 17. Migration plan

### Phase 1: Foundation

1. Confirm the self-hosted Langfuse version supports the required SDK experiment features.
2. Pin compatible Langfuse, DeepEval, jiwer, and pyannote.metrics versions.
3. Define evaluation environment credentials and isolated application infrastructure.
4. Define dataset naming, score naming, trace naming, and experiment metadata conventions.
5. Implement and contract-test the thin metric-to-Langfuse adapters.
6. Create one minimal Langfuse experiment using at least one DeepEval metric.
7. Record an immutable baseline run.

**Exit criteria:** A developer can open one dataset run in Langfuse, inspect every item and trace, see DeepEval score reasons, compare two runs, and retrieve aggregate scores without reading a local result file or opening Confident AI.

### Phase 2: Migrate speech suites

1. Import the existing LibriSpeech, AMI, Earnings-21, and CHiME manifests.
2. Implement framework-native final ASR, live ASR, and diarization experiments.
3. Use jiwer and pyannote.metrics rather than current metric implementations.
4. Validate results against a sample of historical runs.
5. Preserve the existing model card as a historical document linked to the replacement baseline.

**Exit criteria:** New and old scores agree within documented normalization and timing tolerances, and no custom runner or report collector is required.

### Phase 3: Add graph and metadata suites

1. Import AMI annotations.
2. Create the human-reviewed graph/metadata gold set.
3. Implement typed node, edge, grounding, owner, status, summary, retry, and mutation-safety evaluators.
4. Calibrate semantic node matching and DeepEval summary metrics.

**Exit criteria:** PRD decision precision/recall and grounding requirements are enforced by release gates.

### Phase 4: Add RAG, embeddings, and related-meeting suites

1. Import QMSum.
2. Create meeting and cross-meeting fixture corpora.
3. Evaluate retrieval independently from generation.
4. Add DeepEval contextual precision, contextual recall, contextual relevancy, faithfulness, answer relevancy, and calibrated G-Eval/DAG metrics.
5. Add similarity threshold and related-meeting ranking experiments.
6. Calibrate DeepEval answer correctness and faithfulness metrics.

**Exit criteria:** A run identifies whether a regression belongs to retrieval, context construction, generation, or citation post-processing.

### Phase 5: End-to-end and continuous evaluation

1. Add end-to-end meeting fixtures.
2. Complete non-LLM spans for retrieval, persistence, and ranking.
3. Configure nightly and release workflows.
4. Configure sampled online evaluators and dashboards.
5. Define production-trace review and golden-dataset promotion workflow.

**Exit criteria:** Quality, reliability, latency, tokens, and cost are visible over time by feature, model, prompt, and application version.

### Phase 6: Remove the legacy harness

After parity and acceptance:

- Delete the custom CLI, registry, runner, diarization runner, report generator, result types, and custom metric implementations.
- Delete the sentinel adapter protocol.
- Remove unused evaluation-only model adapters and environments.
- Keep only model environments still required to execute a supported production or benchmark model.
- Replace `RESULTS.md` generation with links to immutable Langfuse runs and an approved static release summary.
- Update `README.md`, `DATASETS.md`, `RUNBOOK.md`, and `MODEL_CARD.md` to describe the framework-native workflow.
- Remove legacy dependencies that are no longer used.

Do not delete historical result artifacts until the replacement baseline is approved and exported.

## 18. Acceptance criteria for the migration

The migration is complete when all of the following are true:

1. No standalone experiment orchestrator, result store, result collector, or report aggregation engine is implemented outside Langfuse; aggregate score calculations run as Langfuse run-level evaluators.
2. No standard metric listed in this specification is reimplemented by Tryniq.
3. DeepEval is used only as the LLM/RAG metric engine; Langfuse remains the sole owner of canonical datasets, official runs, traces, and scores.
4. No official result or canonical dataset depends on Confident AI.
5. Speech, graph, metadata, RAG retrieval, RAG generation, citations, embeddings, related meetings, and AI inference each have a named suite.
6. Every run is reproducible from an immutable dataset version and recorded metric configuration.
7. Every item has a linked trace and all unexpected failures affect the run score.
8. PRD thresholds and grounding invariants are automated release gates.
9. Developers can compare model, prompt, retrieval, and application versions in Langfuse.
10. CI runs the smoke suites and links directly to the experiment.
11. Nightly runs publish quality, reliability, latency, token, and cost trends.
12. Public dataset sources, licenses, and attribution are documented.
13. Production-derived data has a documented consent, redaction, review, access, and retention process.
14. The legacy runner, registry, report collector, and custom metric implementations are removed.
15. The static model card links to an immutable framework run that supports every published number.
16. A new evaluation suite can be added without editing a central registry or result aggregator.

## 19. Definition of done for each new suite

A suite is not done until it has:

- A named product risk or decision it informs.
- An immutable dataset and documented source.
- Input, expected-output, and metadata contracts.
- At least one deterministic or standard metric.
- Defined slices.
- Baseline results.
- Thresholds or an explicit informational-only status.
- Failure handling.
- Trace coverage.
- A documented runtime and cost budget.
- A named owner.
- A CI, nightly, release, or online execution cadence.
- A Langfuse run link in the suite documentation.

## 20. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Langfuse dataset mutation breaks reproducibility | Use immutable versioned dataset names and content checksums |
| Langfuse and DeepEval become competing frameworks | Enforce the ownership table: Langfuse owns lifecycle and storage; DeepEval calculates LLM/RAG scores only |
| Results leak into a second SaaS | Do not configure Confident AI for official runs; persist DeepEval results exclusively as Langfuse scores |
| Duplicate tracing increases runtime complexity | Keep Langfuse as the only production tracer; run DeepEval only in offline/online evaluation workers |
| DeepEval LLM-backed metrics disagree with humans | Calibrate on double-reviewed labels and gate metric, rubric, or judge-model changes |
| Evaluation code repeats production logic | Require calls through production service boundaries |
| Public datasets do not match Tryniq meetings | Combine public corpora with reviewed project-specific fixtures and production-derived edge cases |
| Long meeting experiments are expensive | Use smoke/development/test tiers, caching only where semantically safe, and explicit run budgets |
| Failures bias scores upward | Score unexpected failures as zero and always report failure rate |
| Multi-host speech results are incomparable | Require hardware profiles and compare quality separately from host-dependent performance |
| Restricted audio leaks into Git or Langfuse | Store only logical/object-store references and enforce license-aware import rules |
| Production data creates privacy exposure | Self-host, redact, restrict, retain minimally, and require consent |
| Framework upgrade changes results | Pin SDK and metric versions; record lock checksum and re-baseline deliberately |

## 21. Ownership

Recommended ownership:

| Area | Owner |
|---|---|
| Langfuse deployment, retention, and access | Platform |
| Langfuse/DeepEval adapter contract and CI | AI platform/backend |
| DeepEval metric selection and judge calibration | Product AI + QA |
| Speech datasets and scorers | Speech/ASR |
| Graph and metadata gold labels | Product AI + domain reviewer |
| RAG and citation gold labels | Product AI + backend |
| Release gate approval | Engineering lead |
| Dataset licenses and production consent | Project owner |

The engineering lead owns the final baseline and any temporary exception to a release gate.
