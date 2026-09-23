# Propio runtime traceability findings

Date: 2026-09-21

Status: source audit; implementation recommendations
Related document: [Priority implementation plan](traceability-plan.md)

## Scope and baseline

Traceability means reconstructing what happened during a run: inputs, requests, tool calls, decisions, configuration, retries, errors, side effects, and costs. This audit does not score requirements-to-code traceability or overall component quality.

Both reference clones were refreshed and confirmed up to date before the audit. They were checked again before this document was saved:

| Repository | Audited commit |
| --- | --- |
| propio-agent | `6ded485c6dbdaefa2baf78004d6a8e7883cef067` |
| propio-providers | `4de0d6979d802fc6a08aae743f2ac9da7b0a243d` |

The assessment is based on source and test-code inspection. No test suites or live provider requests were run for the audit. Scores are engineering judgments, not measured test results. Source links point into the local reference clones and may move as those clones are refreshed; the commits above identify the evidence baseline.

Propio has useful records within individual components, but weak connections between them. Conversation history, artifacts, and pinned memory provide the strongest foundations. Reconstructing exact requests, configuration changes, retries, side effects, and cost across component boundaries remains difficult.

## Scoring scale

| Score | Meaning |
| --- | --- |
| 0 | No traceability mechanism |
| 1–2 | Isolated output or current state |
| 3–4 | Structured events, with significant missing links |
| 5–6 | Useful linked records and partial reconstruction |
| 7–8 | Strong provenance and history, with limited gaps |
| 9 | Complete, durable, correlated, and verified reconstruction |

Scores consider evidence coverage, causal links, provenance, persistence, and outcome accuracy. Tool scores include the records supplied by the surrounding agent. A callback available to a library consumer is useful evidence, but does not by itself establish durable capture in the CLI.

## Agent and CLI components

| Component | Score | Existing evidence | Ways to add traceability |
| --- | --- | --- | --- |
| [Agent loop](../repos/propio-agent/src/agent-core/runtime.ts) | **4** | Turn lifecycle callbacks, iteration events, tool-call IDs, recovery diagnostics. | Add run, turn, request, and parent-operation IDs; record durations; guarantee terminal records for started operations, including recovery reconciliation. |
| [Diagnostic logging](../repos/propio-agent/src/index.ts) | **3** | Optional timestamped output to stderr or an append file. | Use versioned JSONL envelopes with session/run identity and sequence numbers; report write failures and await flushing. |
| [Terminal UI and inspection](../repos/propio-agent/src/ui/contextInspector.ts) | **3** | Tool previews, context inspection, latest prompt-plan inspection. | Add a persisted run timeline; link displayed operations to artifacts; filter by request, failure, or tool. |
| [User-entered shell commands](../repos/propio-agent/src/ui/processBashCommand.ts) | **1** | Commands and results displayed in the terminal. | Record them alongside agent actions with `actor=user`; capture working directory, outcome, duration, and cancellation. |
| [System prompt and project instructions](../repos/propio-agent/src/prompt/compileSystemPrompt.ts) | **4** | Named prompt sections; project instructions include source paths. | Record source-file hashes and section versions; link the exact compiled prompt to each request. |
| [Prompt budgeting and selection](../repos/propio-agent/src/context/coreTypes.ts) | **5** | Plans identify included/omitted turns, included artifacts, estimates, and retry level. | Persist every plan; explain individual omissions; record the final request after provider-specific transformations. |
| [Conversation state](../repos/propio-agent/src/context/conversationManager.ts) | **6** | Turn IDs, timestamps, assistant/tool entries, artifact references. | Link entries to requests/configuration revisions; retain interrupted/failed outcomes; journal changes incrementally. |
| [Summarization and compaction](../repos/propio-agent/src/context/summaryManager.ts) | **5** | Covered-turn IDs, refresh reasons, success/failure diagnostics, completion duration. | Preserve summary revisions; connect each to its generating request; trace summarized claims to source entries. |
| [Pinned memory](../repos/propio-agent/src/context/conversationManager.ts) | **7** | IDs, origins, optional source links, rationales, timestamps, replacement history, removal state. | Require source references where available; record the actor/cause of each revision; distinguish original provenance from revision provenance. |
| [Skills](../repos/propio-agent/src/skills/types.ts) | **6** | Invocation content, arguments, source path, time, scope, requested/applied model, warnings. | Add invocation IDs/content hashes; associate invocations with turns/requests; record scope activation and expiration. |
| [Configuration and model selection](../repos/propio-agent/src/config/runtimeConfig.ts) | **2** | Defined precedence; selected configuration partly represented in session metadata. | Persist redacted effective configuration and each value's source; record model/configuration changes and fingerprints. |
| [Modes, permissions, and approvals](../repos/propio-agent/src/agent.ts) | **3** | Denial results, mode state, plan-save approval state; reusable registry approval callback. | Record allow and deny decisions with rule, actor, reviewed arguments, scope, and time. |
| [MCP connections and calls](../repos/propio-agent/src/mcp/connectionManager.ts) | **3** | Server status, last error, stderr tail, server/tool mapping, deadlines, call results. | Persist connection transitions/discovery versions; link local calls to remote request IDs where exposed; distinguish remote failure, timeout, and uncertain completion. |
| [Session persistence and recovery](../repos/propio-agent/src/sessions/sessionHistory.ts) | **5** | Versioned snapshots, atomic snapshot writes, workspace association, crash markers. | Journal operations between snapshots; record resume lineage/recovery decisions; link snapshots to trace sequence positions. |
| [Tool-output artifacts](../repos/propio-agent/src/tools/outputPersistence.ts) | **5** | Session directories, external paths, sizes, line counts, linked conversation artifacts. | Add content hashes, originating operation IDs, retention/deletion records, and portable export manifests. |
| [Scratchpads](../repos/propio-agent/src/scratchpad/scratchpad.ts) | **2** | Session-associated directory and availability errors. | Inventory generated files; record creating operations, hashes, purpose, and retention status. |
| [File mentions and attachments](../repos/propio-agent/src/fileSearch/attachmentResolver.ts) | **5** | Requested/resolved paths, ranges, synthetic call/result links, captured content. | Add content hashes and globally unique attachment IDs; record clipping/transformations; extend provenance to image inputs. |
| [Docker sandbox](../repos/propio-agent/bin/propio-sandbox) | **2** | Version checks, launch errors, wrapper exit reporting. | Record container/image identity, mounts, effective isolation settings, launch/exit times, and run linkage. |

