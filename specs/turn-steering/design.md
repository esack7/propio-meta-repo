# Design: turn-steering

## Overview

Redirect a running turn without cancelling it, and express operator input as
the typed commands of the session protocol.

Three things steer a turn: guidance typed while it runs, an interrupt that
keeps completed work, and denying a tool call with a reason (phase 1). This
spec builds the first two in the runtime, then puts all three, plus submitting
a message, behind one command contract that the terminal calls in-process and
a server can later call over HTTP.

## What exists at the baseline

`propio-agent` at `0d24312` (after `tool-permissions`).

- **One key.** `runInteractiveTurn` (`src/index.ts`) attaches
  `createTurnCancelListener` (`src/ui/turnCancelListener.ts`) for the length of
  a turn. It puts stdin in raw mode and maps Escape to
  `abortController.abort("escape")`. Nothing else is read.
- **Cancel, partly kept.** The runtime commits each tool result before it
  dispatches the next call (`executeToolCalls`, `src/agent-core/runtime.ts`),
  so results completed before a cancel are already in context. On abort,
  `emitTurnFailure` calls `abandonIncompleteTurn`, which removes the turn only
  if it has no entries. A turn cancelled after its first tool call is kept, but
  the call that was running and any calls after it in the batch are left
  without results. Only crash recovery fills such gaps
  (`src/agent.ts`, "Fill only missing responses").
- **No queue.** `AgentRuntime.streamChat` takes one `PromptSubmission` and
  refuses a second while running. The loop in `runTurn` has no point at which
  new operator input can enter.
- **Shell only.** `runWithSpawn` (`src/tools/runShellCommand.ts`) starts
  `/bin/sh -c` without its own process group and cancels with `child.kill()`.
  That signals the shell; a child the shell started can survive. Timeout and
  the output cap use the same call.
- **Approvals are already data.** `ApprovalRequest` and `ApprovalAnswer`
  (`src/policy/approval.ts`) are plain JSON, and `ApprovalChannel`
  (`src/permissions/approvalChannel.ts`) carries them. The terminal prompt
  reads keys through `readLineFromKeys` (`src/ui/keyLineReader.ts`) because the
  terminal is in raw mode during a turn.
- **Events are not yet protocol events.** `AgentVisibilityEvent`
  (`src/agent-core/events.ts`) carries `error: unknown` and has no sequence
  number. Fixing that is phase 3.

## Approach

### Guidance in the runtime

The runtime gains a per-turn guidance queue.

- `AgentStreamOptions` gains `guidance?: GuidanceSource`, an object with
  `drain(): readonly GuidanceMessage[]`. A `GuidanceMessage` is `{ id, text }`.
  The runtime does not own the queue, so a caller with no steering passes
  nothing and behaves as today.
- At the top of each loop iteration, after the previous batch's results are
  committed and before the prompt plan is built, the runtime drains the source.
  Each message is committed to the current turn as a user message through a new
  `AgentContextStore.appendOperatorGuidance(text)`, in queue order, and a
  `guidance_delivered` event is emitted with the message id.
- **Guidance at the final answer (proposal 1).** If the model returns a final
  answer and the source is not empty, the runtime commits the answer, drains
  the guidance, and runs another iteration instead of ending the turn. Input
  typed mid-turn is never left waiting for a turn that has ended. The loop's
  iteration limit still applies.
- Guidance is recorded in the trace as `operator_guidance` with actor `user`,
  the turn identity, and the iteration it was delivered before. The text
  follows the trace's existing capture level for prompt content.

Provider requests then contain a user message directly after tool results.
Every adapter must accept that sequence; see "Checks by risk".

### Interrupt

An interrupt is an abort with reason `"interrupt"`. `"escape"` is kept as an
accepted alias for callers that already pass it.

- **Completed results stay.** Unchanged: they were committed as they finished.
- **Unresolved calls are resolved (proposal 2).** When the abort lands during a
  tool batch, the runtime records a result for the call that was running and
  for each call not yet started, before it emits `turn_cancelled`:
  status `cancelled`, text stating that the operator interrupted it, and for
  the running call that its effects may be partial. This is the rule crash
  recovery already applies; the filler moves into the runtime so both paths use
  it. A late result from the interrupted call is still ignored.
- **An interrupted model step is discarded (proposal 2).** Text streamed in a
  step that did not finish is not committed, because a partial step may hold
  half a tool call. The next request carries a short note, attached to the next
  user message, that the previous response was interrupted.
- **A turn with no entries is still removed**, as today.
- **The next message continues.** A submit after an interrupt starts a new turn
  record. The interrupted turn's messages, results, and the note are in the
  prompt plan like any other history. Nothing is re-executed.
- The interrupt is recorded in the trace as `turn_interrupted` with actor
  `user`, the phase it landed in (`model` or `tool`), and the ids of the calls
  it resolved.

