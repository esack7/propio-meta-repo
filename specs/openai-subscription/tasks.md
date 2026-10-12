# Tasks: openai-subscription

Planning date: October 11, 2026. Closeout updated October 12, 2026. Status: reviewed implementation merged and published in providers `0.6.0` and agent `1.4.0`; feature and POC worktrees removed with branches and evidence retained. Detailed live/platform acceptance remains incomplete. See [decisions.md](decisions.md) and [verification.md](verification.md). Scope: `propio-providers` and `propio-agent` as listed in helper-generated repos.txt. Acceptance IDs refer to [requirements.md](requirements.md); interfaces and policy are in [design.md](design.md).

## Delivery sequence

| Phase | Deliverable | Dependencies | Acceptance covered | Exit gate |
| --- | --- | --- | --- | --- |
| 0 | Isolated feature workspace and POC inventory | Spec review | R20 | Refreshed references; feature worktrees prepared; POC evidence preserved |
| 1 | Final contracts and platform feasibility | 0 | R1–R3, R6, R9, R17 | Config/factory ADR, OS store/lock proof, catalog and sandbox spike results |
| 2 | Production account/credential lifecycle | 1 | R4–R7 | OAuth/store/renewal/logout race, identity, and privacy tests |
| 3 | Production subscription provider | 1; uses 2 for live validation | R2–R3, R10–R12, R15–R16 | Factory, request, trace, SSE, context-recovery and API regressions |
| 4 | Normal CLI setup, account and model selection | 2 + 3 | R8–R9, R19 | Fresh install and existing-user flows; clear account/billing selection |
| 5 | Complete agent workflows and native preview | 4 | R13–R16, R18–R20 | Tools/MCP/session/summary tests; live renewal/relogin; native platform gates |
| 6 | Subscription sandbox with host renewal | 1 spike + 5 | R6–R7, R17 | Credential/mount/lifecycle tests and live long-session renewal in sandbox |
| 7 | Full release and distribution | 5 + 6 | R18–R20, all remaining | Clean published-consumer verification, documentation, current preview review |

Phases 2 and 3 can proceed independently after their shared contracts are settled. Phase 5 is a native preview milestone; phase 7 is full completion. These are ordered deliverables, not promised calendar durations. Platform storage and sandbox spikes determine estimates.

## Phase 0: Prepare without losing POC evidence

- [x] Record live POC findings and create this full-feature spec using the bundled helper.
- [x] Refresh selected reference clones; both were up to date on October 11, 2026.
- [x] Review the proposed release scope and contract decisions before implementation.
- [x] Run the bundled prepare-spec workflow for `openai-subscription`, creating `feature/openai-subscription` worktrees from configured origin defaults. Do not modify reference-clone working trees.
- [x] Inventory POC changed files/tests and retain its worktrees/credentials for comparison; no automatic cleanup, merge, or token import.
- [x] Load each repository's configured context in order; record baseline checks and applicable nested guidance.

## Phase 1: Resolve contracts and technical risks

- [x] Finalize `OpenAiAuthConfig`, account IDs, validation, additive factory/runtime dependency argument, and backward-compatibility examples; record an architecture decision.
- [ ] Test maintained secret-store dependency candidates on Node 20+ and clean macOS/Linux/Windows installations; select a backend and explicit fallback policy.
- [ ] Prove whole-secret-record replacement and generation recovery with the chosen store; prototype cross-process locks and crash recovery, including PID reuse/abandoned owners.
- [x] Confirm model catalog validation and available metadata without assuming capacity fields; specify catalog freshness and budget provenance.
- [ ] Prototype scoped host-to-Docker credential transport on supported platforms; document mount exclusions and feasibility before committing to full support.
- [x] Map new errors onto runtime context-length/retry/cancellation handling; define subscription capability checks and diagnostic redaction ownership.

Exit: implementers can construct a subscription provider from resolved config and an explicit token source, with no ambiguity about registration ownership, billing, storage, or platform scope.

## Phase 2: Account lifecycle in propio-agent

- [x] Port POC callback/OAuth behavior into production modules; retain state/nonce/PKCE and signed-ID-token tests.
- [x] Add versioned registry, immutable local account IDs, stable labels/host ID, pending registration handling, and verified client/subject association.
- [ ] Implement OS secret backends and protected-file fallback with permission/path validation; keep all writers behind one locking/atomicity protocol.
- [x] Add near-expiry renewal, double-process rotation, generation checks, safe transient errors, registration-specific terminal invalidation, and persistence failure after successful remote rotation.
- [x] Support safe returning ID hints, no-browser URL behavior, enable-plan consent, and one-time plan-use explanation.
- [x] Implement revoke/clear/logout with bounded backoff, local cancellation, registration retention, and remote-unconfirmed reporting.
- [x] Add auth command parsing/routing before ordinary config/MCP/workspace startup; safe status/accounts output and noninteractive exit behavior.

