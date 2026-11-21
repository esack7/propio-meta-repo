---
name: factory
description: Preview, run, or resume a software factory slice with Claude Code or Codex, including authorized draft PR handoff.
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

Use the preview to explain missing prerequisites. Preserve the working
agreement and report the command's handoff, evidence, and any blocker.
See [factory setup and checks](../../../docs/software-factory.md).
