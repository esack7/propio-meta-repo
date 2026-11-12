# Design: maturity-audit-roadmap

## Overview

Findings are in [audit.md](audit.md). This document defines the future state and
the order of work to reach it.

The roadmap follows one rule: **harden a subsystem while extracting it.** Each
phase fixes an operator-facing problem and, in the same change, removes that
subsystem's imports from the rest of the application. Extraction is never a
separate cleanup pass, and no phase is finished while its primitive still reaches
into application code.

## Future state

### Primitives

| Primitive | Owns | Must not own |
| --- | --- | --- |
| `providers` | Adapters, streaming contract, capabilities, retries, request trace events | Agent loop, pricing, configuration paths |
| `policy` (new) | Tool capability vocabulary, rule matching, decision types, permission modes | Prompts, terminal UI, settings file locations |
| `tools` | Execution contract, schema validation, registry, tool metadata | Rendering, policy decisions, runtime configuration |
| `tools-local` | File, search, and shell implementations for a local workspace | Anything a server without a workspace needs |
| `mcp` | Transports, connection lifecycle, discovery, call outcomes | Configuration file locations, tool rendering |
| `skills` | Parsing, discovery from supplied roots, precedence, invocation metadata | Execution, permission grants |
| `context` | Turns, prompt planning, summaries, memory, serialization | Skill records, mode state, file search |
| `trace` | Journal, recorder, inspection, export, measurements, pricing interface | Storage discovery, terminal formatting |
| `agent-core` | Model/tool loop, the session protocol (below), scheduling, sub-agent execution | Storage, transports, plan mode, slash commands |
| `cli` (application) | Configuration loading, file-backed stores, modes, terminal UI, commands, sandbox | Anything a second application would also need |
| `chat-server` (application, in `propio-server`) | HTTP transport for the session protocol, its own stores, MCP-only tool surface, web chat | Anything the CLI would also need |

### Dependency direction

```
cli, chat-server ──▶ agent-core ──▶ context ──▶ providers (types)
 │                       ├────────▶ tools ───▶ policy
 │                       ├────────▶ policy
 │                       └────────▶ trace (types)
 ├──▶ mcp ──▶ tools (contract only)
 ├──▶ trace
 └──▶ skills, tools-local ──▶ tools      (cli only)
```

`policy`, `skills`, and `trace` import no other primitive. `providers` imports
nothing from this graph. No primitive imports `cli`. No primitive reads
`~/.propio`, the working directory, or the environment unless the caller passed
it in.

### Second consumer

The first consumer other than the CLI is a web chat that talks to a Propio backend
server and uses MCP tools. Decided with the owner on 2026-11-11:

- **Single user now, multi-user later.** No authentication or tenancy is built
  yet, but nothing may prevent it. Every store, credential lookup, and MCP
  connection set is reached through an injected interface that takes an opaque
  owner scope; the CLI passes a constant. Policy decisions record who decided.
- **MCP only.** The server registers no file or shell tools. That is why local
  implementations are a separate primitive (`tools-local`) from the tool contract.
- **Resumable CLI sessions are required; remote sessions come later.** The
  protocol is designed for both and used in-process first.

The server is a consumer, not a primitive. It lives in its own repository and
depends only on published packages.

### Session protocol

One typed, JSON-serializable contract in `agent-core` that every frontend uses:

- **Commands** in: start or resume a session, submit a message, add guidance to a
  running turn, interrupt, answer an approval request.
- **Events** out: turn lifecycle, assistant text, thinking, tool calls with their
  display payload, approval requests, usage. Each event carries a per-session
  sequence number.
- **Resume** is "replay events after sequence N, then continue". The same
  operation restarts a CLI session after exit, reattaches a browser tab, and
  later serves a remote CLI.

The CLI calls it in-process. The server exposes it over HTTP with a streaming
response. Because an approval is a request event and a later command, it works
the same whether the answer comes from a keypress or a browser. The trace journal
already orders events by sequence; the protocol's event log and the journal
should share that numbering rather than become two histories.

### What "mature" means for a primitive

A primitive reaches level 4 when it has: a curated entry point and no wildcard
export; no imports outside the graph above; an import and construction test that
forbids filesystem, process, and network access; no module-level state, so many
instances can run in one process; a documented versioning policy;
and one consumer other than the CLI.