Exit: a real user can sign in, restart, renew, reauthorize, and sign out without tokens appearing in application outputs or another registration being changed.

## Phase 3: Subscription provider in propio-providers

- [x] Port the focused POC adapter and shared strict-completion hooks; give it production naming and a supported explicit constructor.
- [x] Update config types/validator and the normal factory; legacy missing-auth API configs remain valid and subscription/API conflicts are rejected.
- [x] Resolve a fresh bearer token per attempt through injected credentials; protect cancellation and trace boundaries; subscription construction never reads an API environment key.
- [x] Apply documented request allowlist, developer instructions, full-history replay, tool namespaces, commentary, and opaque continuation ordering.
- [x] Refine errors with safe metadata and typed runtime compatibility; context length, usage limit, unsupported capability, policy, and transient admission are distinct.
- [x] Gate pending tool calls on response.completed; cover partial text, pending calls followed by failure, incomplete, malformed/truncated SSE, cancellation, and reader cleanup.
- [x] Preserve diagnostic/retry/request-attempt/payload-capture behavior and clearly classify usage as reported/partial/unavailable, without invented charges.
- [x] Add capability handling for supported inputs and reject unsupported hosted routes/tools; retain existing API/Meta tests.
- [x] Document factory/constructor examples and credential-source ownership for standalone package consumers.

Exit: provider package tests/build/format/Fallow pass; a standalone application can use renewable subscription credentials without Propio-specific paths or UI.

## Phase 4: Standard Propio experience

- [x] Build guided OpenAI setup: choose API or ChatGPT, select/add account, discover model, resolve budget, create a provider entry, choose session/default scope.
- [x] Implement account-specific model catalog client/cache, safe stale/catalog-error states, refresh on grant/account changes, and unavailable default handling.
- [x] Extend `/model` with access-mode/account labels and discovered eligible selections while preserving existing provider menus.
- [x] Add `/account` management, registered-account selection, plan-disabled recovery, and safe no-config/noninteractive paths.
- [x] Prepare async dependencies before Agent selection; keep synchronous factory and existing API-only construction/switch behavior usable.
- [x] Pin token source to immutable account ID; show `Using ChatGPT plan`/Manage usage and make persistent selection explicit.
- [ ] Test cancellation at every setup step and config-write failure after session selection; no failed flow overwrites current defaults/account.

Exit: the feature is usable through the ordinary CLI and model menu without POC commands or manual JSON edits.

## Phase 5: Full native workflows and preview

- [x] Exercise the normal AgentRuntime with existing built-in tools, permissions/approvals, and client-side MCP functions; remove dependence on the demo harness.
- [x] Bind turns and background summaries to immutable access/account/config revisions; test account/model switches while summaries are pending.
- [x] Update session/recovery serialization with optional safe account/mode references and no credentials; support legacy resume and signed-out/removed-account recovery.
- [x] Implement new-conversation default on registration/workspace change and explicit transcript transfer; handle incompatible opaque continuation and incomplete tool rounds safely.
- [ ] Verify context shrinking and summaries through the subscription path; test output/incomplete recovery without unsupported request parameters.
- [x] Validate image capability/input behavior; keep unverified features disabled or accurately unsupported.
- [ ] Audit redaction across browser errors, CLI/debug files, tracing/payload capture, session exports, recovery journals, config snapshots, and support messages.
- [x] Implement recoverable same-host POC migration under both lock protocols; preserve issued client/host IDs and disable the migrated source token set.
- [ ] Run live normal-tool, MCP, text/history, summary, session-resume, refresh, and logout/relogin checks; record safe metadata in a new full-feature verification log.
- [ ] Release/document native preview only after platform gates; until phase 6 passes, subscription sandbox reports a clear unsupported state.

Exit: native subscription access works as an ordinary Propio provider across complete conversations and internal inference; limitations are documented and no unsupported sandbox claim is made.

## Phase 6: Subscription sandbox

- [x] Implement private per-run host credential broker scoped to a selected registration, with host-owned store/refresh and narrow token-get capability.
- [x] Integrate wrapper/delegation startup, container transport and broker teardown; preserve existing API sandbox behavior.
- [x] Exclude production credential directories from broad mounts, including explicit file fallback; do not expose refresh/ID tokens to containers.
- [x] Enforce caller authentication, request bounds, selected-account scope, no account-list/revoke/write API, and sanitized failures.
- [ ] Verify socket/Windows transport and Docker Desktop behavior, concurrent native/sandbox renewal, long sessions, logout, cancellation, crash cleanup, and daemon/host unavailability.
- [x] Document exact supported platform combinations and clear unsupported cases; do not substitute a broad writable ~/.propio mount.

