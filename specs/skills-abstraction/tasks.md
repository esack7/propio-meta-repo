# Tasks: skills-abstraction

- [x] Confirm propio-agent as the only selected repository.
- [x] Refresh reference clone and prepare feature/skills-abstraction worktree.
- [x] Separate metadata parser and explicit-root filesystem discovery from CLI conventions.
- [x] Expose a provisional public skills entry point and use it from the application adapter.
- [x] Preserve precedence, diagnostics and runtime metadata behavior.
- [x] Add public-API regression coverage and standalone catalog consumer.
- [x] Build (also via npm prepack), full tests (97 suites / 1,447 tests), formatting and Fallow audit passed.
- [x] Packed npm artifact installed into a clean temporary consumer (231 dependencies).
- [x] Packaged catalog example and CLI adapter returned identical skills and diagnostics from the same roots, including duplicate names and metadata-name ordering.
- [x] Import succeeded with directory scanning, home/cwd lookup and filesystem writes prohibited. The pure parser also succeeded with file reads prohibited.
- [x] Explicit discovery, materialization, file touches and refresh succeeded with home/cwd lookup and writes still prohibited.
- [x] Public declarations resolved under strict NodeNext TypeScript compilation.
- [x] Fallow default audit and release-workflow full audit passed with no issues in 14 changed files; fallow --fail-on-issues exited zero with no dead files, dead exports or duplication.
- [x] git diff --check passed.

Validation used the local packed artifact; no package was published. No live-provider tests were run because provider behavior did not change. Implementation was merged into `propio-agent` by PR #86, and the feature worktree was closed.

Later release milestones: identify a production second consumer and real destination repository; extract and publish only with release authorization.