### What "daily driver" means

The owner can run a full working day in the CLI without switching tools because
of: an action taken without consent, a turn that could not be redirected, a tool
call that could not be read, or a question about cost or history that needed code
to answer.

## Roadmap

Phases are ordered by what blocks daily use. Each becomes its own spec through
`create-spec`; names below are proposed spec names.

| # | Spec | Repositories | Depends on | Purpose |
| - | --- | --- | --- | --- |
| 1 | `tool-permissions` | propio-agent | — | Operator consent before side effects |
| 2 | `turn-steering` | propio-agent | 1 | Redirect a running turn; command half of the protocol |
| 3 | `tool-call-rendering` | propio-agent | 1 | Readable tool calls; event half of the protocol |
| 4 | `trace-commands` | propio-agent | — | Read traces and cost from the terminal |
| 5 | `chat-server-spike` | propio-agent, propio-server | 1–3 | Find boundary problems while APIs are cheap to change |
| 6 | `outcome-evals` | propio-agent | 1 | Regression signal |
| 7 | `mcp-remote` | propio-agent | 1 | HTTP transport and OAuth, which the web chat needs |
| 8 | `session-stores` | propio-agent | 2, 3 | Resumable CLI sessions; storage a server can replace |
| 9 | `provider-capabilities` | propio-providers, propio-agent | 6 | Prompt caching and feature reach |
| 10 | `project-config` | propio-agent | 1 | Project-level settings |
| 11 | `tools-hardening` | propio-agent | 1, 3 | Concurrency, new tools, rewind |
| 12 | `mcp-maturity` | propio-agent | 7, 10 | Resources, prompts, project servers, deferred schemas |
| 13 | `subagents-and-skills` | propio-agent | 1, 11 | Forked skills |
| 14 | `primitive-packages` | propio-agent, propio-providers | 1–13 | Published primitives, CLI as its own package |
| 15 | `chat-server` | propio-server | 7, 8, 14 | The second consumer, for real |

Phases 1–4 are the daily-driver milestone. Phase 4 has no dependency and can run
alongside 1–3. Phases 5, 7, and 8 exist because of the second consumer; 5 is a
throwaway that produces a gap list, not a product.

### `tool-permissions`

Introduce the `policy` primitive and put an operator decision in front of side
effects.

Scope:

- Validate every tool call against its JSON Schema in the registry before
  dispatch; return a structured validation error to the model.
- Add tool metadata: capability set (`read`, `workspace_write`, `process`,
  `network`, `external`), read-only flag, concurrency-safe flag. MCP tools default
  to `external` and not concurrency-safe.
- Rule model: `allow` / `ask` / `deny`, matched on tool name plus an argument
  pattern (path glob for file tools, command prefix for `bash`, server and tool
  for MCP). Deny wins over ask, ask over allow.