Exit: supported sandbox combinations can continue through access-token expiry while renewable credentials remain host-owned and existing sandbox isolation is preserved.

## Phase 7: Publish and close acceptance

- [x] Publish a backward-compatible provider release using its normal release process; update agent dependency to that compatible version (`0.6.0`).
- [ ] Install published artifacts in a clean consumer with no local links; verify ESM/public exports, native dependencies, Node baseline, auth commands, and normal API/subscription flows.
- [ ] Re-run required provider/agent checks and supported-platform acceptance; review current official preview constraints and applicable local/open-source distribution availability.
- [x] Document setup, API coexistence, account labels, credential storage/fallback, usage/credits, summaries, migration, logout/recovery, capability limits, and sandbox support.
- [x] Update ordinary README/help/config examples and troubleshoot guides; keep safe POC evidence as provenance.
- [ ] Verify every R1–R20 item and create focused PRs per repository, with provider dependency ordering and concrete verification.
- [x] Retire POC-only command wiring from production work only after replacement verification. Preserve POC worktrees unless the user asks to close them.

## Remaining acceptance gates

Unchecked composite tasks above distinguish implementation from acceptance. OS/protected storage, logout, ordinary tools/MCP/summaries, privacy, and sandbox code are implemented and exercised by automated tests; cross-platform and full live acceptance are incomplete. Cancellation/default tests cover API setup at every prompt and failed persistence; browser/account/model cancellation needs interactive production acceptance. Full privacy review and live context shrinking remain open. The packages have been released with documented limitations; release does not establish full platform/live acceptance.

- [x] Actual macOS Keychain whole-record replacement/read/delete.
- [x] Actual kernel lock contention between processes and SIGKILL recovery; simulated rotation/persistence failure recovery.
- [x] Actual macOS/Colima scoped broker transport with dummy tokens; read-only mount/exclusion tests.
- [ ] Linux Secret Service and clean Windows private ACL/storage/lock acceptance.
- [ ] Full implementation live sign-in, ordinary built-in/MCP tools, summary, save/resume, renewal, logout/relogin, and sandbox expiry/long-session acceptance.
- [ ] Docker Desktop and other platform transport acceptance.
- [x] Compatible provider publication and agent dependency promotion; registry dependency verified without local links.
- [x] Agent package publication (`1.4.0`) after review and merge.
- [ ] Complete clean-consumer, platform/live acceptance and distribution review beyond the recorded registry checks.

## Verification matrix

| Area | Required cases |
| --- | --- |
| Config/factory | Legacy API JSON, explicit API, subscription, unknown/empty mode/reference, conflicting key, missing resolver, OPENAI_API_KEY present during subscription, standalone import |
| OAuth | New and returning clients, same-email distinct registrations, identity mismatch, forged signature, wrong nonce/audience/issuer/time, declined scopes, cancellation, late callback, no-browser safe URLs |
| Storage/rotation | macOS/Linux/Windows backends, explicit fallback permission checks, corrupt records, atomic crash points, double process, stale-owner/PID reuse, terminal vs transient refresh, logout racing refresh |
| Requests/streams | Developer instructions, namespace/function replay, encrypted continuation, forbidden fields, HTTP detail/non-JSON errors, real context length, failed/incomplete/EOF after text/calls, abort/idle cleanup |
| UI/defaults | Fresh setup, existing API user, session-only/default selection, account add/switch, catalog disappearance/failure, plan-disabled, noninteractive use, failed save, billing label and usage link |
| Runtime/sessions | Built-in harmless tool, client MCP, permission denial, multi-round tools, summary, compacted history, save/resume/recovery, registration switch during background summary, explicit history transfer |
| Privacy/traces | Sentinel tokens never appear in any log/export/error, ID hints absent from displayed URLs, credential source absent from snapshots, request IDs preserved, failed usage not reported as successful |
| Migration | Same-host POC import, existing registration collision, unrelated profile preserved, concurrent POC refresh refused/serialized, crash at transfer points, source disabled after commit |
| Sandbox | Read-only config, no renewable-token mount/access, caller scope, expiry/rotation, concurrent host clients, logout/crash/cancel, cleanup, Docker Desktop/platform transport |
| Live acceptance | Real text/tool/history plus normal tools/MCP/summary/resume; refresh and logout/relogin; second model/account where available; supported sandbox long-session renewal |

Each repository must run its required unit tests, TypeScript build, formatting check, and Fallow audit. Live tests are opt-in, account-specific, consume allowance, and store only stage/model/account label/error metadata. Do not exhaust a real account to test limits: use simulated admission/stream failures for that coverage. Record skipped platform/live tests explicitly; they block the relevant support claim rather than silently passing.

## Completion and worktree lifecycle

