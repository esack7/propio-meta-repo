# Tasks: trace-commands

Scope and acceptance are in [requirements.md](requirements.md), design decisions
and risk-specific checks in [design.md](design.md). [delivery.json](delivery.json)
owns slice dependencies, PR status and exact-commit evidence; do not duplicate
slice status here.

## Starting implementation

This planning turn created the spec only. No feature branch or worktree exists.
The reference clone was refreshed to feceea2; no source was edited or tests run.

1. Use prepare-spec for `trace-commands` when implementation is requested.
2. Load configured repository context, install fresh dependencies in the worktree,
   and establish build/test/format/Fallow baseline. Reference node_modules may be
   stale or locally linked; do not use it as implementation evidence.
3. Use start-slice for `trace-cli`. Follow the delivery plan, run the specified
   checks and real-CLI fixtures, commit/push, and open a ready PR when complete.
4. Reconcile review fixes and merge evidence with spec-status before advancing.
   Keep all branch history; use close-spec after every slice and criterion is verified.

Prior owner authorization covers commits, pushes and PR preparation for requested
implementation; ask before merging or publishing. Creating this plan does not
start implementation or provider/billing calls. No new product decisions require
blocking clarification: choices are explicit in design and reviewable in each PR.
