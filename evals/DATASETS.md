# Dataset governance and licenses

Langfuse dataset names are immutable:

```text
tryniq/<suite>/<major>.<minor>.<patch>/<split>
```

Allowed splits are smoke, development, test, holdout, and adversarial. Corrections create
a patch version, compatible additions a minor version, and contract/label-policy changes
a major version. Meetings never cross development/test boundaries.

## Envelope

Every item has validated input, expected output, metadata, and logical attachment
references. Required metadata includes stable item ID, source, split, license, annotation
provenance, and reviewer information where applicable.

Large/restricted assets remain in evaluation MinIO and are referenced as logical URIs with
SHA-256 hashes. Local paths, signed URLs, secrets, credentials, and raw production
identifiers are rejected.

## Sources

| Source | Use | License/access |
|---|---|---|
| LibriSpeech test clean/other | final and live ASR | CC BY 4.0 |
| AMI corpus + full annotations | speech, graph, metadata | AMI corpus terms |
| Earnings-21 | long-form business ASR | CC BY 4.0 |
| CHiME-6 | noisy/overlapping speech | LDC/custom, restricted |
| QMSum | meeting RAG and summarization | dataset terms; verify redistribution |
| Tryniq synthetic fixtures | contracts/adversarial behavior | MIT |

Restricted licenses are stored as logical references only and can produce a declared
license skip on a host without access.

## Synchronization

`SourceManifest` records suite/version/split, license, normalization/import policy, source
checksum, canonical content checksum, and items file. Deterministic UUIDv5 item IDs are
derived from immutable dataset name plus stable item ID.

Synchronization:

1. validates every envelope;
2. recomputes the canonical content checksum;
3. fetches an existing Langfuse dataset when present;
4. aborts on checksum or item-count mismatch;
5. otherwise creates the dataset and deterministic items exactly once.

## Review and privacy

Graph and RAG test labels require a second review. Judge calibration sets require at least
50 examples independently scored by two reviewers, adjudicated disagreements, at least
85% pass/fail agreement, and at most 5% false-pass rate for grounding/factuality.

Production-derived material requires documented consent, pseudonymization/redaction,
review, role-restricted access, and retention. Remove email addresses, phone numbers,
tokens, URLs carrying credentials, and unnecessary personal identifiers before upload.
