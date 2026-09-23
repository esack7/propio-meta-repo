# Runtime traceability acceptance review

Date: 2026-09-22 (Pacific)

Merged baseline: `propio-agent` main `7b0e428`; `propio-providers` main `fe34bb5`

Merged adapter verification: [providers PR #16](https://github.com/esack7/propio-providers/pull/16). Candidate detailed G3 provenance: [agent PR #100](https://github.com/esack7/propio-agent/pull/100).

This review maps the twelve criteria in `requirements.md` to executable evidence. “Met” means the stated behavior is merged and supported by code and a deterministic test; it does not imply that every upstream SDK field or external side effect is observable. “Candidate” means the tests pass locally and in PR CI but the change is not merged. “Partial” means the literal criterion has a remaining evidence gap.

| ID | Acceptance criterion | Status | Evidence and limit |
| --- | --- | --- | --- |
| A1 | Two turns, tool calls, retry, summary, causal IDs, ordered events | Met | Merged [agent PR #99](https://github.com/esack7/propio-agent/pull/99) joins these in `src/__tests__/fullCapture.test.ts`, verifying run/session/turn/request/attempt and tool-operation links, sequence, and summary playback. Its retry is a synthetic provider observer sequence; the actual shared retry path is tested separately in providers `src/__tests__/trace.test.ts`. The early `turn_started` record has an operation ID but no turn ID; subsequent records carry the real turn ID and join through that operation. |
| A2 | Resume lineage, truncated journal, no duplicate results | Met | Agent `src/__tests__/recovery.integration.test.ts` hard-stops a child process, appends a truncated line, inspects an offline export, resumes with the same session and a linked new run, and checks that tools are not replayed. |
| A3 | Distinct shell, cancellation, launch, remote-unknown, and capture-failure outcomes | Met | Agent `src/tools/__tests__/implementations.test.ts`, `src/tools/__tests__/boundary.test.ts`, `src/mcp/__tests__/boundary.test.ts`, `src/__tests__/recoveryBehavior.test.ts`, and `src/__tests__/recovery.integration.test.ts` cover structured local outcomes, uncertain MCP completion, and retained side effects when local persistence fails. Merged `src/agent-core/__tests__/runtime.test.ts` delays the trace sink and confirms completion is recorded before the next tool dispatch. |
| A4 | Request/tool links to effective configuration, prompt, policy, and scope | Met | Agent `src/__tests__/agent.test.ts` configuration-lineage and policy tests plus `src/agent-core/__tests__/runtime.test.ts` prompt/scope tests assert the applied revisions and reviewed tool dispatch. [Agent PR #100](https://github.com/esack7/propio-agent/pull/100) additionally links individual skill invocations to those revisions and matches reviewed-argument fingerprints to dispatch. |
| A5 | OpenRouter mutation and xAI fallback as linked attempts | Met | Providers `src/__tests__/openrouter.test.ts` checks retry without tools and the mutation; `src/__tests__/xai.test.ts` checks distinct endpoint attempts. Shared attempt IDs/retry waits are checked in `src/__tests__/trace.test.ts`. |
| A6 | Every adapter covers success, tools, retry, failure, absent usage, and applicable termination | Met | The explicit nine-adapter scenario matrix below is backed by merged deterministic fixtures in [providers PR #16](https://github.com/esack7/propio-providers/pull/16), with all local and PR checks passing. SDK-internal retries remain outside the adapter-observed boundary. |
| A7 | Usage/cost aggregation preserves cumulative, partial, unavailable, and unknown price | Met | Agent `src/trace/__tests__/measurements.test.ts` checks deduplication, purpose/attempt attribution, partial metrics, pricing provenance, resolver failure, and truncated-capture caps. No default price is inferred. |
| A8 | Interrupted run exports and inspects offline without provider/tool access | Met | Agent `src/__tests__/recovery.integration.test.ts` and `src/trace/__tests__/journal.test.ts` move away the source before inspection; `src/__tests__/fullCapture.test.ts` verifies full-bundle material and read-only response playback. |
| A9 | Standard output/export excludes synthetic secrets and reports omissions | Met | Agent `src/trace/__tests__/journal.test.ts` checks standard redaction; `src/__tests__/agent.test.ts` checks configuration secrets; `src/__tests__/fullCapture.test.ts` checks omitted credentials and missing material. This is a tested synthetic-secret policy, not a guarantee against arbitrary secrets in ordinary text; full bundles remain private. |
| A10 | Compatibility and no implicit reusable-library trace I/O | Met | Agent `src/__tests__/agent.test.ts` exercises disabled/degraded tracing and prior session behavior; public boundary suites cover side-effect-free imports/construction. Providers tracing is optional and observers are isolated in `src/__tests__/trace.test.ts`. |
| A11 | Builds, tests, formatting, pinned Fallow | Met | Merged agent PR #99 and providers PRs #15–16 passed their gates. Providers PR #16 passed build, 411 tests, formatting, Fallow, and all GitHub checks on Node 20 and 24. Candidate agent PR #100 passes build, 1,631 tests, formatting, Fallow, and all GitHub checks on Node 20 and 24. |
| A12 | Measured token/tool overhead against documented thresholds | Met | Agent `npm run benchmark:trace` passed: full token 29.7 ms / 47,426 B; tool 3,028 ms / 489,152 B; workspace 950 ms / 50,757 B, all below the README limits. These are local fixtures, not live-provider latency. |

## Nine-adapter scenario matrix

Each linked suite exercises the concrete adapter with mocked transport. “Retry + absent usage” names the new or strengthened fixture in providers PR #16; success, tools, failure, and termination are also covered by adapter-specific tests in the same suite. The shared `src/__tests__/trace.test.ts` separately checks the observer/wrapper contract. These are deterministic fixtures, not live upstream certification.

| Adapter suite | Success | Tool use | Retry | Failure | Absent usage | Termination |
| --- | --- | --- | --- | --- | --- | --- |
| [Anthropic](https://github.com/esack7/propio-providers/blob/41dfec1993c5b1117008fbc13e3cf6e906efa294/src/__tests__/anthropic.test.ts) | Response identity + usage | Streamed `tool_calls` | Overload then success | API error mapping | Unmetered retry response | Raw `end_turn` / `tool_use` |
| [Bedrock](https://github.com/esack7/propio-providers/blob/41dfec1993c5b1117008fbc13e3cf6e906efa294/src/__tests__/bedrock.test.ts) | Request ID + usage | Consumed streamed tool call | Throttle then success | Service error mapping | Unmetered retry response | Raw `end_turn` / `tool_use` |
| [Ollama](https://github.com/esack7/propio-providers/blob/41dfec1993c5b1117008fbc13e3cf6e906efa294/src/__tests__/ollama.test.ts) | Model + token usage | Response tool call | Provider error then success | Exhausted connection failure | Unmetered retry response | Raw `stop` |
| [OpenRouter](https://github.com/esack7/propio-providers/blob/41dfec1993c5b1117008fbc13e3cf6e906efa294/src/__tests__/openrouter.test.ts) | Routed model + charge | Streamed tool call | 429 removes tools | 5xx and network errors | Unmetered retry response | Raw `tool_calls` |
| [OpenAI](https://github.com/esack7/propio-providers/blob/41dfec1993c5b1117008fbc13e3cf6e906efa294/src/__tests__/openai.test.ts) | Responses identity + usage | Function calls | 503 then success | Authentication/capacity errors | Unmetered retry response | Raw `completed` |
| [Meta](https://github.com/esack7/propio-providers/blob/41dfec1993c5b1117008fbc13e3cf6e906efa294/src/__tests__/meta.test.ts) | Responses identity + usage | Parallel function calls | 503 then success | Authentication/capacity errors | Unmetered retry response | Raw `completed` |
| [Gemini](https://github.com/esack7/propio-providers/blob/41dfec1993c5b1117008fbc13e3cf6e906efa294/src/__tests__/gemini.test.ts) | Response identity + native usage | Streamed tool calls | 503 then success | Network/API errors | Unmetered retry response | Raw `STOP` |
| [xAI](https://github.com/esack7/propio-providers/blob/41dfec1993c5b1117008fbc13e3cf6e906efa294/src/__tests__/xai.test.ts) | Response identity + usage | Streamed tool call | Rate-limit and regional fallback | Cancelled/exhausted requests | Unmetered tool response | Raw `tool_calls` |
| [Cloudflare](https://github.com/esack7/propio-providers/blob/41dfec1993c5b1117008fbc13e3cf6e906efa294/src/__tests__/cloudflare.test.ts) | Response identity + usage | Streamed tool call | 503 then success | API failure body | Unmetered retry response | Raw `stop` / `tool_calls` |

## Remaining verification before closing the spec

1. Review and merge agent PR #100, then mark the detailed G3 task complete. A6 is already met through merged providers PR #16.
2. Merge this evidence PR and run `close-spec` only after its worktrees are no longer needed.
3. Keep full-capture limits explicit: adapter payloads precede SDK serialization, hidden reasoning is unavailable, workspace capture excludes ignored/credential-shaped files, and external side effects are not reconstructed automatically.

No live provider calls or paid smoke tests were made for this review.
