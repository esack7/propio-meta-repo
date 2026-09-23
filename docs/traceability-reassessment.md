# Runtime traceability reassessment

Date: 2026-09-22 (Pacific)

Compared with: [original findings](traceability-findings.md) and [implementation plan](traceability-plan.md)

Reviewed main commits: `propio-agent` `946ede9`, `propio-providers` `fe34bb5`

These are engineering scores on the original 0–9 rubric: durable evidence, causal linkage, provenance, outcome accuracy, and reconstruction. They are deliberately conservative. The merged implementation was checked with builds and tests (agent: 1,634; providers: 411), formatting, Fallow, and the trace benchmark. The combined acceptance and delayed-sink fixtures from [agent PR #99](https://github.com/esack7/propio-agent/pull/99), nine-adapter scenario matrix from [providers PR #16](https://github.com/esack7/propio-providers/pull/16), and detailed G3 provenance from [agent PR #100](https://github.com/esack7/propio-agent/pull/100) are merged. Only the skill score changes based on the new causal evidence; test-count growth alone does not raise scores. No live provider calls were made.

| Agent / CLI component | Before → now | Evidence and remaining limit |
| --- | ---: | --- |
| Agent loop | 4 → 7 | [Runtime](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/agent-core/runtime.ts) journals linked requests, tool operations, policy decisions, and turn completions. Pre-turn `turn_started` has an operation ID but no real turn ID yet; external work remains outside the loop. |
| Diagnostic logging | 3 → 7 | [JSONL journal](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/trace/journal.ts) has ordered run events, durable completion barriers, redaction, and degraded-capture reporting. It is not a hosted or authenticated log. |
| Terminal UI and inspection | 3 → 4 | [Offline inspection](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/trace/inspection.ts) exists, but there is still no integrated CLI timeline or filterable graphical viewer. |
| User-entered shell commands | 1 → 1 | [Interactive bash path](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/ui/processBashCommand.ts) still has no trace producer; agent-invoked bash is separate. |
| System prompt and project instructions | 4 → 6 | [Agent configuration capture](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/agent.ts) and request prompt revisions provide effective-state history; exact source-file/section provenance is not uniformly retained. |
| Prompt budgeting and selection | 5 → 7 | [Runtime prompt-plan records](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/agent-core/runtime.ts) retain selection/omission and request fingerprints; standard mode does not include raw prompts. |
| Conversation state | 6 → 8 | [Recovery journal](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/sessions/recoveryJournal.ts) and incremental tool commits retain completed results across interruption; concurrent writers remain unsupported. |
| Summarization and compaction | 5 → 7 | [Summary trace](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/agent.ts) has linked runs, request purpose, summary revisions and full-mode response events; claim-to-source provenance is absent. |
| Pinned memory | 7 → 7 | Existing revision/origin history remains useful; this project did not add mandatory source references. |
| Skills | 6 → 7 | [Skill invocation lineage](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/agent.ts) now assigns stable persisted invocation IDs, records activation/clearing, and links active invocations through prompt and scope revisions to provider requests. Legacy sessions use deterministic trace-only IDs; standard capture omits skill bodies. |
| Configuration and model selection | 2 → 7 | [Configuration lineage](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/agent.ts) records redacted effective state, origins, changes, and request revision IDs; external configuration changes between observations may be missed. |
| Modes, permissions, approvals | 3 → 7 | [Policy records](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/agent-core/runtime.ts) and CLI mode revisions link decisions to dispatch through ephemeral keyed argument fingerprints and distinguish denial, cancellation, and callback failure. External approval UI details are not captured. |
| MCP connections and calls | 3 → 6 | [MCP outcomes](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/mcp/connectionManager.ts) distinguish confirmed remote responses from uncertain timeouts; remote server-internal side effects remain unknown. |
| Session persistence and recovery | 5 → 8 | [Restart fixture](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/__tests__/recovery.integration.test.ts) verifies lineage, truncated tails, retained results and no automatic replay; a crash before durable completion remains unknown. |
| Tool-output artifacts | 5 → 6 | [Full export](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/trace/inspection.ts) inventories hashed material and omissions; standard export omits raw results and built-in pruning has no event producer. |
| Scratchpads | 2 → 2 | Scratchpad contents are not independently revisioned or inventoried as trace artifacts. |
| File mentions and attachments | 5 → 6 | Full request capture preserves supplied material, but dedicated source-hash and transformation provenance is incomplete. |
| Docker sandbox | 2 → 3 | Full-capture level is forwarded by the wrapper; container/image/mount identity is not recorded in the run trace. |

| Tool component | Before → now | Evidence and remaining limit |
| --- | ---: | --- |
| Tool registry | 4 → 7 | [Execution registry](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/tools/executionRegistry.ts) retains reviewed argument snapshots and persistence failures; [runtime](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/agent-core/runtime.ts) journals decisions and outcomes. |
| Read | 5 → 5 | Returned content remains available as a tool result in full capture; no dedicated per-read file-version/hash evidence was added. |
| Write | 4 → 7 | [Tool outcomes](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/tools/types.ts) include create/replace, before/after hashes, and committed side-effect status. |
| Edit | 4 → 7 | The same structured evidence covers edits; exact patch-level provenance remains limited. |
| Grep | 4 → 4 | Search results are capturable, but unreadable/skipped files are not fully accounted for. |
| Find | 4 → 4 | Captured results do not independently prove traversal completeness. |
| List directory | 4 → 4 | Captured results do not retain a directory-version or completeness guarantee. |
| Bash | 4 → 7 | [Shell outcomes](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/tools/bash.ts) distinguish nonzero exit, timeout, cancellation, launch failure and output loss; child process-tree/external side effects cannot be fully observed. |

| Provider component | Before → now | Evidence and remaining limit |
| --- | ---: | --- |
| Shared contract | 3 → 7 | [Trace contract](https://github.com/esack7/propio-providers/blob/fe34bb591024bf1042120bbeeb3fe309d4d5061c/src/trace.ts) adds request/attempt IDs, timings, usage availability, actual model/response metadata, mutation, and opt-in payload capture. |
| Shared retry machinery | 4 → 7 | [Retry tests](https://github.com/esack7/propio-providers/blob/fe34bb591024bf1042120bbeeb3fe309d4d5061c/src/__tests__/trace.test.ts) verify distinct attempts, wait links and failures; retries performed invisibly inside SDKs are not guaranteed observable. |
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
| Actual usage and cost attribution | 0 → 7 | [Measurements](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/trace/measurements.ts) deduplicate cumulative reports, separate request purpose/attempt and reported charges from injectable local estimates, and keep unknown price/usage unknown. |
| Portable reconstruction / recorded-response playback | 2 → 7 | [Export inspection](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/trace/inspection.ts) verifies versioned, hashed standard/full bundles; [playback](https://github.com/esack7/propio-agent/blob/946ede9efeb1895cb86d9581d431c7aa28fe4e57/src/trace/playback.ts) reads only completed recorded events. This is not deterministic re-execution or a complete external-side-effect snapshot. |

## Priorities after this review

The four priority gaps are materially improved in merged code. The literal all-nine-adapter scenario grid is in [providers PR #16](https://github.com/esack7/propio-providers/pull/16), with per-adapter evidence mapped in [the acceptance review](../specs/runtime-traceability/acceptance-review.md). Stable skill-invocation-to-request lineage and reviewed-argument/cancellation records are in [agent PR #100](https://github.com/esack7/propio-agent/pull/100). User-entered shell commands, scratchpad inventories, Docker identity, and a timeline UI are visible low-score follow-ups, not silently counted as completed by the core tracing work.
