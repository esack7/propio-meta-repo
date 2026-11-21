# A software factory for the Propio meta-repo

## Placement and first release

Build a local command in this meta-repo that takes a prepared spec through implementation and review, one delivery slice at a time. The meta-repo already knows which repositories participate, where edits belong, what depends on what, and what evidence counts. Keep each product repository responsible for its code and its own checks. The factory itself can ship as ordinary changes to the scaffold on a meta-repo branch.

The first useful milestone is one invocation that takes a planned slice to a locally committed, checked, independently reviewed change. The operator can choose Claude Code or Codex for either role. A later milestone connects the review handoff to an authorized PR and continues a multi-repo spec after merge.

The Zazen Codes example starts from a labeled issue and runs intake, specification, build, checks, review, and a merge decision. Borrow its sequence of checks before review, bounded repair rounds, and durable handoffs. Here, intake and specification already have owners. A single approved spec can produce several PRs with different repositories and merge dependencies. Start at that boundary and implement the runner against this repo's delivery contract. [Example design](https://github.com/zazencodes/zazencodes-season-3/blob/main/src/software-factory-claude-code-v2/DESIGN.md) · [Local delivery contract](DELIVERY.md)

## Operator experience

Proposed commands, run from the meta-repo root:

```sh
factory plan <spec>
factory run <spec> --slice <slice> --profile mixed
factory status <spec>
factory resume <spec>
```

`plan` is read-only. It shows the selected slice and repository, prerequisites, role assignments, configured checks, and where the run will hand back to the operator. A legacy spec without a populated delivery plan gets guidance to initialize and populate it through the existing workflow. Existing specs can continue to use the manual workflow.

`run` starts the approved work. In the first release the operator selects a slice explicitly. Once merge reconciliation is implemented, omitting the slice can select the next eligible slice in delivery order. `status` explains what happened and what is outstanding. `resume` reconciles the journal with the actual worktree, delivery record, and any existing PR before taking the next action.

## Implementation

Use a small Python command under `factory/`, matching the existing delivery tooling. Expose the same command through the usual Claude and Codex skill entry points. Keep shared role prompts, check definitions, and profile configuration alongside the command. Either CLI or a terminal can start the same run.

An example of the proposed tracked configuration:

```json
{
  "profiles": {
    "claude": { "builder": "claude", "reviewer": "claude" },
    "codex": { "builder": "codex", "reviewer": "codex" },
    "mixed": {
      "builder": { "agent": "codex", "model": "gpt-6.1-sol" },
      "reviewer": { "agent": "claude", "model": "claude-opus-5-5" }
    }
  },
  "max_build_rounds": 3
}
```

Allow optional model selection per role. A same-agent profile still starts a fresh review session. The adapter takes a role, working directory, context, permissions, deadline, and expected result schema. It returns a validated result or a typed failure such as missing login, timeout, or malformed output. Use native noninteractive interfaces and validate both the process result and final payload. Keep provider-specific flags and event parsing inside the two adapters. [Claude Code programmatic usage](https://code.claude.com/docs/en/headless) · [Codex noninteractive usage](https://developers.openai.com/codex/noninteractive/)

| Step | Owner | Behavior |
|---|---|---|
| Select and start | Runner and existing helpers | Read the spec, `repos.txt`, delivery record, and configured context files in order. Use `spec-status` for inspection and `prepare-spec` when preparation is authorized. Call `start-slice` for a new slice. It enforces dependency merge proof and registers the worktree branch for either agent. |
| Build | Builder | Receive the slice criteria, design, repository instructions, and prior findings. Work in the selected feature worktree. Return a summary of changes and any unresolved questions. |
| Check | Runner | Capture the candidate commit. Execute the repository-required checks and the checks mapped to this slice's criteria using definitions from the trusted plan. Record command, outcome, and commit. Feed failures back to the builder before spending a review round. |
| Review and repair | Fresh reviewer, then builder | Give the reviewer the diff against the slice base, requirements, and check results in a read-only environment. Require findings tied to a criterion or concrete defect. Route actionable findings to the builder and rerun checks and review on the revised commit. Exhausted rounds produce a handoff with the outstanding failure. |
| Hand off and advance | Runner | Record evidence per criterion at the reviewed commit, plus remaining scope, next action, and any decision needed. When authorized, create or reuse the slice PR. Reconcile actual merge proof before advancing dependent work. Verify all slices and criteria before offering the existing close workflow. |

### State, authority, and recovery

- Keep `delivery.json` authoritative for slices, PRs, status, and acceptance evidence. Put attempt details in a Git-ignored run directory keyed by spec, slice, and attempt. Keep durable summaries of checks in the tracked evidence so another checkout can assess the result.
- Add a narrow update operation to the existing delivery helper for validated status, PR, and evidence writes. Reuse its per-spec lock and atomic writes, with an expected prior state and branch head. Serialize lifecycle operations. A separate run lock prevents two factory invocations from dispatching a worker for the same spec.
- Keep local build, check, and review resumable without a provider conversation ID. Journal intent before side effects and record the observed result afterward. On restart, inspect registered branch, actual HEAD, dirty files, and existing PR before retrying. Preserve interrupted edits. Surface ambiguous ownership for an operator decision. A changed commit invalidates earlier checks and reviews.
- Give the builder write access to its worktree and the reviewer read-only access. The runner owns Git and GitHub operations and delivery updates. Bind permissions to explicit operator authorization, consistent with the working agreement. A profile selects agents and models. Running local checks or receiving a favorable review does not grant authority to push, open a PR, merge, or publish.

## Delivery sequence

| Increment | Deliverable | Acceptance demonstration |
|---|---|---|
| 1. Read-only plan | CLI, config validation, and context assembly for one named slice | A fixture with two repositories shows the correct worktree, criterion, checks, and ordered context. A missing plan or unresolved dependency is explained. Planning makes zero writes and launches zero agents. |
| 2. Local slice end to end | Runner, delivery update operation, builder and fresh reviewer, checks, bounded repair, and local handoff. Start with a scripted test adapter and wire in both real CLIs. | In a temporary repo, a failed check returns to the builder, a reviewer requests a fix, and the recorded evidence matches the final commit. Run the same small slice in isolated fixtures with Claude only, Codex only, and Codex building with Claude reviewing. |
| 3. Recovery and PR handoff | Locking, journal reconciliation, remote status, and authorized draft PR creation | Interrupt after branch creation, during an edit, and immediately after PR creation. Resume retains edits and reuses the branch and PR. A competing run cannot start a second worker. A local-only run makes no GitHub writes. |
| 4. Multi-repo delivery | Walk planned slices in dependency order, reconcile merges, support package verification, and report spec-level acceptance | Pilot on a small producer/consumer change. Exercise exact-commit candidate verification with `verify-packages`, a squash merge, and a blocked downstream slice. A later edit invalidates stale evidence. Completion is reported only when all criteria and slices are verified. |

Keep fixture tests deterministic and run them in the scaffold's existing test suite. Use authenticated CLI smoke runs separately to catch differences in permissions and output formats. Add issue intake, specialized reviewers, parallel jobs, or a dashboard after the local pilot identifies a need for them.