`discardInterruptedTurn` in `AgentExecutionPolicy` stays for callers that want
the old removal; the CLI stops setting it.

### Process groups

`runWithSpawn` starts the shell with `detached: true`, which makes it the
leader of a new process group, and terminates with `process.kill(-pid, sig)`:
`SIGTERM`, then `SIGKILL` after a grace period if the group has not exited.
Abort, timeout, and the output cap all use this path. The grace period is a
constant (2 seconds) in the module, not a setting. The same function serves
`bash` tool calls and operator `!` commands, so both are fixed.

The result is not reported until the group leader has exited, so a cancelled
command does not keep writing after the tool call has returned. Inside the
Docker sandbox the code is the same.

### Commands

New module `src/agent-core/commands.ts`, exported from the `agent-core`
subpath.

```ts
type SessionCommand =
  | { type: "submit"; commandId: string; text: string; images?: string[] }
  | { type: "guide"; commandId: string; text: string }
  | { type: "interrupt"; commandId: string }
  | { type: "answer_approval"; commandId: string; answer: ApprovalAnswer };

type CommandResult =
  | { commandId: string; accepted: true }
  | { commandId: string; accepted: false; code: CommandRejection; message: string };

type CommandRejection =
  | "turn_running"      // submit while a turn runs
  | "no_turn"           // guide or interrupt with no turn running
  | "unknown_approval"  // answer for a request that is not pending
  | "invalid";          // failed validation
```

- `parseSessionCommand(value: unknown)` validates an untrusted value and is
  what a transport calls. Images are base64 strings.
- `commandId` is supplied by the sender and echoed in the result and in the
  events a command causes (`guidance_queued`, `guidance_delivered`), so a
  client can match them.
- There is no session id in a command. A command is dispatched to a session
  object; routing a wire message to the right session is the transport's job
  and arrives with phase 5.
- A `guide` with no turn running is rejected rather than turned into a submit.
  The sender knows which it meant.

### Session controller

New `src/agent-core/session.ts`: `AgentSession`, constructed with a function
that runs one turn (`runTurn(submission, options)`), so it wraps either
`AgentRuntime.streamChat` or the CLI's `Agent.streamChat`.

- `dispatch(command): CommandResult` is synchronous and never throws for a
  well-formed command. `submit` starts the turn and returns; the outcome
  arrives as events.
- `subscribe(listener)` delivers the runtime's events plus the ones this spec
  adds: `guidance_queued`, `guidance_delivered`, `approval_requested`,
  `approval_resolved`. All are JSON-safe. They are not yet numbered; phase 3
  numbers every event.
- It owns, per instance: the guidance queue (the `GuidanceSource` it passes to
  the turn), the turn's `AbortController`, and pending approvals. Nothing is
  module-level.
- It implements `ApprovalChannel`: `request` emits `approval_requested` and
  resolves when an `answer_approval` command with that request id arrives, or
  rejects when the turn is interrupted. The engine's validation of the answer
  is unchanged.
- On interrupt or failure, guidance still queued is returned in the
  `turn_cancelled` / `turn_failed` handling as `undelivered`, so the frontend
  decides what to do with it.

`ApprovalChannel` moves from `src/permissions` to `agent-core` only if the
import direction requires it; otherwise the controller implements the existing
interface structurally.

### Terminal

- `runInteractiveTurn` creates an `AgentSession` around the agent and
  dispatches `submit`. The approval prompt channel is replaced by a subscriber
  that asks the operator on `approval_requested` and dispatches
  `answer_approval`.
- `createTurnCancelListener` is replaced by a turn input reader
  (`src/ui/turnInput.ts`): a one-line editor in the bottom zone that is live
  for the length of a turn (proposal 4). It handles printable keys, paste,
  Backspace, Ctrl+U, and Enter. Enter with text dispatches `guide`. It shares
  key handling with `readLineFromKeys`.
- While an approval is pending, the reader is suspended and its draft kept; the
  approval prompt has the keyboard. When the answer is given the draft is
  redrawn.
- **Queued display.** `guidance_queued` adds a pending line under the active
  tool calls (`queued: <text>`). `guidance_delivered` removes it and writes the
  text into the transcript as an operator message at that point, so the
  transcript reads in the order the model saw.
- **Escape (proposal 3)** dispatches `interrupt` in every state, including with
  a draft and during an approval. When the prompt returns, undelivered guidance
  and the draft are joined and placed in the prompt as editable text. If the
  composer cannot be seeded, they are printed above it.
- A line that starts with `/` or `!` is not sent; a hint says commands run when
  the turn ends, and the line stays in the draft.
- Non-interactive mode has no reader. It dispatches `submit` and, on a signal,
  `interrupt`, and is otherwise unchanged.
- The footer hint during a turn names both controls: type to guide, Escape to
  interrupt.

