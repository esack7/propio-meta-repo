# Tasks: tool-call-rendering

Delivery status, dependencies, PRs, and commit-specific evidence live in
[delivery.json](delivery.json). Requirements own acceptance descriptions; the
record maps stable criterion IDs to reviewable slices. Avoid duplicate status lists.

Before implementation, fill the delivery record with the approved scope and working
agreement. Define checks for the risks relevant to each slice in the design.

At review handoffs and merges, reconcile the delivery record and run `spec-status`.
Report completed slice, evidence, remaining scope, next action, and decision needed.
Use `start-slice` to continue authorized work. Run normal `close-spec` only after all
slices and criteria are verified; worktree cleanup alone does not complete a spec.

## Resuming (updated 2026-11-13)

Planned, nothing started. Five slices in order: `display-payload`,
`call-renderers`, `approval-display`, `live-output`, `protocol-events`. See
"Slices" in [design.md](design.md).

**Working agreement** (also in [delivery.json](delivery.json)): implement the
slices in order and fix in-scope review findings; commit, push, and open each
PR without asking again; ask before merging or publishing. The design's six
proposals were not reviewed before implementation and are listed under "Open
questions" in [requirements.md](requirements.md); expect corrections in review.

**Owner review of finding 3** (2026-11-13): confirmed from daily use. All
four effects were named as disruptive, so none is deferred within this spec.

**Practical notes** are in
[turn-steering/tasks.md](../turn-steering/tasks.md): signed commits, the two
flaky suites, inline review comments, a failing-first test for each review
fix, and how to try the CLI in tmux against a stand-in model.
