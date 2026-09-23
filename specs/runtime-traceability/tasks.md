# Tasks: runtime-traceability

## Checklist

- [x] Review requirements and design
- [x] Run prepare-spec and confirm worktrees
- [x] Implement changes in specs/runtime-traceability/repos/ worktrees (not reference clones)
- [ ] Verify acceptance criteria
- [x] Open pull requests per repository
- [ ] Run close-spec when worktrees are no longer needed

## Implementation tasks

- [x] G1: Define versioned trace identity, context, event envelope, observer, and compatibility adapters.
- [x] G1: Implement the CLI-owned append-only journal, standard redaction, durability barriers, degradation reporting, and truncated-tail recovery reader.
- [x] G1: Propagate identities through run/turn lifecycle, provider requests, summaries, tools, MCP, persistence, and context operations.
- [x] G2: Add structured command/write/edit/MCP outcomes and separate side-effect completion from artifact/capture failure.
- [x] G2: Persist tool results incrementally and preserve assistant/tool ordering across interruption without replay.
- [x] G3: Add redacted effective configuration and prompt-plan revisions with source, scope, and change causes.
- [ ] G3: Record policy/approval decisions, reviewed arguments, mode and skill scope, and provider request mutations.
- [x] G4: Instrument shared provider machinery and all adapters for attempts, timing, upstream IDs/models, stop reasons, errors, and usage.
- [x] G4: Add completeness-aware usage and injectable pricing aggregation.
- [x] G4: Implement side-effect-free journal inspection and portable, hash-verifiable standard export.
- [ ] Add compatibility, secret-handling, failure-path, crash, resume, and all-adapter fixtures.
- [x] Document capture guarantees, adapter availability limits, export caveats, and operational overhead.

## Verification

- [x] Run repository-required build, unit tests, formatting, and pinned Fallow checks in both worktrees.
- [ ] Run deterministic two-turn, retry, summarization, batch interruption, cancellation race, remote timeout, disk failure, slow sink, truncated journal, and old-session resume fixtures.
- [x] Verify offline export inspection in a fresh directory with no provider or tool access.
- [x] Benchmark token-heavy and tool-heavy traces for latency and disk growth.
- [x] Re-score the findings rubric using concrete implementation evidence in `docs/traceability-reassessment.md`.

## Current checkpoint (2026-09-22, final verification in progress)

- [Providers PR #15](https://github.com/esack7/propio-providers/pull/15) merged and package 0.5.0 published. It adds opt-in, per-adapter-attempt request payload snapshots for all nine adapters. Local build, 404 tests, formatting, Fallow, and GitHub CI passed. SDK-internal serialization and retries remain outside this observation boundary.
- [Agent PR #98](https://github.com/esack7/propio-agent/pull/98) merged. It pins published providers 0.5.0, stores full-mode attempt bodies privately, and supports read-only playback of completed answer **and summary** responses from verified bundles.
- The [acceptance review](acceptance-review.md) maps all twelve requirements to tests: ten met, one candidate pending review/merge of the new fixture, and one partial (the literal all-nine-adapter scenario grid). The [reassessment](../../docs/traceability-reassessment.md) rescored every original component conservatively.
- The new two-turn/tool/retry/summary and delayed-sink fixtures are in [Agent PR #99](https://github.com/esack7/propio-agent/pull/99). Agent build, 1,630 tests, formatting, Fallow, and all PR checks pass; providers build, 404 tests, formatting, and Fallow pass. The latest local trace benchmark passed: full token 29.7 ms / 47 KB; tool 3,028 ms / 489 KB; workspace 950 ms / 51 KB, all under documented limits.
- Remaining gates: review and merge the verification fixture; decide whether to add the exhaustive per-adapter matrix; then mark acceptance complete and run close-spec. No live provider or paid smoke tests were run.
