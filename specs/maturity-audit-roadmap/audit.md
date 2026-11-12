# Audit: propio-agent and propio-providers maturity

Date: 2026-11-11

Baseline (both reference clones fast-forwarded to `origin/main` before reading):

- `propio-agent` `efa1de8f4e5b1c06eeb5cdb59400add89fb059ba`
- `propio-providers` `010d330d844d769fee5ef7325ca3be57baf1efe7`

This is a source and architecture audit. No provider was called and the CLI was
not driven interactively, so UX findings come from the rendering code rather
than from observed sessions. Test suites were run afterwards as a baseline;
results are in [tasks.md](tasks.md). `mature-agent-cli` was not
consulted.

It replaces an audit from 2026-08-18, which was never committed and has been
removed at the owner's request. Since then the trace, tool-outcome, cancellation, and headless-runtime findings
were largely addressed; the permission, validation, evaluation, prompt-cache, and
provider-capability findings were not.

## Summary

The engine is ahead of the cockpit. Context management, session recovery, trace
capture, and the provider adapters are dependable. What the operator touches is
not: there is no way to approve or deny an action, no way to redirect a running
turn other than cancelling it, tool calls render as one truncated line, and the
trace data that now exists can only be read by writing code against a library.

The reusable-primitive work is half done. Six subsystems are exported as
"provisional" subpaths of `@propio-ai/agent`, each with a side-effect-free import
test and a standalone example. They are not yet independent: they import each
other, the package also exports every internal file through a `"./*"` wildcard,
and `src/agent.ts` (3,209 lines) still owns most application behavior through
roughly twenty integration callbacks into the runtime.

## Maturity scale

| Level | Meaning |
| --- | --- |
| 0 | Absent |
| 1 | Prototype: hooks or a narrow special case exist |
| 2 | Functional: works for the common path, known gaps in control or coverage |
| 3 | Dependable: tested failure paths, safe to rely on daily |
| 4 | Primitive: stable versioned API, no application imports, a second consumer |

## Scorecard

| Area | Level | Daily-driver blocker | Main gap |
| --- | :-: | :-: | --- |
| Permissions and approvals | 1 | Yes | Execute mode allows every enabled tool; no approval prompt, no rules |
| Operator steering | 1 | Yes | Escape cancels; nothing else can redirect a running turn |
| TUI tool-call rendering | 2 | Yes | One line per call, 120-character preview, no diff, no live output |
| Trace capture | 3 | No | Solid; remaining gaps are documented low scores |
| Trace usability | 1 | Yes | Library API and an environment variable; no command reads a trace |
| Built-in tools | 2 | Partly | No schema validation, no tool metadata, sequential only, eight tools |
| MCP | 2 | Partly | stdio and tools only, one global config file |
| Skills | 2 | No | Inline only; forked execution is rejected |
| Agent runtime (`agent-core`) | 2 | No | Headless loop is tested; the application wrapper is still a monolith |
| Context management | 3 | No | Strongest subsystem; imports skills, modes, file search, and trace |
| Sessions and recovery | 3 | No | Crash recovery verified; concurrent writers unsupported |
| Providers | 3 | No | Thin capability model, no prompt-cache controls, live tests for 4 adapters |
| Outcome evaluations | 0 | No | None; nothing measures whether a change helps task success |
| Packaging and boundaries | 2 | No | Provisional subpaths plus a wildcard export; cross-subsystem imports |

## Findings

### 1. Permissions: the hooks exist, the policy does not

`Agent.authorizeToolExecution` (`src/agent.ts:751`) applies two rules: plan mode
restricts `write`/`edit` to the approved plan file, and plan/discover modes run
`bash` through a command classifier. For every other case, including all of
execute mode, it returns `allowed: true` with rule `mode_policy`.

- `resolveEffectiveToolAllowlist` (`src/modes/policies.ts`) returns `undefined`
  in execute mode unless a skill declares `allowed-tools`, so the full enabled
  surface is available.
- The only interactive checkpoint is the global-install prompt in
  `src/tools/bash.ts`, driven by a command classifier
  (`src/tools/globalInstallGuard.ts`, 480 lines).
- File tools accept any absolute path. `resolveToolPath` (`src/tools/shared.ts`)
  resolves relative paths against the workspace and passes absolute paths through.
- Plan and discover modes rely on `src/modes/bashPolicy.ts` (591 lines), a
  hand-written shell tokenizer with deny lists. It is a reasonable guard against
  accidents and not a security boundary.
- Tool arguments are never validated against the advertised JSON Schema. `zod`
  is a dependency but is used only under `src/auth/`.
- MCP tools go through the same path with the same result: allowed.