## Tool components

| Component | Score | Existing evidence | Ways to add traceability |
| --- | --- | --- | --- |
| [Tool registry](../repos/propio-agent/src/tools/executionRegistry.ts) | **4** | Structured execution statuses, approval hook, persistence-error field. | Give direct consumers execution events; capture schema/version and approval decisions; propagate persistence warnings into run records. |
| [Read](../repos/propio-agent/src/tools/read.ts) | **5** | Arguments and returned content can be retained through conversation artifacts. | Record resolved path, file hash, exact range, and clipping metadata. |
| [Write](../repos/propio-agent/src/tools/write.ts) | **4** | Requested content/path and completion message. | Record create versus overwrite, before/after hashes, resulting diff, and committed side-effect status. |
| [Edit](../repos/propio-agent/src/tools/edit.ts) | **4** | Replacement arguments and replacement count. | Record actual changed ranges, before/after hashes, and resulting patch. |
| [Grep](../repos/propio-agent/src/tools/grep.ts) | **4** | Query plus file/line matches. | Record scope/file versions; report skipped/unreadable files, which currently disappear into empty results. |
| [Find](../repos/propio-agent/src/tools/find.ts) | **4** | Pattern, requested root, sorted matches. | Record resolved root, traversal options, exclusions, timing, and completeness. |
| [List directory](../repos/propio-agent/src/tools/ls.ts) | **4** | Requested directory and stable typed entries. | Record resolved path, observation time, entry metadata, and completeness. |
| [Bash](../repos/propio-agent/src/tools/bash.ts) | **4** | Command arguments, stdout, stderr, and exit code. | Separate dispatch success from command success; record effective working directory, duration, termination reason, process identity, and output loss. |

## Provider components

The [public stream contract](../repos/propio-providers/src/types.ts) exposes text, tools, status, reasoning summaries, and terminal reasons, but no standardized actual usage or upstream request identity. [Retry diagnostics](../repos/propio-providers/src/diagnostics.ts) carry provider/model, iteration, attempt number, reason, and delay.

| Component | Score | Ways to add traceability |
| --- | --- | --- |
| Shared provider contract | **3** | Add correlated request/attempt lifecycle events, upstream IDs, actual usage, structured errors, and timings. |
| [Shared retry machinery](../repos/propio-providers/src/internal/withRetry.ts) | **4** | Link attempts to requests; record exhaustion, cancellation, and changes to requests between attempts. |
| [Anthropic](../repos/propio-providers/src/providers/anthropic.ts) | **3** | Retain message/request identity and usage, including cache accounting where returned; preserve the existing raw stop reason in the agent trace. |
| [Bedrock](../repos/propio-providers/src/providers/bedrock.ts) | **3** | Capture SDK request metadata, stream usage/metrics, region/model target, and original stop reason. |
| [Ollama](../repos/propio-providers/src/providers/ollama.ts) | **3** | Record resolved host/model identity, returned token/timing statistics, and whether cancellation stopped generation. |
| [OpenRouter](../repos/propio-providers/src/providers/openrouter.ts) | **3** | Capture actual routed model/provider, generation identity, usage, and an explicit event when a retry removes tools. |
| [OpenAI](../repos/propio-providers/src/providers/openai.ts) | **3** | Capture response/request identity, usage, terminal details, and links between continuation state and requests. |
| [Meta](../repos/propio-providers/src/providers/meta.ts) | **3** | Add response identity and usage where returned; record continuation lineage and commentary/final-output classification. |
| [Gemini](../repos/propio-providers/src/providers/gemini.ts) | **3** | Preserve response identity, usage, original finish reasons, and message/tool-history adaptation records. |
| [xAI](../repos/propio-providers/src/providers/xai.ts) | **3** | Record selected API path and each endpoint fallback; add response identity, usage, and endpoint-level timing. |
| [Cloudflare](../repos/propio-providers/src/providers/cloudflare.ts) | **3** | Record model/endpoint target, returned request identifiers and usage, and original terminal details. |

