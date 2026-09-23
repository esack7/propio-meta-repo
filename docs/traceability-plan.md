# Propio runtime traceability priority plan

Date: 2026-09-21

Status: provider adapter matrix merged; final G3 provenance in review

Companion documents: [original findings](traceability-findings.md), [evidence-based reassessment](traceability-reassessment.md), and [acceptance review](../specs/runtime-traceability/acceptance-review.md)

## Objective

After a run ends or is interrupted, a developer should be able to reconstruct its requests, tools, outcomes, configuration changes, policy decisions, timing, and available usage from durable local records. Unknown completion, missing usage, and capture failures must remain visible.

This plan addresses the four priority gaps in the findings document. It records the intended scope; the linked acceptance review distinguishes merged behavior, candidate verification, and remaining limits. The audited repository commits and original score baseline remain recorded in the findings document.

## Ownership and boundaries

| Repository / component | Responsibility |
| --- | --- |
| propio-providers: contracts, adapters, retry machinery | Request/attempt identity propagation, upstream metadata, request mutations, usage normalization, provider timings and termination details. |
| propio-agent: agent-core | Run/turn lifecycle, causal relationships, prompt-plan links, tool dispatch/result events, recovery events. |
| propio-agent: tools, MCP, context | Execution outcomes and policy decisions, remote-call lifecycle, incremental results, artifact provenance and revision links. |
| propio-agent: CLI, sessions, configuration | Local journal, capture policy, redaction, configuration history, persistence/recovery, inspection, export and cost aggregation. |

Keep reusable APIs headless and explicitly configured. Providers must not depend on agent internals. Libraries emit typed records through injected observers and perform no implicit trace-directory discovery. The CLI owns the local storage adapter. A new telemetry service or repository is unnecessary for this scope.

## Delivery sequence

| Order | Deliverable | Gap | Dependency |
| --- | --- | --- | --- |
| 1 | Identity/event contracts and local journal | G1 | None |
| 2 | End-to-end lifecycle instrumentation | G1 | 1 |
| 3 | Accurate tool outcomes and interrupted-run recovery | G2 | 1–2 |
| 4 | Configuration, prompt, policy, and fallback history | G3 | 1–2 |
| 5 | Provider request metadata, timing, and usage across all adapters | G4 | 1–2; use mutation links from 4 |
| 6 | Cost aggregation and portable run export/inspection | G4 | 3–5 |
| 7 | Failure-path verification, documentation, and re-audit | G1–G4 | 1–6 |

Each deliverable should be a reviewable change or small set of coordinated changes. Fix the known result-loss and outcome-reporting problems before building a richer UI. Use feature worktrees for implementation through the normal specification workflow; reference clones remain investigation material.

## G1 — Connect the existing evidence

### Identity model

Define these meanings before implementing producers:

- `sessionId`: stable conversation identity, preserved on resume.
- `runId`: a new active execution segment; resuming produces a new run linked to the prior run/snapshot.
- `turnId`: reuse the existing conversation turn identity; user-entered shell operations may have a run but no conversation turn.
- `requestId`: one logical provider request, with a purpose such as `answer`, `summarize`, or `recovery`.
- `attemptId`: one actual outbound attempt; retries and endpoint fallbacks get separate identities.
- `operationId` and `parentOperationId`: causal hierarchy for requests, tools, policy checks, context work, and persistence.
- `toolCallId`: retain the provider's identifier alongside local identity; do not assume it is globally unique.

Do not create fake conversation turns for preparation failures or synthetic events. Such operations can initially be linked to the run and then associated with the actual turn when one exists.

### Event envelope and propagation

Use a versioned envelope with event ID, per-run sequence, timestamp, component, event type, identity fields, and typed payload. Use monotonic time for durations and wall-clock time for human correlation. Sequence orders observation; parent links express causality.

Add optional caller-supplied trace context and typed observers to the provider boundary without importing agent types. Propagate context through agent runtime, providers, summaries, tool execution, and MCP adapters. Direct users of reusable tools/MCP should be able to supply their own observer and identifiers.

Wrap existing diagnostics and visibility events into this model. Avoid maintaining two independent implementations of the same event. Preserve legacy diagnostic/CLI interfaces through adapters during migration. Cover events currently filtered out by CLI adaptation.

### Durable local journal

The CLI owns one append-only JSONL journal per run, with serialized writes and sequence allocation. Lifecycle metadata should be captured by default; payload capture is controlled separately. Surface permission errors, disk-full conditions, dropped records, and incomplete capture. Observability failures must not cause a completed side effect to be retried or replace its original result.

Define a flush barrier for recorded operation completions and graceful exit. Specify and test the crash-durability guarantee: ordinary buffering alone is insufficient for a claim that acknowledged completion survives process termination. Use an explicit durable-write policy at operation boundaries; do not flush every token. If recording fails, mark capture degraded and warn through an independent channel. A crash before durable completion remains an unknown outcome.

### Acceptance criteria

