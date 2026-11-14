# Design: tool-call-rendering

## Overview

Readable tool calls from a typed display payload, and the serializable,
numbered event half of the session protocol.

The order is the roadmap's: fix the data model, then the views. A tool
describes its call as data; the runtime carries that on the events it already
emits; the terminal draws it. The approval prompt and a replay draw the same
data, which is what makes them match.

## What exists at the baseline

`propio-agent` at `559caa7` (after `turn-steering`).

- **Two strings.** `ToolCallView` (`src/ui/toolCallView.ts`) is id, tool
  name, status, `useLabel`, `resultLabel`. A finished call is drawn as
  `useLabel — resultLabel` on one line (`TerminalUi.appendToolCallTranscriptEntry`,
  `src/ui/terminal.ts`; `renderToolCallViewText`, `src/ui/replRenderer.ts`).
- **Presentation hangs off the tool.** `PresentedTool`
  (`src/tools/interface.ts`) adds `getInvocationLabel` and
  `getDisplayAdapter` to the execution contract; the adapter
  (`src/tools/displayAdapter.ts`) returns strings. `ToolRegistry`
  (`src/tools/registry.ts`) falls back to the first 120 characters of the
  result.
- **Labels are made twice.** The runtime emits `tool_started` with
  `useLabel: null` and `tool_finished` / `tool_failed` with a raw preview
  (`src/agent-core/runtime.ts`, `processToolCall`). `Agent.formatRuntimeEvent`
  (`src/agent.ts`) rewrites both through the registry before the CLI sees
  them.
- **Events carry values that are not JSON.** `turn_failed` has
  `error: unknown`; tool events carry `args` as given
  (`src/agent-core/events.ts`). `AgentSession` (`src/agent-core/session.ts`)
  passes a turn's events through unchecked and numbers nothing.
- **`tool_started` precedes authorization.** It is emitted before
  `runToolWithAbort`, which is where policy asks. A payload on `tool_started`
  is therefore available when the approval question is drawn.
- **Structured outcomes exist but are not shown.** `ToolExecutionOutcome`
  (`src/tools/types.ts`) has exit code, duration, classification, and file
  hashes. It reaches the trace and not the terminal.
- **No output until exit.** `runWithSpawn` (`src/tools/runShellCommand.ts`)
  collects stdout and stderr and returns them when the command ends.
  `ToolExecutionContext` (`src/tools/execution.ts`) has only `signal`.
- **Layout depends on a flag.** With thinking visible, tool views are
  appended to the transcript; otherwise they are upserted in the bottom zone
  (`src/ui/assistantTurnRenderer.ts`). The bottom zone draws only the last
  view (`lastMapValue`, `src/ui/replRenderer.ts`).
- **The approval prompt** (`src/ui/approvalPrompt.ts`) shows the command or
  path from the request's policy target, or 400 characters of argument JSON.

## Approach

### Display payload

New module `src/tools/display.ts`, exported from the `tools` subpath. Types
only, plus pure functions.

```ts
type ToolDisplay = {
  readonly title: string;          // "edit src/a.ts", "bash", "github: create_issue"
  readonly body: ToolDisplayBody;
};

type ToolDisplayBody =
  | { kind: "diff"; path: string; operation: "create" | "replace";
      hunks: readonly DiffHunk[]; added: number; removed: number;
      truncated: boolean }
  | { kind: "command"; command: string; cwd?: string;
      exitCode?: number; classification?: CommandOutcomeClassification;
      outputTail?: string; outputLines?: number; truncated: boolean }
  | { kind: "file_read"; path: string; lines?: number;
      range?: { start: number; end: number } }
  | { kind: "search"; pattern: string; scope?: string;
      matches?: number; files?: number; sample?: readonly string[] }
  | { kind: "generic"; fields: readonly { key: string; value: string }[];
      resultPreview?: string; truncated: boolean };

type DiffHunk = {
  oldStart: number; newStart: number;
  lines: readonly { op: " " | "+" | "-"; text: string }[];
};
```

- Everything is a string, number, or boolean, so the payload is JSON by
  construction. A test asserts it against `JsonValue` from `policy`.
