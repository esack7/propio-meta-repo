# Requirements: openai-subscription

## Summary

Integrate ChatGPT subscription sign-in into normal Propio provider, account, model, session, and sandbox workflows, alongside existing OpenAI API access.

Status: merged and published as `@propio-ai/providers@0.6.0` and `@propio-ai/agent@1.4.0`; feature and POC worktrees closed after user-authorized preservation, October 12, 2026. Remaining live/platform acceptance gaps are retained. Repository scope carries forward the user's explicit confirmation of `propio-providers` and `propio-agent`. Actual evidence and unresolved gates are recorded in [verification.md](verification.md); contract decisions are in [decisions.md](decisions.md).

## Evidence and confidence

The [POC findings](../openai-subscription-poc/findings.md) establish live browser sign-in, account-specific discovery of seven visible models, and successful text streaming, local tool execution/result replay, and conversation continuation on `gpt-6.1-sol` for one account. The POC passed 423 provider tests and 1,650 agent tests.

Production expired-credential renewal, discovery, and a live text/tool-result continuation passed during provider review. The user also reported successful local use of the full implementation. Detailed ordinary built-in/MCP, summary/session, logout/relogin, second-account/model, and long-session sandbox acceptance remains unverified; images stay unsupported. Passing POC tests is a useful baseline, not acceptance of every production criterion. POC source is preserved in local-only commits on the retained `feature/openai-subscription-poc` branches; its worktrees have been removed and its credentials retained.

## Goals

- Let users choose OpenAI API access or ChatGPT plan access in ordinary Propio usage, including `/model`, saved defaults, session resume, tools, and context summarization.
- Provide browser sign-in and account/workspace registration management with reliable renewal and explicit billing behavior.
- Keep token handling in the application and preserve a reusable, application-independent provider package.
- Discover models for the selected account without requiring model-name allowlists in providers.
- Protect tokens across restarts, concurrent processes, diagnostics, sessions, and supported sandbox operation.
- Deliver a staged implementation with native preview first and sandbox support required before declaring the full feature complete.

## Non-goals

- Importing another application's credentials, private ChatGPT backend access, or access to existing ChatGPT conversations.
- Silent fallback from subscription access to API-key billing, switching accounts after an error, or automatically changing credit/plan permissions.
- A second model/tool runtime, app-server integration, or redesign of Propio's agent-core abstraction.
- Enabling currently unsupported hosted Responses tools, audio/video routes, or a generic raw Responses parameter passthrough.
- Paid remotely hosted Propio deployment, a multi-user OAuth service, device-code sign-in, or remote VM credential transfer in this release. These require separate designs and integration eligibility review.

## User experience

1. Existing OpenAI users continue with their current API configurations. When adding OpenAI access, the user chooses **API key** or **Continue with ChatGPT**.
2. ChatGPT sign-in opens the system browser; an interrupted or declined sign-in leaves the user's current provider/account selection intact.
3. Successful plan authorization displays a one-time explanation that eligible requests use the ChatGPT plan or permitted credits, with **Manage usage**. Successful identity sign-in without plan permission is retained but cannot run inference.
4. The normal model menu labels each OpenAI entry as **API** or **ChatGPT plan**, shows the active account label for subscription entries, and lists eligible account-specific choices.
5. New users can complete subscription setup without manually writing JSON: sign in, choose a model, use verified documented limits where available or explicitly choose a verified/conservative working budget, then choose whether to use it for this session or as a default. Preserve saved budgets and allow explicit adjustment before applying the selection.
6. Normal conversation, built-in tools, client-side MCP tools, and summaries use the selected access mode. Local permission, approval, and sandbox rules continue to apply to tool execution.
7. At a usage limit, stop requests and offer **Manage usage** first. Switching to an API entry is a deliberate user action; never replay a partially completed turn automatically.
8. Account switching defaults to a new conversation when changing the ChatGPT registration/workspace. Continuing the current transcript in another account requires an explicit, visible choice.
9. Sign-out stops new requests for that registration, attempts revocation, clears local tokens, and reports whether remote revocation was confirmed.

Proposed commands, finalized in [design.md](design.md): `propio auth login openai`, `propio auth accounts openai`, `propio auth status openai`, `propio auth enable-plan openai`, and `propio auth logout openai`, with `--account <label>`. These commands work without a provider configuration or MCP startup. `/model` remains the normal session selector; `/account` adds account management within the terminal UI.