- A two-turn fixture with tool calls, one retry, and one summary can be joined through IDs with no ambiguous request/attempt association.
- Two sessions and two runtime instances do not collide, including repeated synthetic/provider tool-call IDs.
- Resume preserves session identity, creates a new run, and records lineage.
- Existing consumers work with tracing omitted; constructing reusable APIs causes no file I/O.
- Written JSONL parses directly, has unique event IDs and ordered sequence numbers, and reports interrupted/truncated capture.

## G2 — Make outcomes accurate and durable

### Separate operation outcome from transport status

Preserve the existing tool status contract initially, adding structured outcome metadata for command exit code, signal, deadline, cancellation, and known side effects. Update trace summaries to use this metadata. Any later change to the legacy `success` semantics requires explicit migration notes.

For shell execution, distinguish command success, nonzero exit, timeout, cancellation, and launch failure. Capture resolved working directory, effective timeout, duration, bounded stdout/stderr references, and whether bytes were discarded. Record environment key names or approved non-secret values rather than indiscriminately storing environment contents.

For write/edit, record resolved path, create/replace operation, before/after hashes and patch/artifact references where available. A later storage failure must not turn a completed file write into an apparently safe-to-retry operation.

### Preserve each completed result

Persist each tool completion before beginning the next call in a batch. Extend the context store's incremental-result behavior deliberately: subsequent prompt construction must preserve valid assistant/tool associations and order, with no duplicate results after resume. Do not merely call the current batch API repeatedly without verifying those invariants.

Keep execution evidence independent of conversational cleanup. Discarding an empty or incomplete turn must not erase records of operations already dispatched or completed. On cancellation, record requested cancellation separately from confirmed termination. MCP timeouts and uncooperative tools may have unknown remote outcomes.

Record unresolved operations during recovery as unknown/interrupted, linked to their start records. If a late result becomes observable, append a reconciliation event rather than rewriting history. Never automatically replay a side-effecting operation solely because its completion record is missing.

### Acceptance criteria

- A shell command exiting 7 is counted as a command failure while existing tool API compatibility is preserved.
- In a three-tool batch interrupted during tool two, tool one's completed result remains in the journal and recovered context; tool three was never dispatched.
- Successful write followed by artifact-storage failure retains the successful side effect and exposes the storage failure separately.
- Cancellation request and confirmed process termination are distinguishable; an unconfirmed remote outcome is never labeled successful or rolled back.
- Restart recovery handles a truncated final journal line, identifies incomplete operations, and does not duplicate already recorded results.

## G3 — Record changes that explain behavior

### Configuration and prompt revisions

Persist a redacted effective configuration revision with each value's origin: default, settings file, environment, CLI, or runtime change. Include agent/provider package versions, model selection, capabilities, limits, enabled tool schemas, mode, and relevant workspace baseline. Represent secrets by presence/source, not their values or reversible substitutes.

Emit revision-change events with cause and scope. Every request references the applied revision; every tool dispatch references its actual policy/tool-scope revision.

Record prompt-plan selection and omission reasons, source instruction hashes, skill invocation/revision, summary revision, and artifact references. Distinguish the logical prompt plan from the provider-transformed outbound payload. Capture a protected payload or a fingerprint/reference with an explicit capture level; a hash alone does not make a request reconstructable.

### Decisions and mutations

Record allowed and denied policy decisions, including rule/version, actor, reason, reviewed-argument reference, and invocation identity. Reuse the registry's reviewed argument snapshot so the record matches execution. Capture mode changes, plan-save approvals, skill-scope activation/expiration, and tool enable/disable events.

Provider retries must state changes to the actual request. Record OpenRouter's tool-removal transition and xAI endpoint attempts explicitly. Keep requested model/provider separate from actual upstream model/provider when routing metadata is available.

### Acceptance criteria

- After a model, mode, or tool-scope change, inspection identifies exactly which subsequent requests and calls used the new revision.
- Allowed, denied, cancelled-before-approval, and approval-callback-failure cases have distinct records.
- OpenRouter's final retry states that tools were removed and references the relevant attempt; xAI endpoint fallbacks have separate attempt records.
- A context-pressure retry shows what changed in prompt selection and which summary/instruction revisions were used.
- Synthetic secrets in configuration, headers, arguments, and error bodies do not appear in standard trace/export output.

## G4 — Add request measurements and a run export

### Provider metadata and timing

Extend provider-owned contracts with upstream request/response IDs where available, requested/actual model, endpoint class, original and normalized stop reason, structured errors, and usage. Record per-attempt start, first useful output, completion/failure, duration, and time waiting between attempts. Separate local timing from provider-reported metrics.

Cover all nine adapters: Anthropic, Bedrock, Ollama, OpenRouter, OpenAI, Meta, Gemini, xAI, and Cloudflare. Start with shared streaming/Responses machinery, then adapter-specific fields. Verify field mappings against the installed SDK and authoritative provider documentation during implementation. Unsupported or missing fields remain explicitly unavailable.

Summarizer calls and recovery requests use the same instrumentation with their own request purpose and causal links. SDK-owned retries should be exposed where supported; otherwise disclose the limit instead of implying that locally observed attempts include every upstream attempt.

### Usage and cost