Implementation was performed in prepared `openai-subscription` worktrees. Subsequent user requests separately authorized review PRs, dependency promotion, merges, release, and cleanup. Both specs were closed with the bundled helper after explicit `--acknowledge-unpushed` authorization. POC source was first committed locally (`5e57012` providers, `e66d06d` agent); all four worktrees were removed. Local branches, spec documents, and POC credentials were retained. Remaining acceptance gaps stay unchecked.

## Follow-up: documented prompt budgets

The user reported successful local use and authorized automatic documented defaults on October 11, 2026.

- [x] Verify official model documentation and add exact-ID limits with source URL/check date; keep undocumented catalog fields out of capacity resolution.
- [x] Preserve saved budgets for the selected registration/model; use documented context minus maximum output, bounded by documented input, for recognized unsaved models.
- [x] Add setup and `/model` adjustment before applying session/default scope: `documented`, a verified number, or explicit `conservative`.
- [x] Keep API behavior and the provider package contract unchanged; retain explicit entry for unknown IDs and future snapshots.
- [x] Test automatic selection, saved precedence/account isolation, adjustment/persistence, unknown fallback, metadata and cancellation; rerun agent checks and record actual results.
- [x] Update setup documentation and implementation decisions. No new live/platform acceptance or publication is claimed.

## Follow-up: commit and review PRs

- [x] Re-run provider and agent test/build/format/Fallow gates against the linked feature implementation.
- [x] Commit and push both `feature/openai-subscription` branches after explicit user authorization.
- [x] Create cross-linked draft review PRs: [providers #17](https://github.com/esack7/propio-providers/pull/17) and [agent #101](https://github.com/esack7/propio-agent/pull/101).
- [x] Document dependency order and remaining acceptance gates in both PRs. Compatible provider publication, agent dependency promotion, merging and cleanup remain separate.

## Follow-up: provider PR review

- [x] Preserve typed/safe generic HTTP errors; bound generic 429 admission retries while stopping plan usage-limit and ambiguous replay retries.
- [x] Make subscription idle timeout configurable in the constructor/factory, default to five minutes and test chunk-reset/cleanup.
- [x] Restore legacy OpenAI/Meta API cancellation behavior while retaining subscription caller reasons; keep error translation non-throwing.
- [x] Skip API-key environment reads with an application token source and fail closed for invalid JavaScript credential callbacks.
- [x] Capture failed-response usage before rejecting the stream; retain strict tool/completion admission and fix documentation/import/test nits.
- [x] Run complete provider checks and linked agent build/tests; record simulations separately from earlier live evidence.
- [ ] Optional factory options-object overload: deferred as a separate API ergonomics change.

## Follow-up: live provider approval evidence

- [x] Confirm existing production sign-in and plan permission without importing POC credentials.
- [x] Verify actual expired-credential renewal and discovery through production application auth.
- [x] Run two real `gpt-6.1-sol` subscription requests with one local echo tool call and confirmed result continuation; require HTTP 200 and `response.completed` in both rounds.
- [x] Record sanitized actual request shapes/SSE counts and assertions for provider review. At the user's request, revert the provider evidence-doc commit before merge; retain the verification summary here. Credentials/conversation/opaque data were not committed.
- [x] Update review evidence and document that existing sign-in was reused, error handling remains simulated, and complete normal-Agent/platform acceptance is separate.

## Follow-up: agent review, release, and closeout

- [x] Replace browser-held credential locking with a separate sign-in lock; preserve generation/logout checks at commit.
- [x] Preserve tokens after transient refresh failures and require recovery only for uncertain rotation or failed persistence after rotation.
- [x] Confirm conversation handling before access/account changes in `/model` and `/account setup`, including API destinations.
- [x] Resolve startup defaults without mandatory catalog access; avoid repeated account/broker lookup.
- [x] Preserve legacy API setup, fresh disk persistence, session-only provider budgets, and unrelated saved entries; remove unused budget sidecars.
- [x] Keep sandbox channels for their owner lifetime and report invalid configuration safely.
- [x] Pass final agent checks: 116 suites / 1,733 tests, build, formatting, Fallow audit/check, and GitHub Node 20/24.10.0 CI.
- [x] Merge providers #17 (`010d330`) and agent #101 (`efa1de8`) after review.
- [x] Confirm npm releases providers `0.6.0` and agent `1.4.0` with matching merge `gitHead` values.
- [x] Preserve POC source as local-only commits, close both specs using the bundled helper, and verify all four worktree removals and retained branches/documents/credentials.
- [ ] Deferred: slow-network login commit lock wait; optional factory API ergonomics and typed sandbox configuration errors.

The remaining platform/live criteria above were not promoted to passing during release or cleanup. Final results, historical failures, and recovery instructions are in [verification.md](verification.md).
