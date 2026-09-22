# Tasks: context-management

## Implementation

- [x] Confirm propio-agent repository selection.
- [x] Refresh reference clone and prepare isolated feature/context-management worktree.
- [x] Separate reusable conversation state from the CLI skill/mention adapter.
- [x] Extract token measurement from agent diagnostics and inject estimation.
- [x] Accept rendered supplemental context and caller-provided artifact lookup.
- [x] Share context encoding/validation while preserving the CLI session envelope.
- [x] Support provider or callback summarization.
- [x] Add a provisional package entry point and minimal consumer.
- [x] Add legacy compatibility and boundary regression tests.

## Verification

- [x] Full tests: 95 suites, 1,421 tests passed.
- [x] TypeScript build and repository formatting passed.
- [x] Fallow audit: no issues in 17 changed files.
- [x] Packed npm artifact installed into a clean temporary consumer.
- [x] Consumer imported the public subpath and planned/round-tripped context with
  working-directory/home discovery and file writes blocked.
- [x] Public TypeScript declarations resolved under strict NodeNext compilation.
- [x] Runnable example and git diff whitespace checks passed.

No live-provider calls were made; provider configuration and transport behavior
were not changed. No package was published and no reference working tree was edited.

## Later release milestones

- Identify a second production consumer and real destination repository.
- Extract and publish separately after release authorization.

Implementation was merged into `propio-agent` by PR #85, and the feature
worktree was closed.
