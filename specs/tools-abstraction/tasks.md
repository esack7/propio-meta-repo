# Tasks: tools-abstraction

- [x] Confirm propio-agent selection and prepare feature worktree.
- [x] Separate public execution contract and registry from presentation.
- [x] Add explicit local tool dependencies and runtime adapters.
- [x] Add cancellation, approval and output processing extension points.
- [x] Adapt MCP runtime tools through the public contract.
- [x] Document API, compatibility and protections; add standalone example.
- [x] Complete regression tests, build, formatting and Fallow audit.
- [x] Verify packed exports/declarations and clean-install consumption.

Separate milestones: production second consumer, standalone repository approval and publication.

## Validation results

- Build: passed via npm run build and final npm pack prepack build.
- Full regression suite: 100 suites, 1,506 tests passed.
- Formatting: npm run format:check passed.
- Fallow: npx fallow audit reported no issues in 31 changed files; no new suppressions.
- git diff --check passed.
- Final tarball includes the public tools entry point, declarations and standalone example.
- A fresh consumer installed the tarball, compiled a strict NodeNext TypeScript consumer, ran the shipped example, and executed both local tools and a real local stdio MCP server through the public registry.
- Guarded public import/construction passed with home/cwd discovery, filesystem writes/scans and child-process startup forbidden. Public tools have no display methods; the public registry has no render methods.
- Installed tools were byte-compared with the final build to verify the final dispatch-race fix was included.
- Live-provider tests were not required because provider behavior was unchanged. No package was published.

## PR review follow-up

Addressed shell backend parity (incremental UTF-8 decoding, per-stream byte caps, empty-stderr nonzero exit messages), preserved external storage through content-only processing, documented error-output processing and cloneable approval arguments, and simplified MCP delegation. Documented construction-time cwd capture, restored write display-method style, and reordered package exports.

Retained fail-closed approval snapshots rather than falling back to mutable arguments. Retained output processing for non-success results with an explicit status-aware contract. Deferred CLI persistence migration because aggregate turn accounting, diagnostics and context/session ownership require a separate compatibility migration.

Validation: 101 suites / 1,515 tests passed; build, formatting, diff checks and PR-wide Fallow (`--base origin/main`, 34 changed files) passed. Refreshed packed clean-install import, runtime MCP/local tools and strict TypeScript checks passed.

Implementation was merged into `propio-agent` by PR #88, and the feature
worktree was closed.