- Permission modes replacing today's implicit behavior: `ask` (default), `accept
  edits` (workspace writes allowed, the rest asks), `plan`, `discover`, and
  `bypass` (today's behavior, explicit and visibly labeled).
- Workspace confinement for file tools by default; paths outside the workspace
  ask.
- Approval prompt in the TUI showing the exact operation, with: allow once; allow
  for the rest of the session, either this exact pattern, every call to this
  tool, or every call of this request type (capability, such as all workspace
  writes or all calls to one MCP server); always allow (persisted rule); and deny
  with an optional reason returned to the model.
- Configuration: rules in the user settings file, editable by hand, and a
  `/permissions` command to list, add, and remove rules and to show which rule
  decided the last call. Session grants are listed there too and can be revoked.
- Predefined settings: named presets that expand to a mode plus a rule set, for
  example read-only, ask (the default), accept edits, and bypass. A preset is
  selectable by flag, setting, or command, and user rules layer on top of it.
- Non-interactive runs: `ask` resolves to deny unless a flag or rule allows it.
- Fold the global-install prompt into the rule model. Keep the bash classifiers
  for plan and discover modes as they are.
- Wire through the existing `authorizeTool` integration so every decision keeps
  its trace record, now with actor `user` where the operator decided.
- An `ask` decision is a serializable approval request and a later answer, not a
  callback into terminal code. The CLI prompt is one implementation of answering.
- Rules are loaded and saved through an injected store that takes an owner scope.

Acceptance:

- No tool implementation is reachable with schema-invalid arguments.
- In `ask` mode, `write`, `edit`, `bash`, and any MCP call produce a prompt before
  executing; `read`, `grep`, `find`, and `ls` inside the workspace do not.
- A denial returns to the model as a tool result and the turn continues.
- A persisted allow rule suppresses the prompt in a new session; a deny rule
  cannot be overridden by an allow rule, a session grant, or a preset.
- Approving a tool or a request type for the session suppresses further prompts
  of that kind until the session ends, is restored on resume, and does not carry
  into a new session.
- A fresh install with no configuration starts in `ask`.
- Every preset is covered by a test that states which calls it allows, asks
  about, and denies.
- Non-interactive mode never blocks on a prompt.
- Each decision appears in the trace with rule and actor.
- `policy` imports nothing from the application and passes a guarded-import test.
- An approval request survives a JSON round trip, and a test answers one from
  outside the process that raised it.
- Two policy instances with different owner scopes in one process do not see
  each other's rules.

### `turn-steering`

Scope:

- Accept typed input while a turn runs and deliver it at the next iteration
  boundary as operator guidance, without cancelling.
- Escape interrupts the current model step or tool and returns to the prompt with
  completed tool results retained; the next message continues the same turn
  context.
- Denying a tool call with a reason (from phase 1) is the third steering path.
- Show queued input in the transcript so the operator can see what is pending.
- Express submit, guide, interrupt, and answer-approval as the typed commands of
  the session protocol. The terminal issues them; nothing in `agent-core` reads
  keys.

Acceptance:

- Input submitted mid-turn reaches the model before its next request, in order.
- Interrupting during a tool call leaves completed results in context and does
  not replay them.
- Cancellation of a running `bash` command terminates its process group.
- Every command survives a JSON round trip, and a headless test drives a full
  steered turn with commands alone.

### `tool-call-rendering`

Fix the data model first, then the views.

Scope:

- Replace the two-string `ToolCallView` with a typed display payload carried on
  tool events: kind (`diff`, `command`, `file_read`, `search`, `generic`),
  structured fields, timing, and status. Tools produce it; the runtime forwards
  it; the CLI renders it. The execution contract stays presentation-free.
- Renderers: unified diff for `edit` and `write`; live tail of `bash` output with
  exit status and duration; collapsed summaries for reads and searches; a generic
  key/value view for MCP tools.
- One layout regardless of visibility flags. Completed calls stay in the
  transcript; the bottom zone shows all calls in flight.
- A way to expand the last collapsed result.
- The approval prompt from phase 1 renders the same payload it is asking about.

Acceptance:

- An edit shows the changed lines before approval and after completion.
- A long-running command shows output while it runs.
- A turn with ten tool calls occupies a bounded number of lines until expanded.
- Rendering is identical with thinking output shown or hidden.
- Snapshot tests cover each renderer at narrow and wide terminal widths.
- Every event, including display payloads and errors, survives a JSON round trip
  and carries a per-session sequence number. A turn rendered from a replayed
  event log matches the turn rendered live.

### `trace-commands`

Scope:

- `propio trace list | show <run> | export <run> | verify <bundle>` on the
  existing inspection API. `show` prints a timeline: requests, attempts, tool
  operations, policy decisions, durations, tokens.
- In-session `/trace` (current run summary) and `/usage` (session tokens and
  cost).
- A flag and setting for capture level, replacing the environment variable as the
  primary switch.
- A default pricing resolver shipped as data with a version and date; unknown
  models stay unknown.
- Print the run ID and a `propio trace show` hint when a turn fails.
- Record user-entered `!` shell commands in the journal.
- Rename or retire `--show-trace`.
- Rewrite the README trace section as a workflow.

Acceptance:

- A failed run can be diagnosed from the terminal without writing code.
- Session cost is visible in-session and matches inspection of the journals.
- Timeline output is stable enough to snapshot-test.

### `chat-server-spike`

Scope: create `propio-server` and add it to the project map. Build the
smallest backend that accepts a message over HTTP, runs one turn against a
provider with one stdio MCP tool, streams protocol events to a bare web page, and
answers one approval request from the browser. In-memory storage. Use the
agent's existing subpath exports as they are.

The deliverable is a written gap list: every place the server had to import an
internal file, work around process-level state, or could not serialize something.
Those gaps become acceptance criteria on the phases that follow.

Acceptance: two sessions run concurrently in one server process without sharing
state; the gap list is recorded in the spec; no workaround is merged into the
agent as part of the spike.

### `outcome-evals`

Scope: a small hermetic task suite (fix a failing test, a constrained multi-file
change, a prompt-injection resistance case, a permission-boundary case), run
through non-interactive mode against fixture repositories, graded on outcomes,
with repeated trials and results stored with model, configuration, tokens, and
cost from the trace.

Acceptance: one command produces a pass-rate report; results from two
configurations can be compared; the permission case fails if phase 1 regresses.

### `mcp-remote`

Scope: streamable HTTP transport; OAuth with tokens held in an injected
credential store keyed by owner scope and server; one connection set per scope
rather than per process; per-server tool filters and permission rules.

Acceptance: a remote server authenticates, and reconnects in a new session
without a new login; two scopes in one process hold separate credentials and
connections to the same server; stdio behavior is unchanged.

### `session-stores`

Scope:

- Store interfaces for conversation snapshots, the protocol event log, and the
  trace sink, each taking an owner scope. The CLI supplies today's file layout;
  the server supplies its own.
- `propio --continue` (latest session in this workspace) and
  `propio --resume <id>`, in addition to the existing `/session` commands.
- Resuming restores mode, permission answers given for the session, and pending
  queued input, and replays the transcript from the event log so tool calls
  render as they did.
- Define what happens when two processes open one session: refuse the second
  writer.

Acceptance: a session exited mid-conversation resumes from the command line with
its transcript and permission state; a session killed mid-turn resumes with
completed tool results and without replaying them; an in-memory store passes the
same contract tests as the file store; a second writer is refused.

Remote sessions and reattaching to a turn that is still running are not in this
phase. They need the server, and the protocol above is what makes them a
transport change rather than a redesign.

### `provider-capabilities`

Scope:

- Extend `ProviderCapabilities` to describe tool calling, parallel tool calls,
  reasoning exposure, prompt caching, structured output, and usage reporting.
- Add request options for tool choice, output limit, and a discriminated
  provider-options extension.
- Prompt-cache breakpoints in the Anthropic and Bedrock adapters.
- In the agent, split the system prompt into a stable prefix and a volatile
  runtime block so the prefix is byte-identical across iterations.
- Classify adapters as verified or experimental by live-test coverage and say so
  in the README.

Acceptance: cache-read tokens are nonzero on the second iteration of a turn for
supporting providers and visible in `/usage`; consecutive iterations with
unchanged instructions produce an identical prefix; the eval suite shows no
pass-rate regression.

### `tools-hardening`

Scope: concurrent execution for calls marked concurrency-safe, with results
committed in call order; new tools (web fetch, task list, ask-the-operator);
background process handling for `bash`; file checkpoints with a rewind command
built on the existing workspace capture; removal of `RuntimeConfig` and
`process.cwd()` fallbacks from `src/tools`; separation of the contract and
registry from the local file and shell implementations.

Acceptance: independent reads run concurrently and writes stay ordered; a rewind
restores files changed in a turn; `tools` imports only `policy` and provider
types.

### `mcp-maturity`

Scope: project-level server configuration through the shared loader; tool-list
change notifications; resources and prompts; deferred tool-schema loading above a
size threshold.

Acceptance: a project file adds servers without touching the user file; a server
with a large tool set does not send every schema on every request.

### `project-config`

Scope: one loader for user and project settings with documented precedence,
schema validation with precise errors, and a configuration fingerprint in the
trace. Permission rules, MCP servers, and skill roots all read through it.

Acceptance: invalid configuration fails with file and field; a collaborator
reproduces behavior from tracked project settings plus their own credentials.

### `subagents-and-skills`

Scope: a sub-agent execution path in `agent-core` with its own context and an
inherited permission ceiling; a task tool; `context: fork` skills running through
it; a decision on `allowed-tools` semantics under the permission model; removal
of `InvokedSkillRecord` from `context`.

Acceptance: a forked skill runs without adding its transcript to the parent
context; a sub-agent cannot exceed the parent's permissions; traces link child
runs to the parent operation.

### `primitive-packages`

By this point each subsystem's imports already match the dependency graph.

Scope: convert `propio-agent` to an npm workspace with one package per primitive
and the CLI as its own package, so a server install pulls in no terminal
dependencies; remove the `"./*"` export; decompose `src/agent.ts` so that what
remains is CLI wiring; publish.

Acceptance: every primitive meets the level-4 definition above; the CLI consumes
only published entry points; installing the packages the server needs brings in no
terminal or shell dependency.

### `chat-server`

Scope: replace the spike with the real backend and web chat on published
packages: protocol over HTTP with reconnect by sequence number, durable stores,
remote MCP servers with approval in the browser, trace and usage views.

Acceptance: closing and reopening the browser reattaches to the session, including
one with a turn in flight; the server imports nothing but published entry points.
This is the evidence that moves the primitives it uses to level 4. `tools-local`
and `skills` are not exercised by it and stay at level 3 until something else
consumes them.

## Cross-repository changes

| Repository | Change |
|------------|--------|
| propio-agent | None in this spec. Every phase except 15 lands here. |
| propio-providers | None in this spec. Phase 9 lands here first, then the agent adopts it. |
| propio-server | Does not exist yet. Listed in the project map as a commented, planned entry; uncomment it with the real clone URL when the repository is created in phase 5. |

## Decisions

Decided on 2026-11-11:

- **Package layout.** An npm workspace inside `propio-agent` holds the primitives
  and the CLI, published as separate packages. `propio-providers` stays where it
  is. The server and web chat get their own repository and consume published
  packages, which keeps them honest about what is exported. This departs from
  the repository-per-primitive proposal in `docs/agent-abstractions-plan.md`,
  which the `context-management` and four `*-abstraction` specs followed. That
  document is kept as the record those specs cite; where it and this design
  disagree on layout, this design is current.
- **Second consumer.** The web chat and its backend, as described above.
- **Default posture: `ask`.** Permissions must be configurable, offer predefined
  settings, and allow approving a whole tool or request type for the session.
  `tool-permissions` carries these as scope and acceptance.
- **Rendering: keep the hand-written renderer** and fix its view model. Revisit
  only if `tool-call-rendering` shows the retained-mode renderer cannot do live
  regions.
- **Server repository name: `propio-server`.**
- **Prior documents.** The August audit and the harness guide were untracked and
  are removed. The abstractions plan is restored and committed because five
  earlier specs cite it.

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Approval prompts make the agent tedious and bypass becomes the habit | Read-only tools never ask; session and persisted allow rules; `accept edits` mode; measure prompts per turn in the trace |
| Permission and rendering work collide in the same UI files | `tool-call-rendering` starts after the approval prompt lands; both share one display payload |
| Extraction stalls because each phase skips its boundary cleanup | Guarded-import test and import-direction check are acceptance criteria of every phase, not only of `primitive-packages` |
| Behavior changes land with no outcome signal | `outcome-evals` follows the daily-driver milestone and gates `provider-capabilities` onward |
| Prompt-prefix changes alter model behavior | `provider-capabilities` depends on the eval suite |
| Designing for multi-user turns into building multi-user | The only requirement is an owner scope on injected interfaces and no process-level state; authentication and tenancy are out of scope until a second user exists |
| The protocol is designed in the abstract and misses what a real client needs | The spike runs before the protocol is treated as stable, and its gap list feeds the later phases |
| The spike grows into the product | In-memory storage only, and its code is discarded when `chat-server` starts |
| Audit conclusions about UX come from code, not observed sessions | Owner review (criterion a6) confirms or corrects findings 2 and 3 before `tool-permissions` starts |

## Alternatives considered

- **Extract packages first, then fix behavior.** Rejected: it freezes APIs before
  permissions, tool metadata, and display payloads have reshaped them, and delays
  every daily-driver fix.
- **Adopt an existing agent SDK and keep only the CLI.** Out of scope for this
  audit; the stated goal is owned primitives.
- **One large "CLI v2" spec.** Rejected: phases 1–4 are independently shippable
  and each is reviewable on its own.
- **Make the CLI a client of a local server now.** Rejected for now: it adds a
  daemon to every terminal session to buy remote access that is not yet wanted.
  Using the protocol in-process keeps that door open at the cost of a transport.
- **Put the server in the same workspace.** Rejected: an in-repo consumer can
  reach unexported files without anyone noticing.
