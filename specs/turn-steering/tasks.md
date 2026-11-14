# Tasks: turn-steering

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

`process-group` (a3), `runtime-steering` (a1, a2, a8), and
`session-commands` (a4, a7) are merged and verified: propio-agent#106
(`c33a73f`), #107 (`b7d2061`), and #108 (`783ca4f`). `steering-ui` (a1, a5,
a6), the last slice, is in progress; see "Slices" in [design.md](design.md).

**Working agreement** (also in [delivery.json](delivery.json)): implement the
slices in order and fix in-scope review findings; commit, push, and open each
PR without asking again; ask before merging or publishing. The design's four
proposals were not reviewed before implementation and are listed under "Open
questions" in [requirements.md](requirements.md); expect corrections in review.

**Practical notes** carried from `tool-permissions`
([its tasks.md](../tool-permissions/tasks.md)): commits are signed through
1Password; `src/auth/openai/__tests__/storage.test.ts` and
`src/mcp/__tests__/boundary.test.ts` are flaky and outside this spec; review
comments arrive as inline PR comments; each review fix adds a test that fails
with the fix reverted.

**CI on #106.** The first run failed on Node 24.10 in
`src/ui/__tests__/chatPromptSession.test.ts` ("pastes an image file path into
a pill"), which waits a fixed 150 ms for a file read; Node 20 passed. The
rerun of that job passed with no change. The test is outside this spec and
passes locally. It has not failed on the last five `main` runs, so if it
fails again on this branch, check whether the new real-process tests are
slowing the runner before calling it a flake.

**CI on #108.** The run at `1ed1ff9` passed only on its third attempt, on
Node 20 each time, with no change between attempts:
1. `src/mcp/__tests__/boundary.test.ts` ("disables a pending connection").
2. `src/ui/__tests__/chatPromptSession.test.ts` ("pastes an image file
   path"), the same fixed 150 ms wait that failed on #106.

Neither test is in code this spec touches. The paste test has now failed
twice on this spec's branches and not on `main`. The likeliest cause is
runner load from the real-process tests added here, but that is not
confirmed. A follow-up that replaces the fixed wait with polling is worth
proposing to the owner.

## Baseline checks (2026-11-13, Node 24.11.0)

Run in `specs/turn-steering/repos/propio-agent` at
`0d24312e165868b6d32743825aceb3548aad9b70` (equal to `origin/main`) after a
fresh `npm ci`.

- `npm run build`: passed.
- `npm test`: 133 of 133 suites, 2,380 of 2,380 tests passed.
- `npm run format:check`: passed.
- `npx fallow audit`: not run at the baseline; passes on the first slice.
- The first slice's edit to `src/tools/runShellCommand.ts` began while this
  test run was in progress. The counts match the slice's later full run less
  its eight new tests.
