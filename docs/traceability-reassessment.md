# Runtime traceability reassessment

Date: 2026-09-22 (Pacific)

Compared with: [original findings](traceability-findings.md) and [implementation plan](traceability-plan.md)

Reviewed main commits: `propio-agent` `ec1d6cc`, `propio-providers` `4c64546`

These are engineering scores on the original 0–9 rubric: durable evidence, causal linkage, provenance, outcome accuracy, and reconstruction. They are deliberately conservative. The merged implementation was checked with builds and tests (agent: 1,630; providers: 404), formatting, Fallow, and the trace benchmark. A new combined acceptance fixture is in [agent PR #99](https://github.com/esack7/propio-agent/pull/99), not included in the merged-code scores. No live provider calls were made.

| Agent / CLI component | Before → now | Evidence and remaining limit |
| --- | ---: | --- |
| Agent loop | 4 → 7 | [Runtime](../repos/propio-agent/src/agent-core/runtime.ts) journals linked requests, tool operations, policy decisions, and turn completions. Pre-turn `turn_started` has an operation ID but no real turn ID yet; external work remains outside the loop. |
| Diagnostic logging | 3 → 7 | [JSONL journal](../repos/propio-agent/src/trace/journal.ts) has ordered run events, durable completion barriers, redaction, and degraded-capture reporting. It is not a hosted or authenticated log. |
| Terminal UI and inspection | 3 → 4 | [Offline inspection](../repos/propio-agent/src/trace/inspection.ts) exists, but there is still no integrated CLI timeline or filterable graphical viewer. |
| User-entered shell commands | 1 → 1 | [Interactive bash path](../repos/propio-agent/src/ui/processBashCommand.ts) still has no trace producer; agent-invoked bash is separate. |
| System prompt and project instructions | 4 → 6 | [Agent configuration capture](../repos/propio-agent/src/agent.ts) and request prompt revisions provide effective-state history; exact source-file/section provenance is not uniformly retained. |
| Prompt budgeting and selection | 5 → 7 | [Runtime prompt-plan records](../repos/propio-agent/src/agent-core/runtime.ts) retain selection/omission and request fingerprints; standard mode does not include raw prompts. |
| Conversation state | 6 → 8 | [Recovery journal](../repos/propio-agent/src/sessions/recoveryJournal.ts) and incremental tool commits retain completed results across interruption; concurrent writers remain unsupported. |
| Summarization and compaction | 5 → 7 | [Summary trace](../repos/propio-agent/src/agent.ts) has linked runs, request purpose, summary revisions and full-mode response events; claim-to-source provenance is absent. |
| Pinned memory | 7 → 7 | Existing revision/origin history remains useful; this project did not add mandatory source references. |
| Skills | 6 → 6 | Existing invocation/scope records remain; this project did not establish complete invocation-to-request provenance. |
| Configuration and model selection | 2 → 7 | [Configuration lineage](../repos/propio-agent/src/agent.ts) records redacted effective state, origins, changes, and request revision IDs; external configuration changes between observations may be missed. |
| Modes, permissions, approvals | 3 → 7 | [Policy records](../repos/propio-agent/src/agent-core/runtime.ts) and CLI mode revisions link decisions to dispatch and reviewed arguments; external approval UI details are not captured. |
| MCP connections and calls | 3 → 6 | [MCP outcomes](../repos/propio-agent/src/mcp/connectionManager.ts) distinguish confirmed remote responses from uncertain timeouts; remote server-internal side effects remain unknown. |
| Session persistence and recovery | 5 → 8 | [Restart fixture](../repos/propio-agent/src/__tests__/recovery.integration.test.ts) verifies lineage, truncated tails, retained results and no automatic replay; a crash before durable completion remains unknown. |
| Tool-output artifacts | 5 → 6 | [Full export](../repos/propio-agent/src/trace/inspection.ts) inventories hashed material and omissions; standard export omits raw results and built-in pruning has no event producer. |
| Scratchpads | 2 → 2 | Scratchpad contents are not independently revisioned or inventoried as trace artifacts. |
| File mentions and attachments | 5 → 6 | Full request capture preserves supplied material, but dedicated source-hash and transformation provenance is incomplete. |
| Docker sandbox | 2 → 3 | Full-capture level is forwarded by the wrapper; container/image/mount identity is not recorded in the run trace. |

| Tool component | Before → now | Evidence and remaining limit |
| --- | ---: | --- |
| Tool registry | 4 → 7 | [Execution registry](../repos/propio-agent/src/tools/executionRegistry.ts) retains reviewed argument snapshots and persistence failures; [runtime](../repos/propio-agent/src/agent-core/runtime.ts) journals decisions and outcomes. |
| Read | 5 → 5 | Returned content remains available as a tool result in full capture; no dedicated per-read file-version/hash evidence was added. |
| Write | 4 → 7 | [Tool outcomes](../repos/propio-agent/src/tools/types.ts) include create/replace, before/after hashes, and committed side-effect status. |
| Edit | 4 → 7 | The same structured evidence covers edits; exact patch-level provenance remains limited. |
| Grep | 4 → 4 | Search results are capturable, but unreadable/skipped files are not fully accounted for. |
| Find | 4 → 4 | Captured results do not independently prove traversal completeness. |
| List directory | 4 → 4 | Captured results do not retain a directory-version or completeness guarantee. |
| Bash | 4 → 7 | [Shell outcomes](../repos/propio-agent/src/tools/bash.ts) distinguish nonzero exit, timeout, cancellation, launch failure and output loss; child process-tree/external side effects cannot be fully observed. |

| Provider component | Before → now | Evidence and remaining limit |
| --- | ---: | --- |
| Shared contract | 3 → 7 | [Trace contract](../repos/propio-providers/src/trace.ts) adds request/attempt IDs, timings, usage availability, actual model/response metadata, mutation, and opt-in payload capture. |
| Shared retry machinery | 4 → 7 | [Retry tests](../repos/propio-providers/src/__tests__/trace.test.ts) verify distinct attempts, wait links and failures; retries performed invisibly inside SDKs are not guaranteed observable. |
| Anthropic | 3 → 6 | Adapter tests cover response identity, cumulative/cache usage and raw termination; payload is SDK input, not wire bytes. |
| Bedrock | 3 → 6 | AWS request ID, usage and raw termination are captured; a separate actual model is unavailable. |
| Ollama | 3 → 6 | Actual model and local token counts are captured; upstream request ID is unavailable. |
| OpenRouter | 3 → 7 | Routed model, usage/charge and tools-removal retry mutation are recorded; upstream routing internals remain opaque. |
| OpenAI | 3 → 6 | Responses identity/model/usage and termination are captured; opaque reasoning continuation is intentionally excluded. |
| Meta | 3 → 6 | Responses identity/model/usage and visible commentary classification are captured; hidden reasoning is not. |
| Gemini | 3 → 6 | Response metadata and native/OpenAI-compatible usage are captured where returned; signed tool-history transformations limit wire-level reconstruction. |
| xAI | 3 → 7 | Global/regional fallback produces distinct linked attempts with response metadata and usage when available. |
| Cloudflare | 3 → 6 | OpenAI-compatible response metadata/usage is captured where supplied; upstream details remain conditional. |

| Cross-component capability | Before → now | Evidence and remaining limit |
| --- | ---: | --- |
| Actual usage and cost attribution | 0 → 7 | [Measurements](../repos/propio-agent/src/trace/measurements.ts) deduplicate cumulative reports, separate request purpose/attempt and reported charges from injectable local estimates, and keep unknown price/usage unknown. |
| Portable reconstruction / recorded-response playback | 2 → 7 | [Export inspection](../repos/propio-agent/src/trace/inspection.ts) verifies versioned, hashed standard/full bundles; [playback](../repos/propio-agent/src/trace/playback.ts) reads only completed recorded events. This is not deterministic re-execution or a complete external-side-effect snapshot. |

## Priorities after this review

The four priority gaps are materially improved, but the literal all-nine-adapter scenario grid in [the acceptance review](../specs/runtime-traceability/acceptance-review.md) is only partially evidenced. The next verification decision is whether to build that exhaustive grid or accept shared retry tests plus adapter-specific field fixtures. A delayed-sink durability test is also still open. User-entered shell commands, scratchpad inventories, Docker identity, and a timeline UI are visible low-score follow-ups, not silently counted as completed by the core tracing work.
