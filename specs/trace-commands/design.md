# Design: trace-commands

## Baseline and existing seams

Planning baseline: `propio-agent` main at
`feceea2bde3eb0ff88c3ec5c0c4e3e99a60971cd`, refreshed with the repository helper.
The reference clone is read-only during feature work. No baseline tests were run
for this documentation-only planning step; establish a fresh worktree baseline
before source changes.

- `src/trace/index.ts` exports journal reading, inspection, export, verification,
  and measurement aggregation. Reuse these contracts instead of implementing
  another parser, verifier, or cost accumulator.
- `src/trace/inspection.ts` returns capture completeness, warnings, operation
  outcomes and provider measurements. Timeline detail also needs the journal's
  event envelopes; current operation summaries alone are not a timeline.
- `src/trace/measurements.ts` already separates reported costs, local estimates,
  per-currency totals, retries, purposes, and unpriced attempts. Its pricing
  resolver is injectable and carries source/version/effectiveDate metadata.
- `src/index.ts` creates journals under the sessions directory at
  `traces/<sessionId>/<runId>.jsonl`. Its `traceCaptureLevel` currently reads only
  `PROPIO_TRACE_CAPTURE_LEVEL` and accepts standard/full.
- `src/config/runtimeConfig.ts` owns CLI > env > runtime settings > defaults.
  Extend this existing configuration route, preserving unrelated settings.
- `src/agent.ts` owns private session identity, active runs, lastTraceRunId and
  separate summary runs. Supply a small read-only application accessor/service
  for trace selection rather than exposing mutable recorders to UI handlers.
- `src/cli/args.ts`, `src/index.ts`, and `src/ui/slashCommands.ts` own CLI routing.
  `--show-trace` currently means status plus reasoning summary, not capture.
- `src/ui/processBashCommand.ts` applies mode policy then runs the shell directly;
  it has no journal hook. Model-tool events therefore do not cover operator `!`.

## Commands and output

Route `propio trace ...` before normal provider/auth/MCP initialization. A shared
application service resolves the normal workspace session directory, discovers
journals, and calls public trace APIs. Pass paths and writers explicitly so tests
need no home configuration. Do not add configuration discovery to trace primitives.

Proposed syntax:

- `propio trace list [--session <id>] [--limit <n>] [--json]`
- `propio trace show <run> [--session <id>] [--json]`
- `propio trace export <run> --output <directory> [--session <id>] [--full] [--json]`
- `propio trace verify <bundle-directory> [--json]`

`<run>` is an exact run ID in the current workspace's trace root, not an arbitrary
path or an implicit prefix search. Optional session ID disambiguates duplicates.
Reject traversal IDs; do not follow discovered journal links outside the root.
Unscoped selection skips symlinked sessions; explicit selection of one is refused.
List defaults to the newest 20 runs, with a positive limit capped at 1000 and stable
ID tie-breaking. Review refinement: probe up to 64 KiB of each first record for
ordering, then fully inspect only selected rows. Expose listed_runs inspection
scope, base completeness on actual read/capture warnings rather than ordinary
limit truncation, and count all nonreturned journals in omitted so total equals returned plus omitted. Report
corrupt/unreadable entries and completeness without
silently presenting partial results as complete. Tests determine expected behavior
for empty roots, duplicate IDs, invalid limits and racing/in-progress journals.

Show prints identity/capture summary followed by event sequence order with stable
relative timing, operation/request/attempt relationships, policy decisions and
measurement summaries. Prefer paired monotonic timing; an unpaired terminal
event may use a finite nonnegative payload duration. Missing times/tokens are
unknown, not zero. Reuse `visibleText` and existing width helpers. Render bounded previews; do not load full
captured prompts, responses or workspace material just to show a timeline. JSON
is a documented versioned result object, not terminal text with ANSI removed.
Command errors go to stderr; JSON success stdout is one object. Exit 0 for a
successful read (with explicit completeness warnings), nonzero for selection,
I/O, usage or verification errors. Verify reports findings as data as well as
setting its exit status.

Export uses the trace API’s `exportTraceReadResult` (also used by
`exportTraceJournal`); verify uses `verifyTraceExport`. Export requires
an explicit new destination, standard capture by default and `--full` for captured
private material. Do not silently overwrite or reinterpret a corrupt bundle.
Export the already-validated read result so appends and path replacement cannot
change the exported events. Reuse existing redaction and traversal protections,
supplementing CLI tests where
argument routing introduces a boundary. No network or tool execution in any of
these commands.

## Pricing

Ship a small, explicit supported table as package data. Each entry identifies the
provider, exact model/aliases, supported endpoint/billing class, currency, rate
units, source URL and verification/effective date; the table has a version.
Verify initial rates against primary provider pricing documentation during the
pricing slice. No numerical rates are asserted by this plan. Initial coverage
should include documented OpenAI API and Anthropic API models that the resolver
can identify unambiguously; other providers stay unknown until explicit entries
are verified. Do not infer dated variants, routed upstream prices, free local
models, or subscription prices from a friendly model name.

