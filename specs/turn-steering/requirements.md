# Requirements: turn-steering

## Summary

Redirect a running turn without cancelling it, and express operator input as
the typed commands of the session protocol.

This is phase 2 of the roadmap in
[maturity-audit-roadmap/design.md](../maturity-audit-roadmap/design.md). The
problem is finding 2 of
[maturity-audit-roadmap/audit.md](../maturity-audit-roadmap/audit.md): during a
turn the terminal listens for one key, Escape, and Escape cancels. Phase 1
(`tool-permissions`) added the first other control, denying a tool call with a
reason. This phase adds the rest: typing guidance while the turn runs, and an
interrupt that keeps the work already done.

## Goals

- Accept typed input while a turn runs and deliver it to the model at the next
  iteration boundary as operator guidance, without cancelling the turn.
- Escape interrupts the current model step or tool and returns to the prompt.
  Completed tool results stay in context, and the next message continues from
  them.
- Show queued input in the transcript so the operator can see what is pending
  and when it was delivered.
- Cancelling a running `bash` command terminates everything it started, not
  only the shell.
- Express submit, guide, interrupt, and answer-approval as typed,
  JSON-serializable commands. The terminal issues them; nothing in
  `agent-core` reads keys.
- Record guidance and interrupts in the trace with actor `user`.

## Non-goals

- The event half of the protocol: serializable, sequence-numbered events and
  the display payload (`tool-call-rendering`, phase 3). This spec adds only the
  events steering needs and keeps them JSON-safe.
- Start-session and resume-session commands, the event log, and restoring
  queued input on resume (`session-stores`, phase 8).
- A transport. Commands are dispatched in-process; HTTP is `chat-server-spike`
  (phase 5).
- Slash commands, `!` shell commands, history search, and typeahead while a
  turn runs. Mid-turn input is guidance only.
- Running tool calls concurrently or in the background (`tools-hardening`,
  phase 11).
- Changing what the approval prompt offers. Its answer travels as a command;
  its choices stay as phase 1 left them.
- Changing SIGINT. Ctrl+C still ends the session.

## Acceptance criteria

IDs match [delivery.json](delivery.json).

- [ ] **a1** Input submitted mid-turn reaches the model before its next
      request, in the order it was submitted.
- [ ] **a2** Interrupting during a tool call leaves completed results in
      context and does not replay them; the next request is well-formed, with
      a result for every tool call the model made.
- [ ] **a3** Cancellation of a running `bash` command terminates its process
      group.
- [ ] **a4** Every command survives a JSON round trip, and a headless test
      drives a full steered turn (submit, guide, deny an approval with a
      reason, interrupt, submit again) with commands alone.
- [ ] **a5** In the terminal, the operator can type while a turn runs; queued
      input is shown as pending until it is delivered and then appears in the
      transcript where the model received it.
- [ ] **a6** Escape returns to the prompt without ending the session, and
      input typed or queued but not yet delivered is not lost.
- [ ] **a7** The command contract and session controller read no keys, hold
      no module-level state, and pass a guarded-import test; two sessions in
      one process do not see each other's queued input or approvals.
- [ ] **a8** Each delivered guidance message and each interrupt appears in the
      trace with actor `user`.

## Constraints from later phases

- Commands, like approval requests, must survive a JSON round trip. Images in
  a submit command are therefore strings, not byte arrays.
- No primitive may hold process-level state.
- `agent-core` may import `context`, `tools`, `policy`, and provider and trace
  types. It imports nothing from the CLI.

## Affected repositories

<!-- Confirmed names are listed in repos.txt -->

`propio-agent`, as named for this phase in the roadmap and confirmed on
2026-11-13.

## Open questions

The roadmap section is a brief; [design.md](design.md) settles what it left
open. The owner asked on 2026-11-13 to proceed as for `tool-permissions`, so
the design's proposals are implemented as written and are open to correction
in review of each pull request:

1. Guidance that arrives as the model gives its final answer continues the
   turn instead of waiting for the next one.
2. An interrupted model step is discarded from context; calls that were
   running or not yet started get an "interrupted" result.
3. Escape always interrupts. Undelivered input goes back into the prompt for
   editing instead of being sent.
4. Mid-turn input is a one-line editor without history, typeahead, or
   commands.