Equal adapter scores reflect a common tracing ceiling, not identical behavior. Fields unavailable from an upstream service must remain explicitly unavailable. Provider-private continuation data is not an explanation of model decisions and must not be exposed as reasoning telemetry.

## Missing cross-component capabilities

| Capability | Score | What to add |
| --- | --- | --- |
| Actual usage and cost attribution | **0** | Per-attempt input/output/cache usage; separately attributed summarization usage; pricing-versioned costs with explicit unknowns. Token estimates are insufficient. |
| Portable run reconstruction/replay | **2** | Bundle events, request snapshots, configuration, artifacts, and workspace changes. Support recorded-response playback separately from executing a task again. |

## Four priority gaps

### G1 — Connect the existing evidence

Carry session, run, turn, request, attempt, and operation identities across both packages, with parent links. Iteration numbers and provider tool-call IDs alone cannot reliably connect all records. Preserve existing conversation turn IDs instead of introducing a disconnected second identity.

Evidence: [agent diagnostics](../repos/propio-agent/src/diagnostics.ts), [runtime events](../repos/propio-agent/src/agent-core/events.ts), [provider diagnostics](../repos/propio-providers/src/diagnostics.ts).

### G2 — Make outcomes accurate and durable

Bash reports tool success for a nonzero command exit unless the executor reports abortion. Consumers that only inspect tool status can misclassify command outcomes.

Tool results are committed to conversation state after an entire batch finishes. Cancellation during a later tool call can prevent earlier completed results from reaching that record, even though callbacks may already have observed them. A missing result does not establish that no side effect occurred.

Persist each completion promptly. Distinguish dispatch/execution status, underlying operation outcome, cancellation requested versus confirmed, and unknown completion. Preserve trace evidence even when an incomplete conversational turn is discarded.

Evidence: [BashTool.executeWithStatus](../repos/propio-agent/src/tools/bash.ts), [AgentRuntime.executeToolCalls and runToolWithAbort](../repos/propio-agent/src/agent-core/runtime.ts), [registry output persistence failures](../repos/propio-agent/src/tools/executionRegistry.ts).

### G3 — Record changes that explain behavior

Model switches, effective configuration, policy decisions, prompt revisions, tool availability, and provider fallback changes need explicit historical records. OpenRouter's final retry can remove tools without a dedicated diagnostic describing that mutation. xAI can try alternate endpoints inside a request without a corresponding endpoint-attempt trace.

Record the cause, previous/new revision, scope, and effective point for each change. Link each request and tool execution to the revisions and decisions actually applied.

Evidence: [runtime configuration](../repos/propio-agent/src/config/runtimeConfig.ts), [agent policy/model switching](../repos/propio-agent/src/agent.ts), [OpenRouter retry mutation](../repos/propio-providers/src/providers/openrouter.ts), [xAI endpoint attempts](../repos/propio-providers/src/providers/xai.ts).

### G4 — Add request measurements and a run export

Capture latency, actual usage, upstream identity, and resulting side effects. Export those records with redacted configuration and artifact references. Include summarizer requests and failed/retried requests in accounting, while retaining unknown usage as unknown.

A practical acceptance test is reconstructing a failed run after restarting Propio, including what completed before failure, what changed, and what remains uncertain.

Evidence: [provider stream contract](../repos/propio-providers/src/types.ts), [session metadata](../repos/propio-agent/src/context/persistence.ts), [artifact storage](../repos/propio-agent/src/tools/outputPersistence.ts).

## Interpretation and next step

`--show-trace` currently enables status and reasoning-summary display. It does not supply durable execution history. The debug file contains a text prefix followed by JSON per event, rather than a pure versioned JSONL trace. Runtime lifecycle callbacks also do not all survive the CLI event adaptation.

Extend the existing events, context records, and persistence boundaries. The [implementation plan](traceability-plan.md) addresses G1–G4 in an incremental sequence with compatibility and failure-path checks.
