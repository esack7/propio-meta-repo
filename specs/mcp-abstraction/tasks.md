# Tasks: mcp-abstraction

- [x] Confirm propio-agent selection and prepare isolated feature worktree.
- [x] Separate reusable connection API and public contracts from CLI configuration and executable tools.
- [x] Inject configuration, identity, deadlines and persistence.
- [x] Replace private SDK process access and add lifecycle regression coverage.
- [x] Document the provisional API and add standalone consumer example.
- [x] Run full tests, build, formatting and Fallow audit.
- [x] Verify packaged exports/declarations and clean-install consumption.

Separate release milestones: identify a second production consumer, approve a real destination repository if needed, and coordinate publication. These are not part of this implementation.

## Validation results

- `npm run build`: passed.
- `npm test -- --runInBand`: 99 suites, 1,484 tests passed (47 MCP tests).
- `npm run format:check`: passed.
- `npx fallow audit`: no issues in 13 changed files.
- `git diff --check`: passed.
- Packed files and public declarations verified; no SDK/agent-tool/config types leak through the public declarations.
- Clean installation of the package passed TypeScript consumer compilation, runtime use, persistence contract checks, and the included catalog example.
- Standalone live stdio discovery passed from a clean installation; guarded home-directory/Propio-file access checks passed for public imports and in-memory toggling.
- No live-provider tests were needed: provider behavior was unchanged. No package was published.

Implementation was merged into `propio-agent` by PR #87, and the feature
worktree was closed.
