# Langfuse compatibility record

Validated on 2026-07-29 using the immutable
`tryniq/synthetic-foundation/1.0.0/smoke` dataset
(`819ce3cda4d8411f29dcaa359095647eb2db5e700909f4d0fb1a83581450493f`).

| Component | Validated version |
| --- | --- |
| Python SDK | `langfuse==4.14.0` |
| Web server | `langfuse/langfuse:3@sha256:4bc041b8b47e62d06792ed863d8803ba32f612a8d4e6d539a059e5dc921345c6` |
| Worker | `langfuse/langfuse-worker:3@sha256:3f5069e58eb614d10a403646348ff80cb8451d3d7375477706ed59223becaa83` |
| Embedded metric | `deepeval==4.1.4` |

The compatibility check immutably synchronized the dataset, ran the experiment
twice, retrieved the runs through the SDK, and verified item scores plus run-level
statistics. The two comparable self-hosted run IDs are:

- `3df50354-fc14-4bf5-930a-b18f9d5f61a5`
- `1d67cda7-ac11-4a00-a901-669bd63f1816`

A third run (`597732fa-3c35-4cf3-82a2-f239186a0ee6`) verified flattened run
metadata after enforcing Langfuse's propagated-attribute size limit.

These compatibility runs are evidence for the version pins, not approved quality
baselines. Baseline IDs must only be added to `gates/suites.yaml` after engineering
review.
