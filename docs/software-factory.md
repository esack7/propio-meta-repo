# Running the software factory

From the meta-repo root, preview a prepared spec and run one named delivery slice:

```sh
bin/factory plan <spec> --slice <slice> --profile mixed
bin/factory run <spec> --slice <slice> --profile mixed
```

The preview also accepts `--json`. Omit `--slice` on a preview to inspect the first eligible planned slice, or the earliest outstanding plan if none is eligible. It reads local state and lists any prerequisites, including unmerged dependencies. The existing `start-slice` helper fetches and checks the current base and actual merges when the run starts. The default handoff is local review. Use the same handoff option on the preview and run: `--draft-pr` for a draft or `--ready-pr` for a PR ready for review after CI.

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

Repository, criterion, and package checks must leave the candidate clean. Direct disposable output to an ignored or temporary directory. If a check edits a tracked file or leaves an untracked file, the builder receives the affected paths and any check failure. It can inspect the files in place, repair the cause, and rerun the checks within the slice's round limit. Before staging a repair, the runner requires recorded untracked output to be removed, ignored, or explicitly claimed by the builder in its `intended_files` result. Repository-relative file and directory claims accept leading `./`, trailing directory slashes, and backslash separators. Directories expand to their tracked and unignored files. Formatting mistakes return to the builder within the round limit. Absolute paths and parent segments are normalized when they resolve inside the worktree. Claims resolving outside it or into Git metadata are rejected. The reviewer receives the complete diff and claims filtered to files still changed in that diff, allowing snapshots, lockfiles, or generated source that belongs in the change.

## Choose agents and limits

The default `mixed` profile builds with Codex Sol 6.1 (`gpt-6.1-sol`) and reviews with Claude Opus 5.5 (`claude-opus-5-5`). Select `claude` or `codex` to use one CLI for both roles.

The CLI supplies its default model when the role omits one. Set `max_build_rounds` for the whole slice and `timeout_seconds` per agent invocation or check. Failed checks, timed-out checks, and actionable review findings consume the same round budget. Repository, criterion, and package check timeouts return diagnostics to the builder. Agent and commit timeouts retain their resumable stage.

## Read the handoff

The runner commits each round's edits to the registered slice branch. It checks the candidate commit, sends the full slice diff and check outcomes to a fresh reviewer, and reruns checks and review after fixes. On approval, `delivery.json` records `review`, the reviewed commit, and the checks that passed for each criterion. Review the local branch and delivery change before proceeding with the normal PR workflow.

Factory commits honor repository hooks and signing settings. Checks and review use the commit produced by Git, including any hook edits. A signing failure or other fatal Git error (exit 128) pauses the run at the commit step. Once the signer is ready or the error is resolved, use `bin/factory resume <spec> --slice <slice>` to retry the staged candidate in the same build round. A signer or hook timeout also remains resumable at the commit stage.

When a hook rejects the candidate, the builder receives the diagnostics and the rejected message. It can repair the staged change or supply a corrected commit message with the required trailers. That message applies to the commit being repaired. Later rounds create their own messages. Repeated hook rejection exhausts the build-round budget and leaves a blocked handoff with the staged work intact.

## Resume a run

```sh
bin/factory status <spec>
bin/factory resume <spec> --slice <slice>
```

Resume reuses the registered branch, original base, agent profile, checks, and repair budget. The runner records each stage under `specs/<spec>/.factory-runs/<slice>/`. An interrupted builder receives the current worktree and its partial edits. An interrupted check or review can run again at the saved commit. The runner recognizes a commit it already made and keeps the recorded review when only the PR handoff remains.

One factory invocation at a time can work on a spec. If a worker survives an interrupted runner, wait for the worker to exit before resuming. Unexpected branch movement, changed acceptance criteria, and ambiguous edits require inspection. Completed repair budgets and explicit agent blockers stay visible in the delivery record. Changes to unrelated slices can proceed while the run is stopped.

For earlier factory runs, resume can use a completed local review with current evidence. For an interrupted implementation it needs an identifiable prior attempt and the branch creation record. Inspect any pre-existing edits before using `--adopt-edits` to include them. Use `--profile` to select the profile for a pre-journal implementation.

## Hand a PR back ready for review

Use the working agreement to select the handoff. When the user asks for a PR ready for review, run:

```sh
bin/factory run <spec> --slice <slice> --ready-pr
```

For an existing reviewed slice or draft, use `bin/factory resume <spec> --slice <slice> --ready-pr`. The runner reuses the reviewed commit and PR number. It waits for the repository's configured checks on that commit, marks the PR ready, and confirms its repository, base, head, and ready state on GitHub. The ready handoff also posts a PR conversation comment identifying the automated reviewer, the reviewed commit, and the saved rationale, including non-blocking findings. The handoff reports the comment link. The factory records that the PR is ready before posting the comment. If posting fails, resume retries the comment and reuses it if GitHub already accepted it. Resuming an older ready handoff backfills the comment from its recorded approval. Long comments point to the full rationale in the delivery record. A changed head requires fresh review. The slice stays in `review` until merge and verification. An interrupted promotion resumes with the saved mode, including when GitHub already marked the PR ready.

