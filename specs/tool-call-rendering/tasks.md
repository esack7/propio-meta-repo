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

## Delivery complete (2026-11-15)

All five slices are merged and verified: `display-payload` (#110),
`call-renderers` (#111), `approval-display` (#112), `live-output` (#113),
and `protocol-events` (#114). All nine acceptance criteria have recorded evidence.

#114 merged at 2026-11-15 04:09:03 UTC as `feceea2`, whose tree matches
reviewed head `2232491`. Final-head CI 43675239626 passed every job on
Node 20 and Node 24.10.0: 155 suites, 2,821 tests, and 61 snapshots.
Build, formatting, both Fallow checks and the earlier standalone example pass.

No implementation or review work remains in this spec. Worktrees and retained
slice branches remain available; worktree cleanup is a separate milestone.
See [delivery.json](delivery.json) for criterion-specific evidence and merge history.

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
