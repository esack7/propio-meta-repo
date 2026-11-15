# Tasks: trace-commands

Scope and acceptance are in [requirements.md](requirements.md), design decisions
and risk-specific checks in [design.md](design.md). [delivery.json](delivery.json)
owns slice dependencies, PR status and exact-commit evidence; do not duplicate
slice status here.

## Implementation workflow

The planning baseline is recorded in design.md. Current worktree, slice, PR,
and validation state are recorded in delivery.json.

1. Use prepare-spec for `trace-commands` when implementation is requested.
2. Load configured repository context, install fresh dependencies in the worktree,
   and establish build/test/format/Fallow baseline. Reference node_modules may be
   stale or locally linked; do not use it as implementation evidence.
3. Use start-slice for `trace-cli`. Follow the delivery plan, run the specified
   checks and real-CLI fixtures, commit/push, and open a ready PR when complete.
4. Reconcile review fixes and merge evidence with spec-status before advancing.
   Keep all branch history; use close-spec after every slice and criterion is verified.

Prior owner authorization covers commits, pushes and PR preparation for requested
implementation; ask before merging or publishing. Implementation was subsequently
authorized; this does not authorize provider/billing calls. No new product
decisions require blocking clarification: choices are explicit in design and reviewable in each PR.
