# Annotation guide

Annotators label only evidence present in the supplied meeting fixture. Record annotator
identity, review status, provenance, difficulty, and uncertainty. Never repair model
output while labeling its quality.

## Graph and metadata

- Normalize whitespace/case for exact node matching, but preserve original evidence.
- Every Decision, ActionItem, and OpenQuestion needs at least one source utterance.
- Owners are labeled only when explicitly supported.
- Due dates use normalized ISO dates when resolvable; ambiguity is retained.
- Hypothetical, contradicted, superseded, duplicate, and no-signal cases are explicit.
- A second reviewer verifies all test/holdout nodes, edges, owners, dates, and references.

## RAG

- Label utterance and graph relevance separately with stable IDs and graded relevance.
- Record scope: meeting or cross-meeting.
- Record query type: entity, topic, detail, decision, action, owner, or temporal.
- Mark answerability before writing an expected answer.
- Associate each expected factual claim with supporting utterance IDs and timestamps.
- Unanswerable questions must specify the expected abstention behavior.

## Judge calibration

Two reviewers independently score at least 50 representative outputs. Retain both raw
labels, adjudicated label, rationale, rubric version, and judge version. Semantic scores
remain informational until the agreement thresholds in `DATASETS.md` are met.

## Adjudication

Reviewers discuss disagreements using only the frozen fixture and rubric. The adjudicator
records the chosen label and why the alternatives were rejected. A rubric change creates a
new dataset major version; a corrected individual label creates a patch version.