## Slices

One PR each, in order. Status lives in [delivery.json](delivery.json).

| Slice | Content | Criteria |
| --- | --- | --- |
| `process-group` | Shell commands run in their own process group; abort, timeout, and output cap terminate the group with escalation | a3 |
| `runtime-steering` | Guidance source drained at iteration boundaries, continuation at the final answer, interrupt that resolves unresolved calls, context store method, trace records. No CLI behavior change beyond Escape keeping a well-formed turn. | a1, a2, a8 |
| `session-commands` | `commands.ts`, `AgentSession`, approvals through commands, subpath export, standalone example. The CLI dispatches submit, interrupt, and answer-approval through it with the same keys as before. | a4, a7 |
| `steering-ui` | Turn input reader, queued display, Escape restoring undelivered input, footer hint, README | a1, a5, a6 |

## Checks by risk

| Risk area | Check |
| --- | --- |
| Ordering | Three guidance messages queued across two iterations arrive in order, each before the next provider request; asserted on the messages the fake provider received |
| Guidance at the end | Guidance queued during the final answer produces one more request containing it; with an empty queue the turn ends as before |
| Interruption | Abort during the second of three calls: first result kept, second and third resolved as cancelled, a late result ignored, no tool executed twice across the next turn; abort during a model step; abort while an approval is pending; abort before any entry |
| Well-formed history | After each interruption case, every assistant tool call in the next request has exactly one result |
| Provider sequence | For each adapter in `@propio-ai/providers`, a request whose history has tool results followed by a user message is built without error (request-shape tests against the published package; no live calls) |
| Process group | A command that starts a background child and waits: after cancel, neither the shell nor the child is alive; a child that ignores `SIGTERM` is gone after the grace period; same for timeout |
| Serialization | `JSON.parse(JSON.stringify(command))` deep-equals each command and passes `parseSessionCommand`; malformed values are rejected with `invalid`; a child process sends the commands for one steered turn |
| Isolation | Two `AgentSession` instances in one process: guidance and approval answers sent to one never reach the other; guarded-import test forbids `fs`, `process`, `readline`, `net`, and application imports from the new modules |
| Terminal | Key-level tests with a fake input stream: typing during a turn, Enter queues, pending line shown then moved, Escape with a draft restores it, approval prompt suspends and restores the draft, narrow width |
| Regression | Existing cancellation, recovery, approval, and non-interactive tests pass; where a test asserted the old Escape removal, it is updated in the slice that changes it and named in the PR |

Repository checks for every slice: `npm test`, `npm run build`,
`npm run format:check`, `npx fallow audit`.

## Cross-repository changes

| Repository | Change |
|------------|--------|
| propio-agent | All four slices. |

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| An adapter rejects or mangles a user message that follows tool results | Request-shape test per adapter in `runtime-steering`. If one fails, stop and raise it: the fix belongs in `propio-providers`, which this spec does not select |
| The model treats guidance as a new task and drops the current one | Guidance is committed as a user message with a one-line lead-in saying it was sent while the work was in progress; wording is in one place and covered by a test |
| Mid-turn input and the approval prompt fight over stdin | One owner at a time: the reader suspends on `approval_requested`; tested at key level |
| Redrawing the input line corrupts streamed output | The reader draws only in the bottom zone the retained renderer already manages; phase 3 reworks that zone, so the reader's surface is kept small |
| Killing a process group kills more than intended | The group is created by this spawn and contains only its descendants; `detached` is never combined with `unref` |
| `src/agent.ts` and `src/index.ts` grow again | The controller lives in `agent-core` and the reader in its own UI module; `index.ts` only wires them |
| The command set is designed without a real second client | It is the minimum the terminal needs; the spike (phase 5) is expected to change it, and nothing is published as stable |

## Alternatives considered

- **Cancel and resubmit instead of guidance.** Rejected: it discards the
  running step and is what the audit found inadequate.
- **Deliver guidance by interrupting the current tool.** Rejected: the roadmap
  asks for delivery at the iteration boundary without cancelling. Escape exists
  for the other case.
- **Queue mid-turn input as the next turn's message.** Rejected as the default:
  the operator's point is to change what the model does now. Proposal 1 keeps
  the two cases from diverging.
- **Reuse the prompt composer during a turn.** Rejected for this phase: it owns
  a readline interface, history, and typeahead, and phase 1 already found it
  could not run in the raw-mode terminal a turn needs.
- **Put the queue inside `AgentRuntime`.** Rejected: the CLI builds a runtime
  inside `Agent`, where the frontend cannot reach it. A source passed in lets
  the frontend own the queue and keeps the runtime a consumer of it.
- **Commands as methods (`session.guide(text)`).** Rejected: a method cannot be
  sent from a browser. A typed value with a dispatcher can, and methods can
  still wrap it.
