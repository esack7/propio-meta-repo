# Requirements: tool-call-rendering

## Summary

Make tool calls readable in the terminal by carrying a typed display payload
on tool events, and finish the event half of the session protocol: every
event is plain JSON and numbered.

This is phase 3 of the roadmap in
[maturity-audit-roadmap/design.md](../maturity-audit-roadmap/design.md). The
problem is finding 3 of
[maturity-audit-roadmap/audit.md](../maturity-audit-roadmap/audit.md): a tool
call is flattened to two strings before it reaches the renderer, so the
terminal shows one truncated line per call. The owner confirmed the finding
from daily use on 2026-11-13 and named all four of its effects as disruptive:
no diff on `edit` and `write`, no output while `bash` runs, results cut to one
line with no way to expand, and a layout that shows only the latest call in
flight and changes with thinking visibility.

## Goals

- Tools describe each call as a typed display payload: kind (`diff`,
  `command`, `file_read`, `search`, `generic`), structured fields, timing,
  and status. The runtime forwards it on tool events; the CLI renders it.
  The execution contract stays free of presentation.
- `edit` and `write` show the changed lines, before approval and after
  completion.
- `bash` shows its output while it runs, then exit status and duration.
- Reads and searches collapse to a summary. MCP tools get a generic key/value
  view. The last collapsed result can be expanded.
- One layout whatever the visibility flags. Completed calls stay in the
  transcript; the bottom zone shows every call in flight.
- The approval prompt renders the same payload it is asking about.
- Every event is JSON-serializable, including display payloads and errors,
  and carries a per-session sequence number. A turn rendered from a replayed
  event log matches the turn rendered live.

## Non-goals

- A durable event log, `--continue`, and `--resume` (`session-stores`,
  phase 8). This spec keeps the log in memory and proves replay on it.
- A transport. Events are delivered in-process; HTTP is `chat-server-spike`
  (phase 5).
- Running tool calls concurrently or in the background (`tools-hardening`,
  phase 11). The bottom zone can show several calls in flight, but the
  runtime still runs them one at a time.
- New tools, or changes to what a tool returns to the model.
- Replacing the hand-written renderer, or redrawing scrollback. Expanding a
  result prints it; it does not rewrite lines already scrolled.
- Changing what the approval prompt offers. Only what it shows about the
  operation changes.
- Syntax highlighting inside diffs and command output.
- Trace commands and cost display (`trace-commands`, phase 4).

## Acceptance criteria

IDs match [delivery.json](delivery.json).

- [ ] **a1** An `edit` or `write` shows the changed lines before approval and
      after completion.
- [ ] **a2** A long-running command shows its output while it runs, and its
      exit status and duration when it ends.
- [ ] **a3** A turn with ten tool calls occupies a bounded number of lines
      until expanded, and the last collapsed result can be expanded in full.
- [ ] **a4** Rendering of tool calls is identical with thinking output shown
      or hidden. Completed calls stay in the transcript; the bottom zone
      shows every call in flight.
- [ ] **a5** Snapshot tests cover each renderer (`diff`, `command`,
      `file_read`, `search`, `generic`), running, succeeded, and failed, at a
      narrow and a wide terminal width.
- [ ] **a6** Every event, including display payloads and errors, survives a
      JSON round trip and carries a per-session sequence number that
      increases by one.
- [ ] **a7** A turn rendered from a replayed event log matches the turn
      rendered live.
- [ ] **a8** Tools produce the payload, the runtime forwards it, and the CLI
      renders it. The execution contract has no presentation member. The
      payload contract holds no module-level state and passes a
      guarded-import test. A tool that supplies no payload, such as an MCP
      tool, gets a generic one.
- [ ] **a9** Text that came from the model or a tool cannot move the cursor,
      erase lines, or imitate the approval question in any renderer.

## Constraints from other phases

- Events, like commands and approval requests, must survive a JSON round
  trip. No primitive may hold process-level state.
- `agent-core` may import `context`, `tools`, `policy`, and provider and
  trace types. `tools` imports only `policy` and provider types. Neither
  imports from the CLI or `src/ui`.
- Phase 1 made every field shown in the approval prompt visible text
  (`src/ui/visibleText.ts`). A richer prompt must keep that property (a9).
- Phase 2 holds the turn's output while the operator types a guidance line
  (`src/ui/holdableStream.ts`). Live command output must go through the same
  hold.

## Affected repositories

<!-- Confirmed names are listed in repos.txt -->

`propio-agent`, as named for this phase in the roadmap and confirmed on
2026-11-13.

## Open questions

The roadmap section is a brief; [design.md](design.md) settles what it left
open. The owner asked on 2026-11-13 to proceed as for `turn-steering`, so the
design's proposals are implemented as written and are open to correction in
review of each pull request:

1. A tool describes a call before it runs through an optional, read-only
   preview step. For `edit` and `write` that step reads the file to compute
   the diff the approval prompt shows.
2. Collapsed sizes: one line for a read, a search, or a generic call; at most
   12 lines for a diff or a command's output, with a count of what is hidden.
3. Expanding is a command at the prompt (`/expand`, and Ctrl+O) that prints
   the last collapsed result in full. It is not available mid-turn.
4. Live output events are numbered but marked transient: a replay may skip
   them, and the finished call's payload carries the output tail.
5. The protocol's sequence number is its own per-session counter. Sharing
   numbering with the trace journal, which the roadmap asks for, waits for
   `session-stores`, where the log becomes durable.
6. Hiding tool calls (`showToolCalls` off) stays as an option, and is the one
   visibility flag that still changes what is drawn.
