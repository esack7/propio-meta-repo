# Tasks: tool-permissions

Delivery status, dependencies, PRs, and commit-specific evidence live in
[delivery.json](delivery.json). Requirements own acceptance descriptions; the
record maps stable criterion IDs to reviewable slices. Avoid duplicate status lists.

Before implementation, fill the delivery record with the approved scope and working
agreement. Define checks for the risks relevant to each slice in the design.

At review handoffs and merges, reconcile the delivery record and run `spec-status`.
Report completed slice, evidence, remaining scope, next action, and decision needed.
Use `start-slice` to continue authorized work. Run normal `close-spec` only after all
slices and criteria are verified; worktree cleanup alone does not complete a spec.

## Before the first slice

- [x] Design proposals agreed (2026-11-12); see "Open questions" in
      [requirements.md](requirements.md).
- [x] Feature worktree prepared and baseline checks recorded below.

## Baseline checks (2026-11-12, Node 24.11.0, npm 11.6.1)

Run in `specs/tool-permissions/repos/propio-agent` on `feature/tool-permissions`
at `efa1de8f4e5b1c06eeb5cdb59400add89fb059ba` (equal to `origin/main`) after a
fresh `npm ci`.

- `npm run build`: passed.
- `npm test`: 116 of 116 suites, 1,733 of 1,733 tests passed. This confirms the
  two failing auth suites recorded in the roadmap spec were a stale install in
  the old reference clone.
- `npm run format:check`: passed.
- `npx fallow audit`: not run.
- `@propio-ai/providers` is the published 0.6.0 from the lockfile, not a local
  link.
