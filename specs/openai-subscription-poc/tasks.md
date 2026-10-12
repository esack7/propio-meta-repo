# Tasks: openai-subscription-poc

## Completed

- [x] Confirm repository scope and create isolated POC worktrees with bundled helpers.
- [x] Implement experimental subscription adapter and keep API-key behavior unchanged.
- [x] Implement browser OAuth, identity validation, account labels, storage, rotation, revocation, and cancellation.
- [x] Link provider worktree into agent worktree and provide a local launcher.
- [x] Implement text/tool/history smoke tests and an interactive agent-runtime chat.
- [x] Document testing commands, constraints, and findings.

## Verification and follow-up

- [x] Full provider and agent test suites.
- [x] Public authentication discovery endpoint probe.
- [x] Final builds, formatting, quality checks, and launcher verification after cleanup.
- [x] User completes live login; agent verifies status, model discovery, and all three smoke stages and records outcomes in findings.md.
- [ ] User tries interactive chat; live refresh and logout/relogin checks remain follow-up work.
- [x] Use POC evidence to draft the [full feature spec and implementation plan](../openai-subscription/tasks.md).

## Closeout

- [x] Preserve the provider POC as local-only commit `5e570123478507300982909809b43fabd6de0fea` on `feature/openai-subscription-poc`.
- [x] Preserve the agent POC as local-only commit `e66d06d162c8a2af722427c3df7a152d7456fe01` on `feature/openai-subscription-poc`.
- [x] Close both POC worktrees with the bundled close-spec helper after explicit user authorization for retained unpushed commits.
- [x] Verify worktree removal, retained branches/spec documents, and preserved POC credential directory.

Cleanup occurred October 12, 2026 after the full feature was merged and released. POC commits were not pushed or merged. Live refresh/logout/interactive acceptance above remains unchecked; cleanup does not establish those outcomes. The retained branches can be reopened with the prepare-spec helper and explicit branch-reuse authorization.