- Sizes are capped where the payload is built: a diff at 400 lines, an
  output tail at 200 lines and 16 KB, a generic value at 2,000 characters.
  `truncated` says the cap applied. The full result is still what the model
  receives; the payload is for people.
- Status and timing are not in the payload. They are on the event (below),
  because the runtime knows them and the tool does not.

### How tools produce it (proposal 1)

`PresentedTool` loses `getInvocationLabel` and `getDisplayAdapter` and gains
two optional members:

```ts
describeCall?(args, context): ToolDisplay | Promise<ToolDisplay>;
describeResult?(args, result: ToolExecutionResult, before: ToolDisplay): ToolDisplay;
```

- `describeCall` runs before authorization. It must have no side effects. It
  may read: `edit` and `write` read the target file and compute the diff the
  call would produce, using the same replacement code `execute` uses. A path
  the policy would deny or ask about is still read for the preview only when
  the file tools' own confinement allows the read; otherwise the payload is
  a diff with no hunks and the path.
- `describeResult` runs after execution and fills in what only the result
  knows: exit code and output tail, match counts, line counts. For `edit`
  and `write` it returns the preview diff unchanged on success.
- Both are wrapped: a throw, or a `describeCall` slower than 250 ms, yields
  the generic payload. A display failure never fails a call.
- `ExecutableTool` (`src/tools/execution.ts`) is not touched. The registry
  that executes never calls either member (a8).
- A tool with neither member gets `genericDisplay(name, args, result)`: one
  field per top-level argument, values stringified and capped. MCP tools get
  a title of `server: tool` from the MCP manager and the generic body.
- The diff is computed by a small line-diff function in `src/tools/`
  (Myers, line-based, three lines of context). No new dependency.

Per tool:

| Tool | Kind | Before | After |
| --- | --- | --- | --- |
| `edit`, `write` | `diff` | hunks from the file as it is now | same; on failure, the error |
| `bash` | `command` | command, cwd | exit code, classification, tail |
| `read` | `file_read` | path, requested range | line count |
| `grep`, `find`, `ls` | `search` | pattern, scope | match and file counts, first 5 |
| `skill`, MCP, others | `generic` | arguments | result preview |

### On events

`tool_started`, `tool_finished`, and `tool_failed` gain `display: ToolDisplay`.
`tool_finished` and `tool_failed` gain `durationMs`. The runtime gets the
payload from a new integration, `describeTool`, with the two functions above;
the default is the generic payload. `Agent` supplies the registry's and the
MCP manager's. `Agent.formatRuntimeEvent` stops rewriting labels.

`activityLabel`, `useLabel`, `resultPreview`, and `argumentPreview` are
removed from the events once `call-renderers` no longer reads them.
`display.title` replaces the first two.

### Rendering

New `src/ui/toolDisplay/`: one pure function per kind,
`render(display, state, width, mode) => string[]`, where `state` is
`running | success | error` plus duration, and `mode` is `collapsed` or
`expanded`. Pure functions are what the snapshot tests call (a5).

Collapsed (proposal 2):

- `file_read`, `search`, `generic`: one line. `read src/a.ts · 214 lines`,
  `grep "foo" in src · 12 matches in 4 files`.
- `diff`: a header line (`edit src/a.ts · +3 −1`) and up to 11 hunk lines,
  then `… 27 more lines`.
- `command`: a header (`$ npm test · exit 1 · 12.4s`) and the last lines of
  output up to 11, then the hidden count. A command that succeeds with no
  output is one line.
- An error always shows its first line under the header.

A ten-call turn is therefore at most 120 lines, and ten reads are ten lines
(a3). Every line is fitted to the width in cells
(`src/ui/displayWidth.ts`) and passed through `visibleText` (a9). Diff lines
are colored by op; a `+` or `-` that came from file content cannot be
mistaken for a header because headers are drawn in a different column and
style, and the approval question is always drawn last, after a rule.

### Layout (a4)

One path replaces `appendToolCallView` / `upsertToolCallView`:

- **In flight:** the call is a bottom-zone entry. The zone draws every
  running call, oldest first, each collapsed. With sequential execution this
  is one entry; the renderer does not assume that.
