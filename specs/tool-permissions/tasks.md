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

## Resuming (handoff written 2026-11-13)

Work stopped by choice after `policy-core` merged; nothing is in progress.

**State**

- `schema-validation` (a1) and `policy-core` (a7, a10, a12) are merged and
  verified: propio-agent#102 and #103. Evidence is in
  [delivery.json](delivery.json).
- `enforcement` (a2, a3, a5, a6, a8, a9, a11) and `approval-ui` (a2, a4, a5)
  are planned and not started.
- The worktree `specs/tool-permissions/repos/propio-agent` is clean on
  `codex/tool-permissions-policy-core` at `e19c10a`, the merged head of #103.
  Its `node_modules` matches that branch.
- The meta-repo commits recording all of this are on
  `feature/maturity-audit-roadmap`, local only, unless pushed since.

**Before starting `enforcement`**

1. Read [requirements.md](requirements.md) "Open questions",
   [design.md](design.md) "As implemented in `policy-core`" and "Notes for
   enforcement", and the README section "Reusable policy API (provisional)" in
   propio-agent.
2. Get the owner's answer to open question 1 (exact command grants and the
   working directory). The recommendation is C.
3. Run `spec-status`, then `start-slice` for `enforcement`. It branches from
   the current `origin/main`. Run `npm ci` in the worktree afterwards, since
   `ajv` was added in #102.

**Working agreement** (also in [delivery.json](delivery.json)): implement the
slices in order and fix in-scope review findings; for the remaining slices,
commit, push, and open the PR without asking again; ask before merging or
publishing.

**Practical notes**

- Commits are signed through 1Password. If a commit fails with
  `1Password: failed to fill whole buffer`, ask the owner to unlock 1Password
  and retry; do not commit unsigned.
- `src/auth/openai/__tests__/storage.test.ts` (OS process lock) is flaky,
  failing in about two of three isolated runs. It is outside this spec;
  rerun before treating it as a regression.
- Review comments arrive as inline PR comments: read them with
  `gh api repos/esack7/propio-agent/pulls/<n>/comments`, not only
  `gh pr view`.
- Each review fix so far added a test that fails with the fix reverted; keep
  doing that.

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