What is already in place and should be reused: the runtime evaluates
`integrations.authorizeTool` against a detached argument snapshot before every
dispatch, treats a throwing callback as a denial, and journals each decision with
actor, rule, reason, and an argument fingerprint
(`src/agent-core/runtime.ts:1227-1330`). The public tool registry has an
`approve` callback with the same fail-closed behavior. The CLI supplies neither
with an operator decision. The missing pieces are a rule model, a prompt, and
persistence of the operator's answers.

### 2. Steering: cancel is the only control

During a turn the terminal listens for one key. `createTurnCancelListener`
(`src/ui/turnCancelListener.ts`) maps Escape to abort. There is no input queue,
no way to add guidance for the next model step, and no way to deny one tool call
while letting the turn continue. Combined with finding 1, the operator's choices
during a run are to watch or to stop.

Tool calls in a batch run strictly in order (`executeToolCalls`,
`src/agent-core/runtime.ts:1163`), each committed to context before the next
starts. That ordering is what makes an approval prompt between calls
straightforward to add.

### 3. TUI: tool calls are reduced to a label

The view model is five fields (`src/ui/toolCallView.ts`): id, tool name, status,
`useLabel`, `resultLabel`. Everything a tool produces is flattened into those two
strings before it reaches the renderer.

- A finished call renders as `useLabel — resultLabel` on one line
  (`TerminalUi.appendToolCallTranscriptEntry`, `src/ui/terminal.ts:281`).
- Tools without a display adapter fall back to the first 120 characters of the
  raw result with whitespace collapsed (`src/tools/registry.ts`).
- `edit` and `write` show the path only. No diff rendering exists anywhere in
  `src/ui` or `src/tools`.
- `bash` shows the command, then a summary after exit. Output is not streamed
  while the command runs.
- The retained bottom zone shows only the most recent tool view
  (`lastMapValue(state.toolCallViews)`, `src/ui/replRenderer.ts:227`).
- Whether views are appended or updated in place depends on whether thinking
  output is visible, so the same turn lays out differently under different
  visibility flags (`src/ui/assistantTurnRenderer.ts:204-270`).
- No duration, no expand/collapse, no grouping of related calls.

The terminal layer is hand-written: 10,992 lines in `src/ui`, including a
2,033-line prompt session and its own keypress parser, paste handling, typeahead,
and markdown stream. It is well tested (about 10,900 lines of tests). The
clunkiness is a data-model problem more than a rendering-engine problem: the
renderer cannot show what the event does not carry.

### 4. Traceability: captured well, exposed poorly

Capture is the most improved area since August. Every run writes an ordered JSONL
journal under the sessions directory, linked by run, session, turn, request,
attempt, and tool-operation IDs, with usage and cost aggregation, redaction,
portable export, and bundle verification.

None of it is reachable from the product:

- No CLI subcommand and no slash command reads a journal. `inspectTraceJournal`,
  `exportTraceJournal`, and `verifyTraceExport` are called only from tests and
  from consumer code written against `@propio-ai/agent/trace`.
- Full capture is switched on by `PROPIO_TRACE_CAPTURE_LEVEL=full` at startup.
- `--show-trace` predates the trace system and only toggles status lines and
  reasoning summaries.
- There is no in-session usage or cost display, although the measurements exist.
- No pricing resolver is installed, so cost is reported only where a provider
  returns a charge.
- The trace README section is two paragraphs of roughly 400 words each,
  describing manifest versions. It documents the format, not a workflow.

`docs/traceability-reassessment.md` already scores "terminal UI and inspection"
at 4 of 9 and lists user-entered shell commands (1), scratchpads (2), and Docker
identity (3) as open.

### 5. Tools: a sound contract around thin implementations

The execution contract is clean: `ExecutableTool` with an `AbortSignal`,
structured outcomes that distinguish timeout, cancellation, nonzero exit, and
launch failure, before/after hashes on writes, and consumer-owned output
persistence.

Gaps:

- No argument validation (finding 1).
- No tool metadata. Nothing declares a tool read-only, side-effecting,
  network-using, or safe to run concurrently, so neither policy nor scheduling
  can reason about a call without knowing the tool by name.
- Sequential execution only, including independent reads.
- Eight built-ins: `read`, `write`, `edit`, `grep`, `find`, `ls`, `bash`,
  `skill`. No web fetch or search, no task list, no question-to-operator tool, no
  sub-agent tool, no background process handling.
- No undo. Full-capture mode already snapshots workspace files by hash after each
  tool result, which is most of what a checkpoint/rewind feature needs, but it is
  wired only to trace export.
- `src/tools` imports `RuntimeConfig` from `src/config`, and several tools fall
  back to `process.cwd()`.

