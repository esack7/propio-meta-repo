# Requirements: trace-commands

## Summary

Phase 4 of [maturity-audit-roadmap](../maturity-audit-roadmap/design.md): make
existing trace journals useful from the terminal and make session usage/cost
visible. Phases 1–3 are merged; this phase completes the daily-driver milestone.
The selected repository is `propio-agent`, as proposed in the roadmap and accepted
when the owner asked to continue with this phase. `repos.txt` is authoritative.

## Scope

- `propio trace list | show <run> | export <run> | verify <bundle>` using existing
  trace inspection/export APIs, with stable human and JSON output.
- In-session `/trace` and `/usage`, including background summaries and retries.
- A capture flag and persistent setting; retain the environment variable as a
  compatibility fallback and preserve standard capture as the default.
- Versioned, dated default pricing data; unsupported models and unsupported
  billing contexts remain unknown, never implicitly free.
- Run identifiers and diagnostic commands when a turn fails.
- Trace user-entered `!` shell commands, including rejection and cancellation.
- Retire the misleading `--show-trace` name through a documented compatibility
  alias and rewrite trace documentation as a usable workflow.

## Non-goals

No provider adapter changes, provider calls or paid tests, publication, durable
session replay/resume, new transport, workspace rewind, trace GUI, or journal
format redesign. Trace capture stays observational. Pricing estimates are not
invoices or estimates of subscription entitlements. No automatic network pricing
lookup at runtime. Export does not imply uploading or sharing the bundle.

## Acceptance criteria

- [ ] **a1** Listing and showing a run work without credentials, provider startup,
  MCP discovery, or a running agent. Run selection is workspace-scoped and
  deterministic; missing/ambiguous runs produce actionable errors.
- [ ] **a2** A timeline shows requests, attempts/retries, tool operations, policy
  decisions, durations and known tokens, with explicit missing/incomplete data.
  Fixtures cover failed, cancelled, incomplete and successful journals; output is
  deterministic and hostile text cannot control the terminal.
- [ ] **a3** CLI export and verify use existing APIs. Standard export is the
  default; full material requires explicit selection. Tampered bundles fail with
  nonzero status, and output does not overwrite existing destinations silently.
- [ ] **a4** A packaged pricing resolver has source URLs, version and effective
  date. Known supported cases calculate correctly; unknown models/endpoints and
  unsupported usage components remain unpriced. Provider-reported and estimated
  costs remain distinguishable without double counting.
- [ ] **a5** `/trace` describes the latest foreground turn; `/usage` covers the
  current session's journals, including background summaries and retries. Totals
  match offline inspection with the same pricing resolver and preserve partial
  coverage, unknown usage and currency boundaries.
- [ ] **a6** Capture resolves CLI flag > environment > runtime setting > standard.
  Both standard/full are validated and their origin is inspectable. Existing
  environment usage and settings fields continue to work; full capture remains
  explicit and sensitive material is not displayed accidentally.
- [ ] **a7** Failed turns identify their available journal and give a working
  `propio trace show` hint in text mode, with structured fields in JSON mode.
  Capture failures retain the original error and state when no trace is usable.
- [ ] **a8** Operator `!` commands produce attributed journal records with outcome,
  duration, cwd and cancellation/denial status. Standard capture omits raw command
  and output content; full capture follows existing redaction/material rules.
  Recording failure does not change command execution or error handling.
- [ ] **a9** Help and README document the complete diagnose/list/show/export/verify
  workflow, `/trace`, `/usage`, capture/privacy and pricing limitations. The old
  `--show-trace` flag preserves its behavior as a deprecated visibility alias and
  cannot be confused with capture. Credential-free process tests exercise the CLI.

## Working decisions

Design details and planned checks are in [design.md](design.md). Delivery state and
exact-commit evidence belong to [delivery.json](delivery.json). No implementation
worktree is needed until the owner starts implementation of this plan.