Keep input, output, cache-read/write, and reasoning token counters distinct where supplied; document overlapping counters so totals do not double-count. Preserve provider-reported units and provenance. Distinguish cumulative stream usage from deltas, deduplicate repeated terminal reports, and retain usage from failed attempts when available.

Store a usage availability state such as reported, unavailable, or partial. Keep existing prompt estimates explicitly separate. Missing usage or pricing is not zero. Aggregate answer, summary, recovery, retry, and run totals with completeness indicators.

Inject a versioned pricing resolver at the application layer. Persist currency, rate source/effective date, applicable model/routing context, and calculation inputs. Separate provider-reported charge from locally estimated cost. Do not silently treat locally hosted inference as free or infer billing rules from a generic token count.

### Portable export and inspection

Provide a local inspection/export interface; final command names are an implementation detail. An export contains:

- A versioned manifest with run/session lineage, capture level, package versions, configuration revisions, and completeness warnings.
- The event journal and operation/attempt outcome summary.
- Captured prompt/request/response artifacts permitted by the capture policy.
- Tool results, attachment references, content hashes, and explicit missing/pruned-artifact entries.
- Workspace baseline and final diff/hash information sufficient to identify observed changes; broad shell/external side effects remain unknown unless independently observed.
- Timing, usage, and cost summaries with provenance and completeness.

Use relative artifact paths and verify hashes on import. Keep credentials and opaque provider continuation material out of standard exports. Full payload capture needs explicit opt-in and protected local storage; it should not be presented as safely shareable merely because credential fields were redacted. Record exactly which material was excluded, since a redacted bundle may only support partial reconstruction.

Inspection and recorded-response playback must perform no provider calls, shell execution, or MCP side effects. Re-execution is a separate future feature. A viewer should show observations and uncertainty, not claim to reveal hidden model reasoning or guarantee deterministic reproduction.

### Acceptance criteria

- Each adapter passes fixtures for successful text/tool use, retries, failure, absent usage, and applicable streaming/termination edge cases.
- Duplicate or cumulative usage events do not inflate totals; missing/partial usage remains visible.
- Summarization and failed/retried attempts are attributed separately from the answer request.
- A bundle exported after an interrupted run opens in a fresh directory without the original home/session paths or credentials.
- A reviewer can identify what completed, what failed, what configuration applied, what changed, and what remains unknown without contacting a provider or executing tools.
- Missing artifacts, redacted payloads, unknown pricing, and capture failure prevent claims of complete reconstruction.

## Compatibility and validation

Use additive optional contracts first. Extend both agent diagnostic unions and provider stream consumers deliberately; adding stream variants can break exhaustive downstream switches and must be documented/versioned appropriately. Preserve the current terminal rendering and callback behavior through compatibility adapters, including the existing `--show-trace` meaning until an explicit migration is made.

Version any changed session/trace format, retain readers for existing supported sessions, and test old snapshots with missing trace metadata. Attach run references without making a trace file mandatory for ordinary session restoration. Retention should keep referenced artifacts or record their deletion; a missing file must not silently become an empty result.

Use deterministic provider/tool fixtures and targeted child-process crash tests. Exercise nonzero shell exits, cancellation races, remote timeout with unknown completion, successful side effects followed by storage failure, disk-full/write failures, slow sinks, truncated journals, and old-session resume. Trace assertions must verify causal completeness and outcomes, not only event shapes. Optional live smoke tests supplement fixtures when credentials and paid-call authorization are available.

For implementation changes, run the repository-required build, tests, formatting, and pinned Fallow checks. Measure journal overhead on token-heavy and tool-heavy fixture runs; record latency and disk growth and set a justified regression threshold. Do not capture every token by default merely to demonstrate event volume.

## Completion checklist

- [x] G1: Every observed request, attempt, tool operation, and relevant context operation has causal identity and a durable record or explicit capture-failure signal.
- [x] G2: Completed tool results survive later interruption; command failures and uncertain side effects are accurately represented.
- [ ] G3: Requests and calls reference the actual configuration, prompt, policy, scope, and fallback state they used, including individual skill invocations, reviewed arguments, and cancelled approval decisions.
- [x] G4: Timing and available usage/cost are attributed correctly; a portable bundle supports offline reconstruction within its stated capture level.
- [x] All nine provider adapters have contract fixtures and documented availability limits.
- [x] Existing API/session compatibility and secret-handling tests pass.
- [x] The failed-run reconstruction scenario passes after process restart and export to a fresh directory.
- [x] Re-score components against the findings rubric using actual implementation evidence; do not raise scores solely because a planned milestone is complete.

The nine-adapter fixture item is complete in merged [providers PR #16](https://github.com/esack7/propio-providers/pull/16). G3 remains unchecked until the green candidate in [agent PR #100](https://github.com/esack7/propio-agent/pull/100) merges. The [acceptance review](../specs/runtime-traceability/acceptance-review.md) maps the test evidence and remaining observation limits.

Detailed scratchpad revision tracking, claim-level summary provenance, and a graphical timeline can follow these priorities. The initial delivery must establish reliable evidence and offline inspection first.
