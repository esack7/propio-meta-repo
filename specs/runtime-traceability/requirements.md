# Requirements: runtime-traceability

## Summary

Implement durable end-to-end runtime traceability, accurate outcomes, configuration history, provider measurements, and portable exports

## Goals

- Give every session, run, request, attempt, operation, turn, and tool call durable causal identity.
- Persist an append-only, versioned JSONL journal with explicit capture degradation and crash-recovery semantics.
- Record accurate tool outcomes independently from transport success, including uncertainty and side effects.
- Preserve each completed tool result across later cancellation, interruption, and process restart.
- Record the effective configuration, prompt plan, policy decision, tool scope, and provider request mutation used by each operation.
- Capture provider request metadata, timing, termination, and usage across all supported adapters.
- Aggregate usage and cost without treating missing data as zero.
- Provide side-effect-free local inspection and a portable, hash-verifiable run export.

## Non-goals

- A hosted telemetry service or a new repository.
- Deterministic re-execution or automatic replay of side-effecting operations.
- Capturing hidden model reasoning or every streamed token by default.
- A graphical timeline, detailed scratchpad revision tracking, or claim-level summary provenance.
- Breaking existing provider, diagnostic, terminal-rendering, tool, or session APIs where additive contracts suffice.

## Acceptance criteria

- [ ] A two-turn fixture containing tool calls, a retry, and a summary has unambiguous causal IDs and ordered durable events.
- [x] Resume preserves the session ID, creates a new linked run, handles truncated journals, and never duplicates recorded results.
- [x] Shell nonzero exit, timeout, cancellation, launch failure, remote unknown outcome, and completed side effects followed by capture failure remain distinct.
- [x] Each request and tool dispatch references the configuration, prompt, policy, and tool-scope revision actually used.
- [x] OpenRouter request mutation and xAI endpoint fallback are represented as separate, linked attempts.
- [ ] All nine adapters cover success, tool use, retry, failure, absent usage, and applicable streaming termination cases.
- [x] Usage aggregation deduplicates cumulative reports and exposes partial, unavailable, and unknown-price states.
- [x] An interrupted run can be exported and inspected offline in a fresh directory without credentials, original home paths, provider calls, or tool execution.
- [x] Standard output and exports exclude synthetic secrets while identifying omitted, redacted, missing, or pruned material.
- [x] Existing supported sessions and callers with tracing omitted continue to work, and reusable libraries perform no implicit trace-directory I/O.
- [x] Repository-required builds, tests, formatting, and pinned Fallow checks pass.
- [x] Journal overhead is measured for token-heavy and tool-heavy fixtures and checked against a documented regression threshold.

See [the acceptance review](acceptance-review.md) for evidence, limitations, and the two open criteria. Checked items reflect deterministic local evidence, not live-provider certification.

## Affected repositories

<!-- Confirmed names are listed in repos.txt -->

## Open questions

- Final CLI command names for inspection and export are intentionally left to implementation.
- Provider fields that are not exposed by the installed SDK remain explicitly unavailable and documented per adapter.
- Capture levels and durable-write frequency should be finalized using security tests and measured overhead.