- **Finished:** the entry leaves the bottom zone and its collapsed rendering
  is appended to the transcript, in the position the model's output has
  reached. It is never redrawn.
- Thinking visibility no longer selects between two paths. Visible thinking
  is flushed and closed before a finished call is appended, as it is today.
- `showToolCalls` off keeps today's single "Running tool" status and appends
  nothing (proposal 6).
- Plain and non-TTY modes have no bottom zone: a start line is written when
  the call starts and the collapsed rendering when it finishes. JSON mode
  writes nothing, as today.

### Expand (proposal 3)

The terminal keeps the payload and state of the last finished call that was
drawn collapsed with something hidden. `/expand` and Ctrl+O at the prompt
print its expanded rendering as a new transcript entry: the whole capped
payload, and for a result stored externally, the path of the full output.
With nothing to expand they say so. Neither is available while a turn runs;
the mid-turn line editor accepts only guidance.

### Approval prompt (a1)

The runtime passes its existing preview into authorization. The application's
`ApprovalRequest` envelope (`agent-core/approval.ts`) extends the policy request
with optional `display?: ToolDisplay`; permissions attaches it only when asking.
The session forwards this envelope unchanged. This replaces the original CLI-side
map after review: each frontend gets the same preview, without visibility-event
forwarding, call-ID correlation, or eager copies. The policy request and engine
remain independent of presentation types.

The prompt always retains authoritative operation details, including generic/MCP
arguments, the resolved file path, or the full command/cwd/environment. Only diff
bodies need an extra rendered preview; command and generic headers would repeat
or hide these details. The terminal temporarily hides only the matching running call while the
approval block is open. Its running state is retained; prompt cleanup restores
visibility only if the call still exists. Other in-flight calls stay visible. Disposing the answering channel denies every pending request
before aborting its UI so neither the tool nor the session can wait forever.

`formatApprovalRequest` renders the payload collapsed, with a larger cap for
a diff (40 lines), above the reason and the choices. Without a payload it
falls back to today's lines. The operator sees the same hunks before
answering that the transcript shows afterwards. If the file changed between
preview and execution, the tool's own match check fails as it does today and
the failure is what is shown after.

### Live output (a2)

- `ToolExecutionContext` gains `onOutput?(chunk: { stream: "stdout" |
  "stderr"; text: string }): void`. This is an execution concern, not a
  presentation one: the tool reports what the process wrote.
- `runWithSpawn` calls it as data arrives, after decoding and before the
  buffer cap. `BashTool` passes it through. Nothing else uses it yet.
- The runtime turns chunks into `tool_output` events (`toolCallId`, `stream`,
  `text`), coalesced to at most one per 100 ms per call and 4 KB per event.
  Excess text within a window is dropped from the event, not from the
  result, and the event says how much.
- The bottom-zone entry for a running command shows the last 5 lines
  received and the elapsed time. Output goes through `visibleText`, and
  through the turn's holdable stream so it waits while the operator types.
- `tool_output` is transient (proposal 4): it is numbered like any event,
  carries `transient: true`, and a consumer replaying a log may skip it. The
  finished call's payload has the tail.

### Protocol events (a6)

New `src/agent-core/protocol.ts`.

```ts
type ProtocolEvent = { readonly seq: number; readonly event: SessionEventBody };
```

- `SessionEventBody` is the union of the session's own events and a JSON
  form of each turn event. `toProtocolEvent` converts: `error: unknown`
  becomes `{ name, message }`; `args` becomes a `JsonObject` (values that
  are not JSON are replaced by their string form and counted);
  `prompt_plan_built` is reduced to its numeric summary. The runtime's event
  types are otherwise unchanged; conversion happens at the session boundary.
- `AgentSession` numbers every event it delivers, starting from
  `options.firstSequence ?? 1`, increasing by one, with no gaps. Numbering is
  per instance (proposal 5). `subscribe` listeners receive `ProtocolEvent`.
- `AgentSession` takes an optional `eventLog: { append(event): void }`. An
  in-memory implementation with `after(seq)` ships in `agent-core` for tests
  and the spike. A durable one is `session-stores`.