## Acceptance criteria

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| R1 | Backward-compatible OpenAI configuration | Missing auth mode selects API access; existing key/environment resolution and other providers pass regressions; merely signing in never changes defaults |
| R2 | Explicit subscription configuration | `type: openai` with `auth.mode: chatgpt` references one stable account ID; mixed API secrets/subscription config is rejected; no API fallback even with OPENAI_API_KEY set |
| R3 | Renewable caller-owned credentials | Provider factory supports an additive injected credential source; provider constructors perform no browser, config-path, or credential-store discovery |
| R4 | Correct OAuth and identity | Fresh PKCE/state/nonce; issued client ID; verified issuer/audience/signature/expiry/identity; exact loopback callback; cancellation/denial/mismatch cannot replace the active registration |
| R5 | Account/workspace boundaries | Registration identified by issued client ID plus verified identity, never email; stable host ID; labels can differ for registrations with the same email; switch/relogin preserves correct mappings |
| R6 | Protected persistence | Supported native platforms have tested OS secret storage or explicitly selected protected file storage; secrets never enter providers.json, sessions, URLs printed to terminals, telemetry, or debug logs |
| R7 | Safe renewal and logout | Atomic token-set replacement under cross-process serialization; terminal refresh errors clear only the selected token set; transient failures preserve it; logout does not recreate clients |
| R8 | Normal setup and selection | New-user setup, `/model`, `/account`, saved defaults, restart, and noninteractive errors work; status displays access mode/account safely |
| R9 | Model discovery and context budget | Catalog fetched for the selected account; only visible slugs displayed in server order; removed models are explained; context budget has an explicit source and is never asserted to be catalog capacity without evidence |
| R10 | Subscription request compatibility | Public Responses endpoint, stream true/store false, developer instructions, full history replay, namespaced local tools; reject or omit unsupported fields according to documented policy |
| R11 | Confirmed stream completion | Only response.completed establishes success; incomplete/failed/error/EOF cannot dispatch pending tools or become successful summaries; cancellation and partial output have distinct outcomes |
| R12 | Existing error recovery | Genuine context-length failures retain ProviderContextLengthError compatibility; usage, capability, policy, admission, authentication, and transport failures retain safe structured metadata |
| R13 | Normal tool loop | Live built-in harmless workspace read and client-side MCP function execution pass; permissions/approvals are unchanged; no local tool side effect before confirmed provider completion |
| R14 | Sessions and summaries | Save/resume preserves needed opaque continuation without tokens; summaries use the same pinned access/account binding; account switches do not redirect pending background work |
| R15 | Diagnostic privacy and attribution | Existing retry/tracing works with subscription adapters; safe access-mode and opaque account identity recorded; tokens/ID hints/auth URLs omitted even with debug/payload capture enabled |
| R16 | Input compatibility | Text works; images are enabled only after capability checks and live verification; unsupported upload/audio/video/hosted-tool features fail clearly before submission |
| R17 | Sandbox support | Host-mediated renewal works with read-only config mount; container has no refresh/ID token access; scoped access ends with sandbox lifetime; secret-store directory is not broadly mounted |
| R18 | Migration and distribution | Provider published first, compatible agent dependency installed and tested in a clean consumer; explicit same-host POC migration avoids duplicate registration/rotating-token races |
| R19 | User-controlled costs | Manage usage link; no invented dollar charge/remaining quota/reset time; summaries are disclosed as using the selected account; no code changes permitted-credit settings |
| R20 | Release verification | Unit/contract, native-platform, and live integration gates in tasks.md pass; POC success is not substituted for full feature verification |

## Affected repositories

`repos.txt` is helper-generated from the previously confirmed exact repository list:

- `propio-providers`: shared config validation/factory, renewable credential contract, subscription Responses adapter, capabilities, structured errors, provider traces, reusable package tests/docs.
- `propio-agent`: OAuth, secret storage, account registry, model discovery/setup/UI, agent wiring, session/summary handling, migration, sandbox bridge, integration tests/docs.

The meta-repo holds this specification and POC evidence. No other repository is required.

## Open questions

These are implementation checkpoints with recommended defaults, not requests to postpone planning:

| Decision | Recommended default | Closure point |
| --- | --- | --- |
| Credential-store dependency | A maintained Node 20-compatible OS secret-store adapter, lazy-loaded; tested protected-file fallback chosen explicitly | Phase 1 technical spike |
| Cross-process lock dependency | OS-released per-registration lock with generation checks; never infer safety solely from lock age | Phase 1 technical spike |
| Context capacities in subscription catalog | Treat current visible-name/slug fields as discovery only; preserve existing config, otherwise use an exact-ID table of verified documented limits with output reservation, or an explicit verified/conservative budget for unknown IDs | Phase 1/4 catalog contract |
| Sandbox transport across supported platforms | Private host-local scoped credential broker; validate Docker Desktop paths and Windows transport before support claims | Phase 6 spike |
| Returning sign-in hints | Follow current documented id_token_hint behavior, with complete URL redaction; no hinted URL printed by --no-browser | Phase 2 |
| Preview changes and deployment eligibility | Recheck official docs before release; ship local/open-source integration only under applicable availability | Phase 7 |

Detailed architecture, recovery, and source references are in [design.md](design.md); ordered deliverables and verification are in [tasks.md](tasks.md).