### 6. MCP: lifecycle is careful, coverage is narrow

`src/mcp/connectionManager.ts` handles connect deadlines, call timeouts, child
cleanup, reconnect, and uncertain-completion outcomes with good test coverage.

- Transport is `StdioClientTransport` only. Remote servers over HTTP, and
  therefore OAuth, are unsupported.
- Only tools are consumed. Resources, prompts, and tool-list change
  notifications are not.
- Configuration is one file, `~/.propio/mcp.json`. There is no project-level
  server list, so a repository cannot declare the servers it needs.
- Config entries are `command`, `args`, `env`, `enabled`. No per-server tool
  filter or trust setting.
- Every discovered tool schema is sent on every request; there is no deferred
  loading for servers with large tool sets.

### 7. Skills: discovery is solid, execution is inline only

Parsing, precedence, diagnostics, path matching, and invocation lineage are
complete and traced. The frontmatter model already carries `allowed-tools`,
`model`, `effort`, `context`, `agent`, and `paths`.

- `context: fork` is parsed and then rejected at invocation
  (`src/agent.ts:1516`). There is no sub-agent runtime to fork into;
  `getSubagentToolAllowlist` in `src/modes/policies.ts` is an unused placeholder.
- `allowed-tools` narrows the tool surface, which is the reverse of how it is
  usually read (as pre-approval). Once a permission model exists this needs a
  deliberate decision.
- `InvokedSkillRecord` is imported by `src/context`, tying the two subsystems
  together.

### 8. Runtime and application structure

`AgentRuntime` (`src/agent-core/runtime.ts`, 2,185 lines) is a real headless
loop with direct tests for cancellation, denial, recovery, and stalled streams.
`Agent` (`src/agent.ts`, 3,209 lines, roughly 130 methods) wraps it and supplies
about twenty integration callbacks covering file mentions, plan mode, skills,
summaries, tool-output persistence, recovery checkpoints, and trace capture.
`src/index.ts` adds another 1,427 lines of command handling.

The runtime is extracted; the application behavior around it is not decomposed.
A second Propio application would get the loop and would have to rebuild
everything in `agent.ts` that it also needs.

Cross-subsystem imports, excluding tests:

| Subsystem | Imports from |
| --- | --- |
| `agent-core` | `context`, `tools`, `trace`, `diagnostics` |
| `context` | `skills`, `modes`, `fileSearch`, `trace` |
| `tools` | `config` |
| `mcp` | `tools`, `config` |
| `modes` | `tools`, `skills` |
| `skills`, `trace` | none |

`package.json` exports `./context`, `./skills`, `./mcp`, `./tools`,
`./agent-core`, and `./trace`, and also `"./*": "./*"`, which makes every file in
the package importable and undercuts the curated entry points.

### 9. Providers

`@propio-ai/providers` is the one finished extraction: published, semantically
released, ten adapters behind a single streaming method, typed errors, shared
retry, and a trace contract with request and attempt identity.

- `ProviderCapabilities` has three fields: context window, images, synthetic
  tool-call history.
- `ChatRequest` carries messages, model, tools, and reasoning opt-in. It has no
  tool choice, output limit, sampling parameters, structured output, or
  provider-specific options.
- No adapter sets prompt-cache controls. Cache token counts are reported when a
  provider returns them, but the Anthropic and Bedrock adapters never mark a
  cache breakpoint, and the agent's system prompt embeds a per-request timestamp
  (`src/prompt/systemPromptContext.ts:41`). For a daily driver on those providers
  this is a direct cost and latency penalty on every iteration.
- Live integration tests exist for Anthropic, OpenAI, Meta, and Cloudflare.
  Bedrock, Ollama, OpenRouter, Gemini, xAI, and the ChatGPT subscription adapter
  are covered by mocked transports only.

### 10. Evaluation

Unchanged since August: about 37,000 lines of deterministic tests in the agent
and none that run the agent on a task and grade the outcome. Every phase in the
roadmap changes behavior the operator feels; without a small task suite there is
no way to tell an improvement from a regression except by using it.

### 11. Configuration

All configuration is user-global under `~/.propio/` (`providers.json`,
`mcp.json`, `settings.json`). Project instructions come from `AGENTS.md`;
nothing else about a project is configurable. Permission rules, MCP servers, and
skills all need a project scope, and they should share one loader with one
precedence order rather than each growing its own.

## What does not need work first

- Context management, summaries, pinned memory, and session recovery.
- Trace capture and the journal format.
- Provider adapter correctness and retry behavior.
- Release automation in both repositories.

These are the stable ground the roadmap builds on.