Set `ready_checks` in `factory/config.json` to the CI gates that must pass for each repository using ready handoff. Use `Workflow / job` for a GitHub Actions check or the exact name for a standalone check or commit status. Both Propio repositories use `CI / required`. The factory waits up to `timeout_seconds` for pending or unreported checks. If multiple reports match a gate, a successful report on the reviewed commit satisfies it. A failed or skipped gate identifies the check that needs attention. After repairing or rerunning CI for the reviewed commit, use `resume` to finish the handoff.

New PR titles default to `feat(<spec>): implement <slice words>`. Set the slice's optional `pr_title` in the delivery plan for a more specific squash title, such as `fix(cli): preserve the capture setting`. Existing PR titles are preserved.

## Authorize a draft PR

```sh
bin/factory run <spec> --slice <slice> --draft-pr
bin/factory resume <spec> --slice <slice> --draft-pr
bin/factory status <spec> --slice <slice> --remote
```

Use `--draft-pr` when the operator has authorized both pushing the reviewed slice branch and opening or reusing a draft in its mapped GitHub repository. The first command grants that scope at launch. The second can add it after local review. A resumed run remembers the choice. Pass `--local-only` on resume to disable further remote writes. Record the applicable authority in the working agreement. GitHub handoff needs a signed-in `gh` and Git push access.

Before publication the runner checks the clean branch and commit-specific evidence. It creates or fast-forwards only the registered slice branch on the configured origin, checks the PR repository, base, head and draft state, then records the PR number in `delivery.json` with the slice still in `review`. If an interruption loses GitHub's response, resume looks up the PR before attempting creation. A divergent remote branch or conflicting PR needs an operator decision. `status --remote` reports current PR state and leaves delivery records untouched.

For a deterministic demonstration with isolated Git remotes, run `python3 tests/test-factory.py`. To use authenticated agents on the same synthetic greeting-file exercise, run `FACTORY_LIVE_PROFILE=mixed python3 tests/test-factory.py FactoryTests.test_live`. Substitute either single-agent profile to exercise that adapter in both roles. Live runs use the selected account's normal allowance.

## Advance and verify a whole spec

```sh
bin/factory run <spec> --profile mixed
bin/factory verify <spec> --json
```

Run the first command after preparing worktrees and again after each external merge. It fetches the configured default branches, verifies predecessor slices, and builds eligible slices in delivery order. Independent repositories can reach review in the same invocation. A repository with outstanding work waits for that slice. If an implementation was interrupted, use `resume --slice` for that slice. Use `--draft-pr` or `--ready-pr` when that handoff is authorized for every slice the invocation can start. Ready mode checks CI configuration for all eligible repositories before starting a slice. A CI failure or timeout leaves the affected slice resumable and allows independent slices to continue.

Use `verify` to update `delivery.json` and check acceptance without starting agents. A recorded PR must be merged into the mapped base from the registered branch at the reviewed head. The merge commit must be reachable from the freshly fetched base. This also verifies squash merges. A slice with no recorded PR can use direct ancestry. For an externally squash-merged PR, enter its number on the slice so the factory can locate the merge.

A manually recorded merge can unlock a dependent build once the factory confirms the merge. A previously verified dependent remains eligible for downstream work when its own merge, criteria, and applicable package checks still pass. The spec still needs acceptance evidence for the manual predecessor to verify. Each unsuccessful verification reports the current issue and preserves the slice's last recorded status and evidence.

The report names waiting slices, missing criteria, and failed checks. It exits successfully once every slice and criterion is verified. The JSON report includes reviewed heads, integrated commits, and package results. New factory reviews also bind evidence to the criterion wording and configured criterion checks. Earlier records are checked against their retained branch heads. `status` reads the last recorded state. `run` can successfully hand off slices for review while verification is still pending. Merges, releases, and worktree cleanup each have their own authorization.

### Check a producer package against a consumer

Declare the producer as a direct dependency on the consumer slice in `delivery.json`. Use actual slice IDs and npm scripts from the consumer. For example, these fields belong on a consumer slice that uses the `providers` slice:

```json
{
  "depends_on": ["providers"],
  "package_checks": [
    {"producer_slice": "providers", "mode": "candidate", "checks": ["build", "test"]}
  ]
}
```

The default `candidate` mode builds and packs the integrated producer commit, installs that artifact into a temporary copy of the consumer, and runs the listed scripts. The reviewer receives the result for the candidate consumer commit. Spec verification repeats the check if integration produced a different commit, including a consumer squash merge. A saved pass is reusable only for the same repositories, commits, mode and scripts. Add a separate `published` entry to test the consumer's locked registry package. Both modes use the existing package verifier. [Package prerequisites](DELIVERY.md#package-integration-without-publication)

Run `python3 tests/test-factory-spec.py` for the two-repository pilot with local Git remotes, scripted agent and GitHub responses, and real npm packages.
