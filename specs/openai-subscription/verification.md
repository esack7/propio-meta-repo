# Implementation verification

Updated October 12, 2026, America/Los_Angeles. Status: implementation reviewed, merged, and published; feature and POC worktrees closed with source/evidence preserved. Full production live/platform acceptance remains incomplete.

## Release and closeout

| Item | Verified result |
| --- | --- |
| Provider review and merge | [PR #17](https://github.com/esack7/propio-providers/pull/17), squash commit `010d330d844d769fee5ef7325ca3be57baf1efe7` |
| Provider publication | [Release v0.6.0](https://github.com/esack7/propio-providers/releases/tag/v0.6.0); npm version `0.6.0` and `gitHead` match the provider merge |
| Agent registry dependency | `@propio-ai/providers@0.6.0` pinned in package and shrinkwrap; checks ran against the installed registry artifact without a local provider link |
| Agent review and merge | [PR #101](https://github.com/esack7/propio-agent/pull/101), squash commit `efa1de8f4e5b1c06eeb5cdb59400add89fb059ba` |
| Final agent unit suite | 116 suites / 1,733 tests passed, including 30 review regression cases |
| Final agent checks | Build, full formatting, whitespace, Fallow audit with all gates against `origin/main` (zero issues in 41 changed files), and Fallow check passed |
| Agent GitHub CI | [Run 38271892778](https://github.com/esack7/propio-agent/actions/runs/38271892778) passed Node 20 and 24.10.0 tests/build/format, Fallow, commit convention, and required gate on `7c8649b` |
| Agent publication | [Release v1.4.0](https://github.com/esack7/propio-agent/releases/tag/v1.4.0); npm version `1.4.0` and `gitHead` match the agent merge |
| POC preservation | Local-only commits on `feature/openai-subscription-poc`: providers `5e570123478507300982909809b43fabd6de0fea`, agent `e66d06d162c8a2af722427c3df7a152d7456fe01` |
| Worktree cleanup | Bundled close-spec helper completed for both specs with explicit `--acknowledge-unpushed` authorization; all four worktree directories and registrations were removed |
| Retained state | Both local feature branches in each reference repository, spec documents, and `~/.propio/poc/openai-subscription` credential directory remain |

Agent review commits `e7afe5f`, `d43c880`, and `7c8649b` address transcript confirmation, transient refresh recovery, browser/credential locking, startup resolution, fresh disk persistence, legacy API setup, unused sidecars, owner-scoped sandbox lifetime, session override retention, and sanitized configuration errors. The [final follow-up](https://github.com/esack7/propio-agent/pull/101#issuecomment-6128362610) found no merge blockers. The slow-network login commit lock concern remains deferred. Session settings intentionally take precedence over edits to existing disk entries until restart, and sandbox missing-default diagnostics fall back safely if library error wording changes.

Review authentication and inference tests use simulated HTTP/SSE. The over-eight-hour lifetime case uses a clock jump; API sandbox-host startup/error/cleanup uses actual child processes. No new live OpenAI sign-in/inference was performed for the agent review fixes, package publication check, or cleanup. Earlier POC live tests, the production renewal/tool round-trip below, and user-reported local use remain distinct evidence. Linux/Windows storage acceptance, other sandbox transports, detailed normal tools/MCP/summary/resume/logout acceptance, and live long-session sandbox renewal remain open.

The sections below preserve the dated implementation/review history. Statements about pending publication, open worktrees, dependency blockers, old lifetime limits, and earlier test totals describe those earlier stages; this closeout supersedes their status. Provider evidence documentation committed in `8c2a77e` was reverted in `22d8b15` at the user's request before merge; its summary remains in this meta-repo, with no raw credential/conversation data included.

## Review PR preparation

### Live tool round-trip follow-up

The next review confirmed the code fixes and requested real endpoint/tool evidence before approval. On October 12, 2026 at 03:32 UTC (October 11 locally), a live check used the existing production `personal` registration with plan permission, production Keychain storage, agent commit `6798a2f` and provider commit `711b4ee` on Node 22.23.3. The access token had expired; production `OpenAiAuth` renewed it before account-specific model discovery, which returned seven visible models including `gpt-6.1-sol`. No new browser authorization, POC credential import or billing/default change occurred.

Two actual public `POST /v1/responses` requests passed with HTTP 200 and observed `response.completed`. The first request used developer instructions and the `functions` namespace containing one harmless `echo_marker` function. Exactly one confirmed tool call had arguments matching a synthetic challenge. The harness executed the echo entirely in memory, replayed the production adapter's assistant call and tool result, and verified the second completed answer incorporated the result without another tool call. The application source was acquired per inference round; retries were disabled. This used the real provider factory and renewable source, with real HTTP/SSE observed by a pass-through temporary harness; no model response was simulated.

The temporary review evidence included a report and sanitized live observation, committed in `8c2a77e` and later reverted before provider merge at the user's request. The observation was checked for semantic equality with the actual temporary capture before formatting. Only route/request structure, event counts, model/account label and verification assertions were retained. No credential, account/client/subject ID, conversation, argument/result content or encrypted reasoning was committed. HTTP request IDs were not recorded from the headers; response items lacked a namespace field, while outgoing namespace wrappers were accepted. No intentional usage/admission failure was induced; error-code tests remain simulated.

This closes the fresh positive endpoint/namespaced-tool/continuation evidence gap for one production registration/model and verifies real expired-credential renewal. It does not repeat interactive sign-in or exercise ordinary Agent built-in/MCP, summary/session, logout/relogin, long reasoning or sandbox/platform acceptance; those composite gates remain open. The fixed provider source still has 462 passing tests, and the linked agent has 1,703 passing tests as recorded below; this follow-up changes documentation/evidence only. Formatting, full-feature Fallow audit and whitespace checks passed for the evidence addition. The PR description is updated; no review-thread message is posted.

Evidence was committed and pushed as `8c2a77e7bdd4130394e2b34fbee19da7254d9415`. GitHub CI passed on that head, including Node 20 and 24.10.0 formatting/build/tests, Fallow, commit convention and the required gate (runs 38200414313 and 38200538049). Both feature worktrees are clean; the agent commit is unchanged.

### Provider review fixes

The user asked to address the review on [provider PR #17](https://github.com/esack7/propio-providers/pull/17). All three pre-merge issues are fixed: generic HTTP failures retain the typed provider errors with safe metadata and bounded generic 429 admission retries; the subscription idle bound is configurable through constructor/factory with a five-minute default; subscription abort handling is gated away from legacy API providers. Additional fixes remove throws from the subscription error translator, skip API-key environment reads when a token function is supplied, fail closed for an invalid JavaScript token source, and record usage reported in failed SSE before rejecting it. Factory import placement, README section placement/signature and blank-token type assertions were corrected.

| Review check | Actual result |
| --- | --- |
| Provider full unit suite | 21 suites / 462 tests passed; 26 review regressions added |
| Provider build and full formatting | Passed |
| Provider full feature Fallow audit against `origin/main` with all gates | Passed, no issues in 12 changed files |
| Provider Fallow check and whitespace | Passed, zero issues/threshold findings |
| Linked agent build/full suite against updated provider | Passed; 114 suites / 1,703 tests |
| Provider GitHub CI for review commit | Passed on Node 20 and 24.10.0, including Fallow, commit convention and required gate; run 38199500648 |
| Fresh live OpenAI inference or captured wire fixture | Not run/captured |

New regressions simulate HTTP/SSE and use fake timers for long reasoning gaps, chunk-reset and factory timeout cleanup. Coverage checks generic and plan-specific errors/retries, non-JSON admissions, SSE invalid subscriber context, safe echoed-message handling, fresh credentials per admission retry, custom cancellation reasons on subscription vs OpenAI/Meta API paths, failed usage without tool/terminal success, and missing JavaScript token callbacks. Early retry fixtures reused consumed Response bodies and were corrected to create a response per attempt. The new DOMException regression exposed cross-realm `instanceof Error` assumptions; AbortError is now recognized by its name and translated without throwing. Final complete suites passed after correction.

The sixth positional factory argument remains additive; an options-object overload was an optional ergonomic suggestion and is deferred. The original POC live text/namespaced-tool/history successes on `gpt-6.1-sol` and the user's reported local success remain separate evidence. No live wire fixture was fabricated or captured, and no POC credentials/worktrees were changed. Remaining production live/platform acceptance and the agent published-dependency blocker still apply.

Provider fixes were committed and pushed as `711b4eeaaa73fc625a435bd1976a26645f89491c` on the existing feature branch; PR #17's description includes the updated results and cross-repo validation. Provider and agent worktrees are clean; agent source/PR head is unchanged. No review-thread reply, merge, publication or cleanup was performed.

The user explicitly requested commits, pushes and GitHub PRs for both feature repositories. The bundled refresh helper reported both references up to date; the local-package helper confirmed the feature-to-feature provider link. Both worktrees were committed and pushed on `feature/openai-subscription`, and both are clean with local HEAD matching the pushed tracking branch:

- Provider commit `42de4d580685634de79754952a6eca4c2eece2c7`: [draft PR #17](https://github.com/esack7/propio-providers/pull/17).
- Agent commit `6798a2f174203d948cc51f31eeea04c123e5eb36`: [draft PR #101](https://github.com/esack7/propio-agent/pull/101).

Before committing, provider checks passed again: build, 20 suites / 436 tests, full formatting, Fallow audit with all gates, Fallow check and whitespace. Agent checks passed again: build, 114 suites / 1,703 tests, full formatting, Fallow audit with all gates, Fallow check, sandbox shell syntax and whitespace. Inference and OAuth endpoints in automated tests remain simulated; no new OpenAI live checks ran during PR preparation. Existing actual native/container evidence remains as recorded below.

The PRs link each other and describe the unverified live/platform gates. Provider GitHub CI initially passed on Node 20 and 24.10.0 with Fallow and commit convention checks. Agent GitHub CI installs the unchanged published `@propio-ai/providers@0.5.0`, rather than the locally linked feature implementation. The agent remains blocked for merge/release until a compatible provider is published and its dependency/shrinkwrap are promoted; that promotion was not included in this request. Neither PR is merged or published. Meta-repo documents/unrelated local changes were not committed, and original POC worktrees remain intact.

Actual [agent CI run 38196380133](https://github.com/esack7/propio-agent/actions/runs/38196380133) failed on both Node 20 and 24.10.0 during build: the published provider lacks `ProviderRuntimeOptions`, the sixth factory argument and OpenAI `auth` config. Fallow and commit convention passed. The dependency failure is recorded in the draft PR and is not counted as passing validation; local linked-package checks above passed.

## Documented budget follow-up

On October 11, 2026, the user reported testing the implementation locally successfully. That is user-reported live evidence; the individual production acceptance stages and platforms were not specified, so the remaining live/platform gates below are retained.

The follow-up adds exact-ID official model limits and automatic working context budgets in the agent worktree only. Recognized unsaved models select 922,000 tokens, reserving 128,000 from the documented 1,050,000 context window and respecting documented input limits. Saved per-model budgets win; setup resolves them for the same immutable registration. Unknown model IDs require explicit verified or conservative input. Setup and `/model` expose an adjustment before session/default application; `documented` resets a saved selection. Account budget metadata records the source, limits, official URL and check date. The provider contract and API behavior are unchanged. Details and source links are in [decisions](decisions.md) and the agent's `docs/openai-subscription.md`.

| Follow-up check | Actual result |
| --- | --- |
| Agent full unit suite | 114 suites, 1,703 tests passed; 26 tests added for this follow-up |
| Final focused regression after helper extraction | 3 suites, 31 tests passed |
| Agent TypeScript build | Passed |
| Agent full Prettier check | Passed |
| Agent Fallow audit `--gate all` | Passed, no issues in 38 changed files |
| Agent Fallow check `--fail-on-issues` | Passed, zero issues/threshold findings |
| New live inference/sign-in or subscription capacity boundary test | Not run |
| Provider rechecks for this follow-up | Not rerun; provider sources/contract unchanged, earlier results below retained |

The new setup/menu workflow tests use simulated accounts, discovery and runtime preparation with real temporary config/budget persistence. They establish selection behavior, saved-budget preservation and account isolation, override/reset persistence, unknown-model fallback and cancellation without changing current defaults. They do not verify an account-specific 922,000-token subscription request. Official documentation values are defaults, not discovered subscription entitlements. No POC worktree, real credential, reference working tree, publication, merge or cleanup was changed.

## Workspace and provenance

The bundled refresh helper reported both references up to date. The prepare helper created `feature/openai-subscription` from provider `fe34bb5` and agent `946ede9`. Configured context files were loaded in order. The local-package helper linked the feature agent to the feature provider. Both reference working trees remained untouched by implementation.

The original POC worktrees and their uncommitted changes remain in `specs/openai-subscription-poc/repos/`. The end-of-run inventory matches their initial changed-file inventory. No live POC tokens were copied, imported, refreshed, revoked, or deleted. The [POC findings](../openai-subscription-poc/findings.md) remain evidence of that harness's live sign-in/catalog/text/tool/history successes on `gpt-6.1-sol`; those successes do not establish full implementation acceptance.

## Automated results

| Repository/check | Actual result |
| --- | --- |
| Provider `npm test -- --runInBand` | 20 suites, 436 tests passed; 28 tests added to the reference baseline |
| Agent `npm test -- --runInBand` | 112 suites, 1677 tests passed; 43 tests added to the reference baseline |
| Both `npm run build` | Passed |
| Agent final focused regression run after summary cleanup extraction | 6 suites, 200 tests passed |
| Both `npm run format:check` | Passed |
| Both `npm run fallow:audit` | Passed with all gates: provider 11 changed files; agent 35 changed source/config files |
| Both `npm run fallow:check` | Passed; no dead code/duplication issues or above-threshold complexity |
| `bash -n bin/propio-sandbox` and both `git diff --check` | Passed |
| Local `npm pack` / clean consumer | Both packed; ESM public exports, subscription factory, legacy API factory, no constructor credential reads, and auth help passed without local package symlinks |
| Local Docker image | Node 20.20.2 Alpine build passed with the local provider artifact; subscription provider and application auth exports load in the resulting image |

Unit/integration inference is simulated HTTP/SSE, not live OpenAI inference. OAuth tests use real loopback callback servers and cryptographically signed test identities with simulated discovery/token endpoints. Runtime tests execute an actual harmless workspace read and an actual subprocess stdio MCP server through ordinary Agent machinery with simulated model responses. Summary/session tests use the production paths and simulated responses.

Coverage includes config/billing conflicts, missing credential source, API environment isolation, request allowlist/history/namespace replay, typed context-length errors, safe HTTP/SSE errors, pending tool failure/incomplete/EOF, caller abort, idle timeout and reader cleanup. Account tests cover PKCE/state/nonce/signature/issuer/audience/expiry/client/subject, returning hints, permission-disabled grants, terminal/transient renewal, durable-generation recovery and blocked uncertain rotation. Storage/migration tests use dummy records; they cover OS lock ownership, protected paths, source-lock collision and selected-source retirement. Selection tests cover cancelled API setup at every prompt, session-only/default preservation and failed default persistence. Catalog tests cover server order, visibility, cache copies, generation/account separation, forced refresh, invalid payload and cancellation. Existing provider/runtime permission regressions pass.

One agent run was interrupted by rebuilding the linked provider while its tests were reading the provider output. Its failures were module-not-found errors. After the provider build completed, a sequential full rerun passed 1676/1676 (before the added logout cancellation test). An early Docker check found that pruning restored the published provider; the development artifact is now reapplied after pruning, and the resulting image's exports passed. A final cancellation regression caught changed API signal identity; cancellation was restricted to subscription requests and the original API signal is preserved. These failed attempts were corrected, not counted as successful verification.

## Actual native/container checks

- macOS Keychain: wrote a dummy whole record, replaced generation 1 with generation 2, read it back, and deleted the temporary entry. Passed using the production backend. No actual OpenAI credential was used.
- Kernel locking: an independent Node process held the permanent lock; another acquisition could not enter, cancellation stopped its wait, SIGKILL released ownership, and a subsequent acquisition succeeded. Passed. Refresh HTTP exchanges in tests remain simulated.
- macOS/Colima Docker transport: a real container used the production broker client against a loopback host broker. Two calls received different dummy access tokens; another account was rejected; the descriptor contained only its scoped capability and safe metadata. Container exit 0, two broker requests. Passed. This is transport/renewable-source evidence, not real OAuth expiry evidence.
- Mount view: automated tests exclude POC tokens, production OpenAI auth files and symlink aliases; the view is owner-only and mounted read-only. The wrapper rejects a workspace ancestor that would expose credential directories through `/workspace`. Broker requests are bounded/authenticated/scoped, failures sanitized and lifecycle closure tested.

Colima did not share `/var/folders` temporary mounts. Configuration/channel temporary directories were moved under the user home directory. The eight-hour broker lifetime requires sandbox restart afterwards.

The local Docker build reported existing dependency engine/audit warnings (including release-tool engines newer than Node 20). It completed. No unrelated dependency upgrade or security remediation was performed. Clean local package runtime imports were also checked on Node 20 separately from native storage acceptance. The development image is tagged `propio-openai-subscription:local`; the user's existing compose image was not replaced during this verification.

## Acceptance gaps at the initial implementation handoff

The production `personal` registration was still signed out at the final status check (`connected: false`, no saved profiles). A browser sign-in requires the user's interaction. No new production live sign-in, model discovery, inference, built-in/MCP tools, context shrinking/summary, session resume, real refresh, logout/relogin or long-session sandbox run was claimed. The user was asked to sign in from a separate terminal; no response or signed-in registration was available during this run.

Linux Secret Service and clean Linux installation/rotation acceptance were not available. Windows private ACL handling is not implemented/verified; credential operations explicitly fail closed. Native Linux/Windows subscription sandbox startup is explicitly unsupported pending transport proof. Docker Desktop and other platform combinations remain unverified. These gates block those support claims and full feature acceptance. macOS/Colima is a transport preview pending live acceptance, not a release declaration.

Interactive subscription account/model cancellation, a full privacy review across every output route, a second account/model, and every migration crash point still need acceptance review. Images remain disabled. Local `/account` logout cancels the selected registration’s foreground/background requests; an automated test checks account scope and reader cleanup. Already admitted requests in another process cannot be recalled by logout; new credential acquisition is blocked first.

R1–R3, R9–R12, R16 and R19 have automated implementation evidence. R4–R8 and R13–R17 have implementation/test evidence with live/platform gates pending. R18 publication and published-consumer evidence are excluded from this request; local tarballs and simulated migration are verified. R20 and full feature completion remain open until the required live/platform/release gates pass.

## Local acceptance instructions

Use the released CLI from the directory you want as your workspace:

```sh
npm install -g @propio-ai/agent@1.4.0
propio auth login openai --account personal
propio setup openai
propio
```

Choose Continue with ChatGPT, the signed-in account, a currently eligible model, a verified capacity or the explicitly conservative prompt budget, and the desired session/default scope. `/model` and `/account` provide normal selection/management. Read a harmless local file, exercise an existing client MCP function, continue the conversation, save/resume under the same registration and trigger a context summary. Repeat after access-token expiry, then logout/relogin. Check the visible plan/account/summary disclosure. Live requests consume allowance; test limit/error cases with simulations rather than exhausting it.

The [released agent guide](https://github.com/esack7/propio-agent/blob/efa1de8f4e5b1c06eeb5cdb59400add89fb059ba/docs/openai-subscription.md) covers account commands, setup, protected storage, recovery, capabilities, and sandbox limitations. No local package link is required for ordinary installs.

For further source work, reopen the relevant legacy spec with the bundled prepare-spec helper and explicit retained-branch reuse authorization (`--reuse-branches`). The POC's local-only branches contain the preservation commits above; its original guide is in `docs/openai-subscription-poc.md` in the restored agent checkout. Keep feature-to-feature package links separate from reference checkouts. Each source repository's reproducible checks are `npm test -- --runInBand`, `npm run build`, `npm run format:check`, `npm run fallow:audit -- --base origin/main`, and `npm run fallow:check`. Do not rebuild a linked provider during agent tests.
