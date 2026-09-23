# Runtime traceability acceptance review

Date: 2026-09-22 (Pacific)

Baseline: `propio-agent` main `ec1d6cc`; `propio-providers` main `4c64546`

Candidate final verification: [agent PR #99](https://github.com/esack7/propio-agent/pull/99)

This review maps the twelve criteria in `requirements.md` to executable evidence. “Met” means the stated behavior is supported by code and a deterministic test; it does not imply that every upstream SDK field or external side effect is observable. “Candidate” means the new fixture passes locally but is not merged. “Partial” means the literal criterion has a remaining evidence gap.

| ID | Acceptance criterion | Status | Evidence and limit |
| --- | --- | --- | --- |
| A1 | Two turns, tool calls, retry, summary, causal IDs, ordered events | Candidate | Agent `src/__tests__/fullCapture.test.ts` now joins these in one fixture, verifies run/session/turn/request/attempt and tool-operation links, sequence, and summary playback. Its retry is a synthetic provider observer sequence; the actual shared retry path is tested separately in providers `src/__tests__/trace.test.ts`. The early `turn_started` record has an operation ID but no turn ID; subsequent records carry the real turn ID and join through that operation. |
| A2 | Resume lineage, truncated journal, no duplicate results | Met | Agent `src/__tests__/recovery.integration.test.ts` hard-stops a child process, appends a truncated line, inspects an offline export, resumes with the same session and a linked new run, and checks that tools are not replayed. |
| A3 | Distinct shell, cancellation, launch, remote-unknown, and capture-failure outcomes | Met | Agent `src/tools/__tests__/implementations.test.ts`, `src/tools/__tests__/boundary.test.ts`, `src/mcp/__tests__/boundary.test.ts`, `src/__tests__/recoveryBehavior.test.ts`, and `src/__tests__/recovery.integration.test.ts` cover structured local outcomes, uncertain MCP completion, and retained side effects when local persistence fails. The candidate `src/agent-core/__tests__/runtime.test.ts` also delays the trace sink and confirms completion is recorded before the next tool dispatch. |
| A4 | Request/tool links to effective configuration, prompt, policy, and scope | Met | Agent `src/__tests__/agent.test.ts` configuration-lineage and policy tests plus `src/agent-core/__tests__/runtime.test.ts` prompt/scope tests assert the applied revisions and reviewed tool dispatch. |
| A5 | OpenRouter mutation and xAI fallback as linked attempts | Met | Providers `src/__tests__/openrouter.test.ts` checks retry without tools and the mutation; `src/__tests__/xai.test.ts` checks distinct endpoint attempts. Shared attempt IDs/retry waits are checked in `src/__tests__/trace.test.ts`. |
| A6 | Every adapter covers success, tools, retry, failure, absent usage, and applicable termination | Partial | All nine adapter suites test payload/metadata emission, and shared tracing tests retry, failure, terminal handling, and unavailable usage. There is not yet one explicit scenario matrix proving every applicable case for **each** adapter. SDK-internal retries also remain outside the adapter-observed boundary. |
| A7 | Usage/cost aggregation preserves cumulative, partial, unavailable, and unknown price | Met | Agent `src/trace/__tests__/measurements.test.ts` checks deduplication, purpose/attempt attribution, partial metrics, pricing provenance, resolver failure, and truncated-capture caps. No default price is inferred. |
| A8 | Interrupted run exports and inspects offline without provider/tool access | Met | Agent `src/__tests__/recovery.integration.test.ts` and `src/trace/__tests__/journal.test.ts` move away the source before inspection; `src/__tests__/fullCapture.test.ts` verifies full-bundle material and read-only response playback. |
| A9 | Standard output/export excludes synthetic secrets and reports omissions | Met | Agent `src/trace/__tests__/journal.test.ts` checks standard redaction; `src/__tests__/agent.test.ts` checks configuration secrets; `src/__tests__/fullCapture.test.ts` checks omitted credentials and missing material. This is a tested synthetic-secret policy, not a guarantee against arbitrary secrets in ordinary text; full bundles remain private. |
| A10 | Compatibility and no implicit reusable-library trace I/O | Met | Agent `src/__tests__/agent.test.ts` exercises disabled/degraded tracing and prior session behavior; public boundary suites cover side-effect-free imports/construction. Providers tracing is optional and observers are isolated in `src/__tests__/trace.test.ts`. |
| A11 | Builds, tests, formatting, pinned Fallow | Met | On agent PR #99: build, 1,630 tests, formatting, and Fallow pass locally; all GitHub checks pass on Node 20 and 24. On providers: build, 404 tests, formatting, and Fallow pass locally; merged PR #15 CI passed. |
| A12 | Measured token/tool overhead against documented thresholds | Met | Agent `npm run benchmark:trace` passed: full token 29.7 ms / 47,426 B; tool 3,028 ms / 489,152 B; workspace 950 ms / 50,757 B, all below the README limits. These are local fixtures, not live-provider latency. |

## Remaining verification before closing the spec

1. Merge the candidate joined fixture after CI and review.
2. Decide whether A6’s literal per-adapter scenario matrix is required for closeout; current suites cover the shared behavior and adapter-specific metadata but not the complete nine-by-scenario grid.
3. Keep full-capture limits explicit: adapter payloads precede SDK serialization, hidden reasoning is unavailable, workspace capture excludes ignored/credential-shaped files, and external side effects are not reconstructed automatically.

No live provider calls or paid smoke tests were made for this review.