The default resolver remains application-owned and implements the existing
ProviderPricingResolver. Preserve explicit overrides for other consumers. Apply
cache and reasoning categories only when their inclusion in the provider's token
counts is known; do not bill reasoning twice or count cached input as both full
price and cache price. An unsupported pricing rule or missing usage stays partial
or unknown. Never add reported and estimated costs for the same attempt into a
single misleading bill; use the inspection model's separate totals/labels.
Cross-currency costs are not converted or summed. Snapshot/fixed arithmetic tests
use deterministic data, not network calls or live bills. Package tests verify the
data ships in the built/packed artifact.

## Capture and visibility compatibility

Add `--trace-capture <standard|full>` and `runtime.traceCaptureLevel` in the existing
settings file; retain `PROPIO_TRACE_CAPTURE_LEVEL`. Use established precedence
CLI > env > settings > standard, with invalid values failing clearly and origin
reported through runtime configuration. Resolve capture before constructing any
run, including background summary runs. Test forwarding in sandbox invocation.
No capture-off mode is added in this scope.

Introduce `--show-turn-details` as the accurate name for status plus reasoning
summary visibility. Retain `--show-trace` as a deprecated alias for that same
behavior; neither flag changes capture. Help and migration examples explain this.
Avoid repeated deprecation output that would corrupt JSON or streamed answers.

## In-session inspection and failures

`/trace` at the idle prompt summarizes the latest foreground run, even if a
background summary completed later. No run yet is an explicit empty state.
`/usage` includes all recorded runs for the current session (not every historical
session in the workspace), including provider summary work and retries. Match
inspection using the same resolver, preserve completeness, and ensure distinct
runs are counted once. Foreground and summary IDs must remain distinct; no new
module-level session state. Read after run closure and label concurrently written
summary journals as partial. Normal turn output and JSON responses remain stable.

At failed foreground completion, use actual allocated trace identity and capture
state to print the run ID plus a shell-safe show command. Add optional structured
trace metadata to JSON error output instead of contaminating stdout. Do not emit
an invented run path when allocation failed, or replace the original provider,
tool or cancellation error when inspection/formatting fails. Cancellation remains
distinct from failure; a summary's failure must not replace the foreground hint.

## Operator shell journal

Add an optional application trace lifecycle hook around `processBashCommand`,
including mode denial before spawn. Each nonempty operator command gets its own
run linked to the same session, with actor=user/source=operator_shell. Keep one
terminal outcome (success, nonzero exit, timeout, launch failure, cancellation,
or policy denial), timing and cwd metadata. Empty input creates no run. This
path creates no provider usage and must not replace the latest foreground-model
run selected by `/trace`.

Standard mode records metadata and lengths rather than raw command/output. Full
mode uses the existing redacted material capture path and its caps/failure behavior.
Record completion before closing, including thrown spawn failures, while keeping
execution and cleanup independent of capture failure. Existing shell policy and
output behavior remain authoritative; this does not add new permission prompts.

## Delivery and validation

Five slices, in delivery order (the authoritative dependency graph is delivery.json):

1. `trace-cli`: discovery, standalone command routing, timeline, export/verify,
   process-level no-provider-startup tests and initial workflow docs (a1–a3, a9).
2. `pricing`: supported data/resolver and arithmetic/packaging checks (a4).
3. `capture-settings`: precedence, validation, sandbox forwarding, visibility
   alias/help migration and capture docs (a6, a9).
4. `session-inspection`: `/trace`, `/usage`, failure hints and reconciliation of
   multi-run measurements with offline inspection (a5, a7, a9).
5. `operator-shell`: shell journal lifecycle, policy/cancellation/failure cases,
   complete end-to-end documentation and acceptance pass (a8, a9).

For every source slice: `npm test`, `npm run build`, `npm run format:check`,
`npm run fallow:audit -- --base origin/main`, and `npm run fallow:check`. Record
exact commit evidence. At UI handoffs run the real built CLI against local scripted
journals/provider fixtures at narrow/wide widths, including an interactive session
for slash commands and a shell command. No credentials or paid calls are needed.
Keep deterministic timeline snapshots and inject clocks/IDs for fixtures. Include
partial JSONL, duplicate identities, malformed rows, terminal control characters,
known/unknown/mixed pricing, cached usage, retries and missing material. Do not
call a slice verified until review, merge and evidence reconciliation are done.

## Risks and boundaries

The main risks are counting retries/summary work twice, silently treating missing
usage as free, starting provider setup from offline commands, exposing full capture
by default, and changing error identity while adding failure hints. The checks
above are planned before implementation. Existing imports remain one-way: trace
holds data/inspection logic; CLI/UI own discovery, formatting and configuration.
The full-capture journal can contain private data; docs explain this without adding
an unrelated sharing workflow. Any newly discovered cross-repository change needs
an explicit repository-selection decision before preparation.
