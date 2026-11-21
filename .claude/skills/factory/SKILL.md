---
name: factory
description: Build and review spec slices with Claude Code or Codex, resume interrupted work, hand off authorized draft PRs, and verify multi-repository delivery.
---

Run the shared command from the meta-repo root. For previews, use
`bin/factory plan <spec> [--slice <slice>] [--profile <profile>]`.
For authorized implementation, use
`bin/factory run <spec> --slice <slice> [--profile <profile>]`.
For an interrupted slice, use `bin/factory status <spec>` and
`bin/factory resume <spec> [--slice <slice>]`. Add `--draft-pr` to run or resume
when the user authorized a push and draft PR. Resume remembers prior authorization.
Use `--local-only` if the user narrows the handoff to local work.
The built-in profiles are `mixed`, `claude`, and `codex`.

For spec-wide implementation, run `bin/factory run <spec> [--profile <profile>]`
after preparation and after each merge. Use `bin/factory verify <spec> [--json]`
to reconcile current merges, package compatibility and acceptance across the
spec. Report any blocked dependency and the outstanding action.

Use the preview to explain missing prerequisites. Preserve the working
agreement and report the command's handoff, evidence, and any blocker.
See [factory setup and checks](../../../docs/software-factory.md).
