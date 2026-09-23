# Design: runtime-traceability

## Overview

Implement durable end-to-end runtime traceability, accurate outcomes, configuration history, provider measurements, and portable exports

## Approach

Implement the work in seven reviewable slices: shared identity/event contracts and the CLI journal; lifecycle instrumentation; accurate tool outcomes and recovery; configuration/prompt/policy history; provider metadata/timing/usage; cost aggregation and offline export; then failure-path verification and documentation.

Provider-facing APIs accept optional caller-supplied trace context and typed observers without depending on agent internals. The agent propagates those identities through requests, summaries, tools, MCP, and recovery. The CLI supplies the local storage adapter and owns sequence allocation, redaction, durability, retention, inspection, and export.

The event envelope is versioned and contains a unique event ID, per-run sequence, wall-clock timestamp, monotonic duration data where applicable, component, event type, causal identity fields, and a typed payload. Legacy diagnostics and visibility callbacks are retained through adapters during migration.

The journal is append-only JSONL with serialized writes. Completion barriers use an explicit durable-write policy at operation boundaries. Capture failures are reported independently and never replace an already-observed operation result or cause a side effect to be retried.

Tool transport status remains compatible while structured outcome metadata records exit code, signal, deadline, cancellation, confirmed termination, known side effects, and uncertainty. Each tool completion is persisted before another call in the batch begins. Recovery appends unknown/interrupted or reconciliation events rather than rewriting history.

Configuration and prompt state use immutable revisions with origin and redaction metadata. Requests and tool dispatches reference the exact revisions they used. Provider attempts record actual mutations, upstream metadata, normalized and original termination, local timing, and usage provenance.

Offline inspection reads only recorded data. Export uses relative artifact paths, a versioned manifest, hashes, explicit missing-data entries, and completeness warnings. Full payload capture is opt-in and protected; standard bundles exclude credentials and opaque continuation state.

## Cross-repository changes

| Repository | Change |
|------------|--------|
| propio-providers | Add trace context and observer contracts, request/attempt events, retry mutations, adapter metadata, timings, stop reasons, structured errors, and normalized usage with availability/provenance. |
| propio-agent | Add run/operation propagation, tool and MCP outcomes, incremental result durability, configuration/prompt/policy revisions, local journal and recovery, cost aggregation, inspection, and portable export. |

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Event additions break exhaustive consumers | Use additive optional contracts, version unions, and compatibility adapters with compile-time consumer tests. |
| Tracing changes runtime behavior or retries side effects | Keep observers injected and headless; isolate capture failures and persist observed outcomes before subsequent work. |
| Secret or opaque state leakage | Centralize capture policy and redaction; test configuration, headers, arguments, and error bodies with synthetic secrets. |
| Journal corruption or misleading completeness | Serialize writes, use completion barriers, tolerate a truncated tail, and emit explicit degraded/incomplete states. |
| Usage or cost inflation | Retain provenance and cumulative/delta semantics, deduplicate terminal reports, and represent missing data as unavailable rather than zero. |
| Excessive latency or disk growth | Avoid per-token persistence by default; benchmark representative fixtures and enforce a justified threshold. |
| Cross-repository contract skew | Land compatible provider contracts first, link local packages for agent verification, and preserve old call paths during migration. |

## Alternatives considered

- A separate telemetry service or repository was rejected because durable local evidence is the immediate requirement and reusable libraries must remain deployment-agnostic.
- Reusing only legacy diagnostics was rejected because those events omit causal identity, persistence guarantees, configuration history, and accurate outcomes.
- Treating prompt estimates as usage or missing pricing as zero was rejected because it creates false completeness.
- Replaying incomplete side effects during recovery was rejected because absence of a completion record does not prove absence of the side effect.
