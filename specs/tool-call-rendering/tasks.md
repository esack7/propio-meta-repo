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

## Resuming (updated 2026-11-14)

`display-payload` merged as propio-agent#110 and is verified.
`call-renderers` is implemented and ready for review in propio-agent#111
at `666bab5`. All local checks pass (149 suites, 2,691 tests, 60 snapshots),
and the CLI was verified in tmux. Await review/merge, then reconcile delivery
before starting `approval-display`; `live-output` and `protocol-events` follow.
See [delivery.json](delivery.json) for criterion-specific evidence.

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

## Baseline checks (2026-11-13, Node 22.23.3)

Run in `specs/tool-call-rendering/repos/propio-agent` at
`559caa7e5f1856ba9a87e5ba0809258117adf051` (equal to `origin/main`) after a
fresh `npm ci`.

- `npm run build`: passed.
- `npm test`: 142 of 143 suites, 2,545 of 2,546 tests passed. The failure was
  `src/mcp/__tests__/boundary.test.ts`, one of the two known flaky suites; it
  passed on every later run.
- `npm run format:check` and `npx fallow audit`: not run at the baseline;
  both pass on the first slice.
