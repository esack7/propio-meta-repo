# Tasks: agent-core-abstraction

- [x] Confirm propio-agent selection and prepare isolated feature worktree.
- [x] Move provider-ready submission contract out of UI ownership.
- [x] Extract the model/tool loop and typed events into a public headless runtime.
- [x] Inject provider, context, executor, policy and optional integrations.
- [x] Make the CLI use the same runtime and preserve its presentation contract.
- [x] Add standalone record-lookup consumer and public API documentation.
- [x] Add direct runtime cancellation, policy, failure and recovery tests.
- [x] Complete final regression, build, formatting and Fallow checks.
- [x] Verify packed declarations, import side effects and clean-install execution.

No separate repository or package publication is requested or performed.

## Validation results

- Build passed with `npm run build` and the package prepack build.
- Full regression suite: 102 suites, 1,527 tests passed.
- Formatting passed with `npm run format:check`.
- Fallow: no issues in 11 changed files; no new suppression directives added.
- `git diff --check` passed.
- Clean installation of the tarball compiled a strict NodeNext TypeScript
  consumer using the public runtime, context and tools declarations.
- The packaged standalone example executed a tool, returned its final response
  and demonstrated cancellation without credentials.
- Guarded import, construction and execution passed with filesystem writes,
  directory scans, process startup, home/cwd discovery and Propio config reads
  forbidden. The same check verified external artifact metadata preservation.
- Direct runtime tests cover lifecycle ordering, opaque reasoning continuation,
  failed tools, denied tools, context retry exhaustion, output-token recovery,
  pre-cancelled input, late tool results, cancellation during tool-start events,
  overlapping turns, and stalled-stream cancellation/idle timeout.
- Live-provider tests were not run: no provider adapter or provider retry policy
  changed. Package publication and a production second consumer remain separate
  milestones.

Implementation was merged into `propio-agent` by PR #89. The clean feature
worktree remains available beneath this spec on `feature/agent-core-abstraction`.
