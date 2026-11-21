# Running a local software factory slice

From the meta-repo root, preview a prepared spec and run one named delivery slice:

```sh
bin/factory plan <spec> --slice <slice> --profile mixed
bin/factory run <spec> --slice <slice> --profile mixed
```

The preview also accepts `--json`. Omit `--slice` on a preview to inspect the first planned slice in delivery order. It reads local state and lists any prerequisites, including unmerged dependencies. The existing `start-slice` helper fetches and checks the current base and actual merges when the run starts. The default handoff is local review. Add `--draft-pr` to the preview to see the remote handoff, or to the run to authorize it.

## Prepare the inputs

1. Use the existing spec and worktree workflows. For a legacy spec, initialize its delivery record with `sh .claude/skills/spec-status/scripts/spec-status.sh project-repositories.yaml <spec> init` and populate the plan. Record the authorized scope in the working agreement. [Delivery record format](DELIVERY.md)
2. For each criterion assigned to the slice, add the commands that exercise that criterion under `factory_checks` on the slice object in `delivery.json`. Each command is an array of arguments. For example, this field on a slice covering `a1` runs its regression test:

   ```json
   "factory_checks": {
     "a1": [["npm", "test", "--", "--runInBand", "tests/recovery.test.ts"]]
   }
   ```

3. Configure the repository's standard checks under `repo_checks` in [factory/config.json](../factory/config.json). An explicitly empty array is valid for a repository with only criterion-specific checks. Install the worktree's development dependencies as required. The runner executes the configured commands directly in the worktree, in order, and stops at the first failure. Use trusted checks and run with the credentials appropriate to those commands.
4. The runner uses Python 3.9+, Git, and Ruby with its standard YAML library for the project map's ordered context paths. Sign in to the CLIs required for the selected profile and configure a Git author for local commits. Claude Code needs `--restricted` and `--json-schema`. Codex needs `exec --ephemeral`, `--ignore-user-config`, and `--output-schema`. The review session always starts fresh.

## Choose agents and limits

The default `mixed` profile builds with Codex Sol 6.1 (`gpt-6.1-sol`) and reviews with Claude Opus 5.5 (`claude-opus-5-5`). Select `claude` or `codex` to use one CLI for both roles.

The CLI supplies its default model when the role omits one. Set `max_build_rounds` for the whole slice and `timeout_seconds` per agent invocation or check. Failed checks and actionable review findings consume the same round budget.

## Read the handoff

The runner commits each round's edits to the registered slice branch. It checks the candidate commit, sends the full slice diff and check outcomes to a fresh reviewer, and reruns checks and review after fixes. On approval, `delivery.json` records `review`, the reviewed commit, and the checks that passed for each criterion. Review the local branch and delivery change before proceeding with the normal PR workflow.

## Resume a run

```sh
bin/factory status <spec>
bin/factory resume <spec> --slice <slice>
```

Resume reuses the registered branch, original base, agent profile, checks, and repair budget. The runner records each stage under `specs/<spec>/.factory-runs/<slice>/`. An interrupted builder receives the current worktree and its partial edits. An interrupted check or review can run again at the saved commit. The runner recognizes a commit it already made and keeps the recorded review when only the PR handoff remains.

One factory invocation at a time can work on a spec. If a worker survives an interrupted runner, wait for the worker to exit before resuming. Unexpected branch movement, changed acceptance criteria, and ambiguous edits require inspection. Completed repair budgets and explicit agent blockers stay visible in the delivery record. Changes to unrelated slices can proceed while the run is stopped.

For earlier factory runs, resume can use a completed local review with current evidence. For an interrupted implementation it needs an identifiable prior attempt and the branch creation record. Inspect any pre-existing edits before using `--adopt-edits` to include them. Use `--profile` to select the profile for a pre-journal implementation.

## Authorize a draft PR

```sh
bin/factory run <spec> --slice <slice> --draft-pr
bin/factory resume <spec> --slice <slice> --draft-pr
bin/factory status <spec> --slice <slice> --remote
```

Use `--draft-pr` when the operator has authorized both pushing the reviewed slice branch and opening or reusing a draft in its mapped GitHub repository. The first command grants that scope at launch. The second can add it after local review. A resumed run remembers the choice. Pass `--local-only` on resume to disable further remote writes. Record the applicable authority in the working agreement. GitHub handoff needs a signed-in `gh` and Git push access.

Before publication the runner checks the clean branch and commit-specific evidence. It creates or fast-forwards only the registered slice branch on the configured origin, checks the PR repository, base, head and draft state, then records the PR number in `delivery.json` with the slice still in `review`. If an interruption loses GitHub's response, resume looks up the PR before attempting creation. A divergent remote branch or conflicting PR needs an operator decision. `status --remote` reports current PR state and leaves delivery records untouched.

For a deterministic demonstration with isolated Git remotes, run `python3 tests/test-factory.py`. To use authenticated agents on the same synthetic greeting-file exercise, run `FACTORY_LIVE_PROFILE=mixed python3 tests/test-factory.py FactoryTests.test_live`. Substitute either single-agent profile to exercise that adapter in both roles. Live runs use the selected account's normal allowance.