- `parseProtocolEvent(value: unknown)` validates an untrusted value, for a
  client in another process.
- In one process the CLI still receives the original error object and
  rendered result directly, as `turn-steering` left it.

### Replay (a7)

The terminal's turn rendering is driven by a function of protocol events:
`renderTurnEvents(events, ui, visibility)`. Live, the CLI feeds it events as
they arrive. A test records a turn's log, JSON-encodes it, decodes it, feeds
it to a fresh terminal of the same width, and compares the transcript text.
Transient events and the bottom zone are excluded from the comparison;
streamed assistant text is compared after it has been flushed. The scenario
has an edit with approval, a failing command with live output, three reads,
an MCP call, mid-turn guidance, and a denied call.

## As implemented in `display-payload`

Where this list and "Approach" disagree, this list is current.

- **Shape.** `ToolDisplay` is `{ title, body, error? }` in
  `src/tools/display.ts`. `title` is the activity phrase ("Editing
  src/a.ts"), so it replaces the old invocation label exactly. `error` is
  set when the call failed.
  - `command` has `stdoutTail` and `stderrTail` with `stdoutLines` and
    `stderrLines`, not one `outputTail`: the shell runner collects the
    streams separately.
  - `search` has `mode` (`content`, `files`, `list`), so one body serves
    `grep`, `find`, and `ls`.
  - `file_read.range` is `{ start, count? }`.
  - `diff` adds `baseHash`, `stale`, and `unavailable`.
- **Describing.** `describeCall(args, context)` and
  `describeResult(args, result, before)` on `PresentedTool`
  (`src/tools/interface.ts`). `context.canPreviewRead(rawPath)` is how the
  caller limits preview reads. The runtime integrations are
  `describeToolCall` and `describeToolResult` on `AgentIntegrations`.
- **Preview reads follow read policy.** `Agent` answers `canPreviewRead`
  yes only when `read` is enabled, is in the tool scope the call will be
  authorized against (passed to `describeToolCall` as `scope`), and
  `ToolPermissions.allowsWithoutAsking` allows a `read` of that path. It
  never prompts and is not recorded as the last decision (review of #110). Where a read would
  ask or be denied, the payload has no hunks and
  `unavailable: "Not read before approval"`. In `bypass` every file may be
  previewed.
- **Stale previews.** The finished payload keeps the preview's hunks only
  if `baseHash` equals the `beforeHash` the tool recorded when it ran.
  Otherwise it has no hunks and `stale: true`.
- **No preview** for a binary file, a directory, or a file over 1 MB. An
  edit that would fail (string not found, ambiguous match) says so in
  `unavailable` before the call runs.
- **Line breaks are compared.** Lines are compared with their line breaks;
  a last line without one is marked `noNewline`, so gaining or losing the
  final newline shows as `-1 +1`. Carriage returns stay in the line (review
  of #110).
- **Byte budgets.** Diff text is capped at 64 KB of UTF-8 across all hunks
  (`DISPLAY_LIMITS.diffBytes`); a line over what is left is cut at a
  character boundary and marked `truncated`. The command tail is 16 KB of
  UTF-8, not of UTF-16 units. Trailing newlines are trimmed by a backward
  scan (review of #110).
- **Detached copies.** The describe hooks receive `structuredClone`d
  arguments, result, and earlier description, and a copy of the tool scope
  with its own set and copied metadata (metadata that cannot be copied is
  left out). Presentation code cannot change what is authorized, run, or
  recorded (review of #110).
- **The budget is measured, not only raced.** A description is accepted
  only if it arrived within 250 ms of monotonic time, since the budget
  timer cannot fire while a hook blocks the event loop. The timer is set
  for what is left of the budget after the hook returns, so work before its
  first await counts (review of #110).
- **The diff search has a deadline.** Previews give it 50 ms; past it the
  differing middle is shown as one replacement, which is still a correct
  diff. The diff works only on the changed region and its context. A 1 MB
  worst case (500,000 alternating lines) takes about 130 ms, down from
  560 ms (review of #110).
- **Diff limit.** Past an edit distance of 1,000 lines the differing middle
  is shown as one replacement.
- **A nonzero exit is a result, not an error.** `error` is set on a
  `command` only when the call itself failed: cancelled, timed out, or
  refused before it ran.
- **Labels.** `displayUseLabel` and `displayResultLabel` in `display.ts`
  derive the two strings the terminal still draws; `Agent.formatRuntimeEvent`
  uses them. A finished `edit` or `write` now reads `Changed (+3 -1)` or
  `Created (+12 -0)`. `activityLabel`, `useLabel`, `resultPreview`, and
  `argumentPreview` stay on the events until `call-renderers`.
- **`durationMs`** covers the tool's execution only and is 0 for a call that
  was denied or never ran.
- **Not done.** No tool event for a call resolved as interrupted, as before.
  Line counts for `read` are of the text returned to the model, which for a
  result stored externally is the preview.

## As implemented in `call-renderers`

- `src/ui/toolDisplay/render.ts` renders five kinds from `ToolDisplay`.
  `ToolCallDisplay` carries the payload and runtime status; the old label view
  and temporary label conversion exports are removed.
- Completion events optionally carry `fullOutputPath`; expansion prints that
  escaped path without reading the external file.
- Ctrl+O expands; Ctrl+Y now toggles tool visibility. `/expand` is an idle
  command. Ctrl+O clears and restores the prompt layout without losing input.
- Failed reads/searches/generic calls use a second error line. Diff/command
  collapsed output remains at most twelve lines including error/hidden counts.
- Completed diffs are colored; plain output remains unstyled. Expanded text
  wraps using the shared grapheme-aware width functions.
- Real terminal testing exposed a pre-existing bottom-zone clear off-by-one:
  newline-terminated entries leave the cursor on an empty row, which must also
  be cleared. A regression test and a repeated tmux capture verify the fix.

## Slices

One PR each, in order. Status lives in [delivery.json](delivery.json). The
owner named all four effects as disruptive, so the three slices that fix
them come first and the protocol work, which changes nothing visible, last.

| Slice | Content | Criteria |
| --- | --- | --- |
| `display-payload` | `display.ts`, the diff function, `describeCall` / `describeResult` on every built-in tool, generic fallback and MCP titles, `describeTool` integration, `display` and `durationMs` on tool events. Labels are still drawn, now derived from the payload. | a8 |
| `call-renderers` | Per-kind renderers with snapshots, the single layout, bottom zone for all calls in flight, `/expand` and Ctrl+O, removal of `ToolCallView`, the display adapter, and the label fields. README. | a1, a3, a4, a5, a9 |
| `approval-display` | Carry `display` on the application approval envelope; the prompt renders the diff and retains operation details. | a1, a9 |
| `live-output` | `onOutput` in the execution context and shell runner, `tool_output` events, live tail in the bottom zone through the hold. | a2 |
| `protocol-events` | `protocol.ts`, conversion, numbering, in-memory log, parser, event-driven turn rendering, replay test, standalone example. | a6, a7 |

## Checks by risk

| Risk area | Check |
| --- | --- |
| Payload shape | Each built-in tool: `describeCall` then `describeResult` for a success and a failure; every payload deep-equals its JSON round trip; caps apply and set `truncated` |
| Diff correctness | Property test: applying the hunks to the old text gives the new text, for random line edits, empty files, no trailing newline, CRLF, and `replace_all`; the previewed diff equals the diff of the file before and after the real edit |
| Preview is read-only | `describeCall` for `edit` and `write` leaves file content and mtime unchanged; a path outside what file tools may read yields no hunks; a throwing or slow describe yields the generic payload and the call still runs |
| Boundary | `display.ts` and the diff function import nothing outside `src/tools` and policy types, and reference no process, filesystem, clock, or module-level mutable state; `ExecutableTool` has no display member (type-level test); `tools` and `agent-core` import nothing from `src/ui` |
| Renderers | Snapshots for five kinds × running, success, error × 40 and 120 columns, collapsed and expanded; wide characters and a line longer than the width; no line exceeds the width in cells |
| Bounded output | Ten calls of each kind with large results: line count at or under the stated bound; `/expand` prints the hidden lines |
| Layout | The same event sequence with thinking shown and hidden gives the same tool-call lines; two calls in flight both appear in the bottom zone; a finished call appears once in the transcript |
| Hostile text | A file line, command output, MCP argument, and tool title containing cursor moves, erase sequences, OSC links, and a fake "needs approval" block: the rendered text has no control sequences beyond the renderer's own styling, in the transcript and in the prompt |
| Approval | An edit in `ask` mode: the prompt contains the hunk lines before the answer; after allow, the transcript has the same lines; after deny, no file change |
| Live output | A real command printing a line every 100 ms: `tool_output` events arrive before the result; a flood of output is coalesced and the event count bounded; output received while a guidance line is typed appears after it is sent; cancel mid-output leaves no stray lines |
| Serialization | Every event of a full turn, including a failed turn and a thrown non-Error, deep-equals its JSON round trip and passes `parseProtocolEvent`; sequence numbers are 1..n without gaps; two sessions number independently; `firstSequence` is honored |
| Replay | The scenario under "Replay" rendered live and from the decoded log gives equal transcript text at 80 columns |
| Regression | Existing approval, steering, cancellation, plain-mode, and JSON-mode tests pass; a test that asserted an old label is updated in the slice that changes it and named in the PR |

Thresholds: `describeCall` budget 250 ms; live output at most 10 events per
second per call; collapsed bound 12 lines for `diff` and `command`, 1 for the
rest.

Repository checks for every slice: `npm test`, `npm run build`,
`npm run format:check`, `npx fallow audit`. `call-renderers`,
`approval-display`, and `live-output` are also tried in a real terminal with
the tmux method in [turn-steering/tasks.md](../turn-steering/tasks.md).

## Cross-repository changes

| Repository | Change |
|------------|--------|
| propio-agent | All five slices. |

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| The preview diff differs from what the edit does | Both use one replacement function; a test compares the preview with the diff of the real before and after |
| A preview read leaks a file the operator would have denied | The preview obeys the file tools' read confinement, and its content is shown only to the operator, never returned to the model |
| Richer output gives model and tool text more room to spoof the terminal | Every renderer ends in `visibleText`; hostile-text checks cover transcript and prompt; the question is drawn after a rule the payload cannot produce |
| Live output fights the guidance line and the spinner | Output is written only through the retained view and its holdable stream; tried in tmux at the bottom row |
| Removing label fields breaks a consumer of the `agent-core` subpath | The subpaths are provisional and versioned with the package; the removal is a `feat!` commit and is listed in the PR |
| Converting events at the session boundary drifts from the runtime's types | `toProtocolEvent` is exhaustive over the union, so a new runtime event fails the build until it is handled |
| `call-renderers` grows too large to review | The renderers are pure and land with their snapshots first in the PR; layout is a second commit. If review asks, expand is split into its own slice and the plan is updated |
| Event rendering refactor in the last slice changes what earlier slices drew | The replay test and the earlier slices' snapshots run against it; no snapshot is updated in that slice |

## Alternatives considered

- **Put the display payload on `ToolExecutionResult`.** Rejected: the
  roadmap keeps the execution contract presentation-free, and a payload is
  needed before the call runs.
- **Let the CLI compute diffs from arguments.** Rejected: the terminal would
  have to know each tool's semantics, and a browser client would need the
  same code again.
- **Compute the diff from the before and after hashes already recorded.**
  Rejected: hashes hold no content, and nothing exists before approval.
- **Carry the payload in `ApprovalRequest`.** Rejected: `policy` would import
  the tools' display types. Matching by `toolCallId` at the frontend needs no
  new dependency.
- **Stream every output chunk as a durable event.** Rejected: a build log
  would dominate the event log. The tail on the finished payload is what a
  replay needs.
- **Expand in place by redrawing the transcript.** Rejected: the renderer
  appends to scrollback and cannot rewrite it. Revisit only if printing
  proves inadequate, as the roadmap says of the renderer in general.
- **Number events in the runtime.** Rejected: the session adds its own
  events between the runtime's, and one counter must cover both.
