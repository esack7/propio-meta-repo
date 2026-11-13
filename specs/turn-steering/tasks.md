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

The spec is planned and no slice has started. Slices, in order:
`process-group`, `runtime-steering`, `session-commands`, `steering-ui`; see
"Slices" in [design.md](design.md).

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
