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

## Resuming (updated 2026-11-12, second machine)

`approval-ui`, the last slice, is in review as propio-agent#105.

**State**

- `schema-validation` (a1), `policy-core` (a7, a10, a12), and `enforcement`
  (a2, a3, a5, a6, a8, a9, a11) are merged and verified: propio-agent#102,
  #103, and #104.
- `approval-ui` (a2, a4, a5) is `8015e55` plus three rounds of review fixes
  (`704bd92`, `f3ae860`, `d5c8275`), all signed, on
  `codex/tool-permissions-approval-ui`, pushed, based on `origin/main` at
  `cfd0045`. All ten review findings are fixed and CI passed; replies to the inline comments are not posted. Evidence is in [delivery.json](delivery.json). Next:
  review comments, then the owner's decision to merge. After it merges, mark
  it verified; every criterion is then covered and the spec can be closed
  with `close-spec`.
- `src/mcp/__tests__/boundary.test.ts` failed in 2 of 10 local full runs on
  this machine during `enforcement` and passes alone; no MCP code changed.
  Treat it like the OpenAI storage test: rerun before calling it a
  regression.
- Docker on this machine (colima) shares the home directory but not `/tmp`;
  mount test directories from under `$HOME`. To run `bin/propio-sandbox` with
  a temporary `HOME`, set `DOCKER_HOST` to the colima socket, since the
  Docker context lives in the real home. The wrapper builds an image named
  `propio-agent-agent`, the name the owner's own install would reuse without
  rebuilding at the same package version: remove it after a test run.
- To try the CLI without a real model, point `OLLAMA_HOST` at a local server
  that answers `/api/chat` with a tool call. The provider reads `OLLAMA_HOST`
  before the configured host.

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
