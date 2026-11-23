# Design: openai-subscription

## Overview

Integrate ChatGPT subscription sign-in into normal Propio through the existing provider contract and agent runtime. Keep browser authentication, renewable sessions, storage, and account selection in `propio-agent`; keep wire formatting, capabilities, errors, and streaming in `propio-providers`.

Design recorded October 11, 2026 and reconciled with the released implementation October 12, 2026. The [POC](../openai-subscription-poc/findings.md) confirms the direct public Responses route for one account/model. The implementation was merged and released in providers `0.6.0` and agent `1.4.0`; remaining platform/live acceptance gaps are in [verification.md](verification.md). POC branches remain local reference implementations. Feature and POC worktrees have been closed with source and evidence preserved.

## Approach

### 1. Extend the existing OpenAI configuration

Keep `type: "openai"`. Introduce an optional discriminated `auth` object:

```ts
type OpenAiAuthConfig =
  | { mode: "api-key" }
  | { mode: "chatgpt"; accountId: string };
```

Absent `auth` is legacy API access. Explicit `api-key` uses current `apiKey`/`OPENAI_API_KEY` rules. Explicit `chatgpt` resolves only the supplied account registration; reject `apiKey` alongside it and never consult API-key environment variables on that path. Reject unknown modes and empty account references. Other provider schemas remain unchanged.

Example subscription entry after setup:

```json
{
  "name": "openai-personal",
  "type": "openai",
  "auth": { "mode": "chatgpt", "accountId": "account-local-uuid" },
  "models": [
    { "name": "GPT-6.1-Sol", "key": "gpt-6.1-sol", "contextWindowTokens": 128000 }
  ],
  "defaultModel": "gpt-6.1-sol"
}
```

The example's 128000 is a selected conservative prompt budget, not a claim of model capacity. Persist the selected budget in `providers.json`; documented source URLs/check dates live in the agent's exact-ID limit table. No separate budget sidecar is written. Keep the provider's existing required positive `contextWindowTokens` contract. Both API and subscription entries can coexist under distinct provider names. Logging into an account changes no existing default until the user selects it.

### 2. Inject credentials without changing synchronous factory behavior

Add an optional sixth options argument to `createProvider(config, modelKey?, diagnosticListener?, debugEnabled?, retryConfig?, runtimeOptions?)`, preserving all existing positional arguments. The options supply a typed caller-owned OpenAI credential resolver. A subscription factory call without it produces an actionable credential-source error; it does not search the user's filesystem. Existing explicit `OpenAiProvider` construction keeps its API behavior. Promote the POC `OpenAiSubscriptionProvider` into the stable package surface with a production identity and documented options.

The resolver returns an asynchronous token getter bound to one immutable account ID, never the globally active UI account. Get a current access token immediately before each network attempt, honoring cancellation. Only the agent credential manager refreshes or reads the secret store. Construction remains synchronous, while token retrieval can fail asynchronously before network submission. Redact the callback/options from configuration snapshots.

Keep `LLMProvider`, `ChatRequest`, and `ChatStreamEvent` contracts. Add optional capability fields only where a real agent consumer needs them; do not introduce a second agent loop or provider-owned OAuth client. Keep tracing wrappers and retry listeners applied through the normal factory path.

### 3. Promote OAuth and account management

Move the POC auth/callback/store logic into focused production modules under `src/auth/openai/`; use a general credential-store interface only where OS storage and sandbox consumers require it. Reuse signed-token/callback tests and replace POC-only names/paths. Use actual app name `Propio` for initial registration.

An agent-owned account registry contains versioned registration metadata: opaque local account ID, stable user label, issuer, verified subject, issued client ID, host ID, optional display email/workspace label, secret-store reference, and state/version. Email is display data, not an account or workspace key. Do not invent a workspace identifier from email or subject. Bind the validated identity to its issued client ID, which represents the registered workspace. An interrupted first registration may retain its issued client ID in a pending record but cannot become active without verified identity.

Persist one UUID-based `urn:uuid:` host ID per Propio installation for the initial release, continuing the POC's documented supported format. Tool restarts, logout, and local sandbox processes delegated by that installation reuse it; a separately provisioned machine is a new host. Public-key-derived IDs can be introduced with an explicit lifecycle/migration later. [S1]

Browser flow:

Request `openid profile email offline_access resource.invoke chatgpt.tokens.use.direct` and `resource=https://api.openai.com/v1`. Use `https://auth.openai.com/api/accounts/authorize` for browser authorization, `https://auth.openai.com/api/accounts/oauth/token` for code/refresh exchange, and trusted OpenID discovery for JWKS/revocation. Never send client secrets: this is a public-client flow. [S2]

1. Prepare a pending registration/attempt; start a loopback listener on `127.0.0.1:<available>/auth/callback` before opening the system browser.
2. Use fresh random state, nonce, and PKCE S256 per attempt. New registrations use dynamic_agent_client; existing ones use their saved issued client ID and omit agent_name_hint.
3. Keep the exact redirect URI/resource across authorization and token exchange. Validate callback state before denial/error handling. Require an issued client ID for new registration and reject a changed one for returning sign-in.
4. Verify ID-token signature using published JWKS and validate issuer, audience, time claims, nonce, and subject. Returning sign-in must match the stored identity.
5. Validate token-response grants. Plan permission is separate from identity. Commit the token set before making the account selectable for inference; failed or cancelled flow leaves current selection intact.
6. Close listeners and clear temporary state/codes on all exits. Requests have timeouts and cancellation; endpoints are restricted to the trusted OpenAI auth service.

Returning sign-in follows current docs: send retained id_token_hint only to OpenAI's authorize endpoint; login_hint is optional and must belong to the same registration. This is a deliberate change from the POC, which omitted the ID hint. The browser launcher may use the full hinted URL internally, but terminal output, errors, traces, and support reports must never contain it. For `--no-browser`, omit the ID hint and show a safe authorization link; suppress email hints from printed links too. Tokens/codes are never echoed. [S2], [S3]

`enable-plan` repeats OAuth with the complete scope set and supported explicit-consent parameter. Use `prompt=consent` unless force_reconsent rollout is confirmed for this integration; ordinary sign-in does not force consent. Declining plan permission leaves a recognized signed-in account in a plan-disabled state, with enable-plan or explicit API selection offered. [S6]

### 4. Protect and renew credential sets

Use an agent-owned store rooted under `~/.propio/auth/openai/` for metadata and lock state, separate from providers.json and the POC directory. Secrets use OS storage by default: macOS Keychain, a verified Linux secret service, and Windows protected credential storage. Phase 1 selects and tests a maintained dependency compatible with the repository's Node baseline and packaging; native installation failures must be tested in clean consumers.

Where OS storage is unavailable, stop with a clear setup choice. Offer an explicit protected-file mode rather than silently downgrading. Unix files require owner-only directory/file permissions, verified ownership and safe paths, atomic replacement, and rejection of unsafe symlink destinations. Windows fallback requires tested owner-only ACLs before support is advertised; chmod alone is insufficient. Keep file secrets outside any broadly mounted sandbox configuration tree. Existing insecure credential records are reported without printing their contents.

One serialized session record contains access/refresh/ID tokens, scopes, expiry/saved time, and generation, keyed by a secret reference associated with the registration. Replace the complete secret record atomically, then publish metadata generation. Recovery recognizes an interrupted metadata write and the newest committed secret generation; it must not roll back a rotating refresh token. Do not treat OS storage, JSON registry writes, and config selection as a single atomic operation unless proven by the chosen backend.

Lock at the registration level across all processes and storage backends, re-read after acquiring the lock, and refresh only if the newest record still requires it. Prefer a lock released by the OS when the process exits. If a portable lock implementation needs stale-owner recovery, verify owner identity including process start and use atomic recovery; age alone never authorizes stealing. Every writer uses the same protocol. Set bounded waits, network timeouts, and cancellation.

Refresh before expiry with small clock skew. Persist rotations before returning the new token. Transient network/5xx errors retain credentials. Terminal refresh-token codes clear only that registration's token set and mark reauthorization required; retain client/identity/host mapping. invalid_client remains a configuration error requiring diagnosis, not a reason to generate a new client. Do not treat every inference 401 as terminal revocation or start an OAuth retry loop. [S3], [S6]

If the service rotated tokens but the new set cannot be durably saved, fail the current credential operation and mark persistence recovery required. Do not return the token while leaving an old refresh token as the apparent current record, and do not blindly repeat refresh with the old token. A process crash after remote rotation but before any local commit may require reauthorization; local atomicity cannot make the remote exchange transactional. Test and document this boundary separately from recoverable metadata writes.

Logout blocks new requests for the registration and cancels local bound work where possible, serializes against refresh, attempts discovered refresh-token revocation with bounded transient backoff, then clears local secrets. Preserve registration metadata and host identity. A local logout cannot undo upstream work already admitted; other processes re-check shared state before each new attempt. Report unconfirmed remote revocation with ChatGPT Settings guidance. [S3]

### 5. Integrate account/model selection into the CLI

Route auth commands before ordinary configuration discovery, MCP startup, workspace scanning, and sandbox delegation. Proposed interface:

| Command | Behavior |
| --- | --- |
| `propio auth login openai --account personal` | Add or reauthorize a stable labeled registration; validate identity before activation |
| `propio auth accounts openai` | List safe labels, registration states, and configured references; no tokens |
| `propio auth status openai --account personal` | Report sign-in/permission/expiry/storage mode; safe JSON is available explicitly |
| `propio auth enable-plan openai --account personal` | User-initiated consent with full scopes |
| `propio auth logout openai --account personal` | Revoke and clear selected secrets; preserve registration mapping |
| `propio auth import-poc openai --account personal` | Explicit same-host migration described below |
| `/account` | Manage/add registrations and prepare an account switch between turns |
| `/model` | Pick configured API/subscription entry and its eligible model; choose session-only or saved default |

The terminal setup flow combines account selection, catalog loading, context-budget selection, and provider entry creation. It uses existing UI/composer patterns and atomic config writers. Auth-only login is useful without requiring a model or provider entry; the CLI then offers setup as a separate choice. Account label resolution happens in the application; configs bind the immutable local account ID.

Account discovery sends the same selected registration's token to `GET /v1/models`, validates the documented models array, filters visibility=list, preserves ordering, displays display_name, and uses slug for inference. Cache by immutable registration and grant generation with a bounded freshness policy; never reuse another account's catalog. Reload on account switch/reauthorization and manual refresh. A failed lookup does not erase a working config or silently select the first model. [S4]

Keep configured model budgets/defaults for deterministic offline loading. Merge eligible catalog entries into the menu; a newly selected model is materialized into a resolved config before factory creation. Preserve saved per-model budgets for the selected registration. Otherwise use an exact-ID table of verified official documentation limits, reserving maximum output from the context window and respecting any documented input limit. Unknown models require a verified user budget or a visibly labeled conservative 128000 budget. Setup and `/model` allow explicit adjustment, including resetting to `documented`, before choosing session/default scope. Persist the choice in `providers.json`; keep source URLs and check dates for documented defaults in the exact-ID table. Do not infer capacity from undocumented catalog fields or apply old limits to future snapshots. A removed/hidden default remains identifiable but unavailable; ask for another eligible selection instead of silently substituting.

Resolve saved defaults and prepare credentials at startup without mandatory catalog discovery. Perform discovery when setup or model selection needs it, then apply a fully prepared selection through the existing synchronous factory/switch behavior. Add a prepared runtime dependency option to Agent rather than making its constructor discover OS credentials. Keep existing API-only Agent usage compatible. Publish a documented preparation helper if library callers need this flow.

Display `Using ChatGPT plan`, account label, and Manage usage near the composer/model status, including batch/noninteractive run headers. First enabled sign-in gets one-time plan-use explanation. No quota percentages, reset times, or dollar amounts are inferred from token counts; report only supplied usage metadata. ChatGPT settings control permitted credits. Background summaries consume the selected access mode and must be disclosed in setup/docs. [S7]

### 6. Harden the adapter for ordinary Propio requests

Reuse the shared Responses machinery with a subscription-specific profile. Every subscription request uses public `POST /v1/responses`, store=false, stream=true, full required history, and developer instructions. Convert system messages without changing instruction ordering. Namespace local function tools and preserve exact function/call identity on replay. Preserve encrypted reasoning and required output items internally; expose only supported summaries/commentary. [S4], [S5]

Build requests from a supported allowlist. Exclude server conversations/previous_response_id and documented unsupported sampling, output-limit, metadata, hosted-tool, and execution fields. Unsupported user-selected features raise a capability error; internal irrelevant defaults are omitted. Model scope alone does not establish input capability. Text is required; images need provider/model checks and live tests before enabling. Existing local file-reading tools produce text and remain usable; this does not imply Files API or hosted file-search support. [S5]

Validate actual terminal status: response.completed alone confirms success. Buffer pending tool calls until that event; failed/incomplete/error/truncated streams may show partial text but cannot dispatch tools, mark successful turns, or produce accepted summaries. Cancel/release readers promptly. Persist interruptions as such, without inventing missing tool results or re-executing already completed tools on resume. [S4]

The POC's generic ChatGptPlanError must be refined for full integration: preserve safe code, param, actual HTTP status, request ID, retry-after when present, and an explicit retryability classification, while retaining existing typed errors used by the runtime. In particular, genuine context-length errors must remain ProviderContextLengthError for existing compaction recovery. Usage-limit errors must not become generic rate-limit retries; unsupported capability is not context shrinkage. Incomplete responses require cause-specific handling; do not blindly invoke max-output recovery when that request field is unsupported.

| Failure | Behavior |
| --- | --- |
| Eligibility/policy/region/direct permission | Stop; explain selected account/restriction and preserve safe request metadata; no sign-in loop |
| Usage limit exceeded | Stop new subscription requests; Manage usage; no inferred reset and no automatic billing change |
| Usage/user/routing temporarily unavailable before stream | Bounded documented backoff; preserve token set; do not retry a capability/policy failure merely because of status |
| Capability or unsupported route | Actionable feature/parameter error; never repeat the same invalid request |
| Ambiguous connection failure after submission | Do not replay automatically without evidence of safe retry; account usage may already have occurred |
| Failure after stream opens | Preserve partial output and failure; no automatic resubmission or pending tool execution |
| Terminal renewal failure/confirmed disconnect | Invalidate selected secrets; require sign-in with retained issued client ID |
| Context length | Existing bounded context rebuilding using the same account/mode |

Retain current API and Meta stream/retry behavior unless separately covered and intentionally changed. Trace attempt/logical lifecycle, actual model, request IDs, and usage fields through existing APIs; never classify a failed subscription stream as completed merely because text was emitted. [S6]

### 7. Bind sessions, summaries, and account changes

Prepare an immutable selection binding containing provider entry, model, access mode, opaque local account ID, and configuration revision. Pin it to each turn and any background summary operation. Account/model changes are applied between turns; already-started summaries retain their original binding or are cancelled, never redirected to the UI's newest account.

Sessions store only a safe account reference/access mode plus existing conversation and opaque provider continuation. Never serialize credential callbacks, tokens, ID hints, or raw secret-store objects. On resume, resolve current credentials independently and explain signed-out/missing/changed registration states. Preserve previous session schema reading and make new fields optional for legacy files.

Existing provider changes can retain normal history, but cross-registration/workspace changes default to a new conversation. Offer explicit transcript continuation with the destination label and preserve readable history. Treat opaque continuation as bound to its provider/account: strip or rebuild incompatible provider-specific state on an explicit transfer instead of sending another registration's encrypted replay blindly. Test unfinished/recovered tool rounds and never execute a historical side effect merely to repair history.

Use the same provider binding for context shrinking/summaries and other internal inference. Trace purposes distinguish chat and summary usage. Sanitize config snapshots, auth exceptions, browser-launch failures, debug files, recovery journals, sessions, and opt-in request-payload tracing. Prompt payloads remain private user data even after auth redaction; no credentials are included under any debug setting.

### 8. Support the Docker sandbox through host-owned renewal

The existing sandbox mounts ~/.propio at /app/.propio read-only. A container cannot atomically rotate credentials there, and host keychains are unavailable inside it. Making the entire mount writable would expose unrelated state and does not solve keychain access. Keep host-owned OAuth and storage.

Phase 6 implements a host-local credential broker launched by the sandbox wrapper. Scope each instance to the selected immutable registration and sandbox lifetime. It authenticates the container through a private capability/channel and returns short-lived access tokens only; it cannot list accounts, return refresh/ID tokens, change defaults, register clients, or open arbitrary URLs. The host serializes renewal using the same credential manager. Close the channel on container exit, logout, cancellation, or wrapper failure. Avoid token-bearing process arguments, persistent environment configuration, and verbose transport logging.

For Unix, start with a private per-run socket/transport mounted only into that container; validate Docker Desktop behavior rather than assuming native Unix path semantics. Select a supported Windows transport in the spike and test it. Retain a read-only configuration view, while excluding production secret files from broad mounts, including explicit file-storage fallback. User code inside the sandbox may use its authorized access token; the broker is not a security boundary against inference authorized for that sandbox. It must prevent access to renewable credentials and unrelated accounts.

Native preview can ship before this phase with an explicit unsupported subscription-sandbox error. The full feature is not complete until supported-platform broker renewal, permission/lifecycle, and mount tests pass. If a platform cannot meet the broker contract, declare its subscription sandbox unsupported instead of using an unreviewed writable credential mount. Remote/self-hosted credential transfer remains separate scope.

### 9. Migration, packaging, and rollout

Port the focused POC adapter/OAuth regression tests; remove POC names from production paths. Do not merge unrelated POC harness UI or assume its generic errors/storage are release-ready. Existing API config has no forced migration and is never rewritten just by login.

Explicit same-host `import-poc` acquires the POC's existing lock protocol and the production registration lock, verifies host and registration mapping, validates stored record shape, moves the complete token set to the protected production store, and retains issued client/host IDs. Copy-then-retire ordering must be recoverable: once production commits, the POC source is disabled/tokens cleared before either runtime resumes. A journal handles crashes between those operations. Never leave two independently refreshing copies. Preserve unrelated POC profiles and any current default. Require a fresh production login if ownership/identity/host cannot be established; migration is optional, not an auto-startup side effect.

Publish the provider package first, with backward-compatible API contract tests and Node/ESM compatibility. Update agent dependency to the released compatible version and validate a clean installed consumer. Local links only validate development; they are not release evidence. Ship native preview with clear scope, complete sandbox integration, then declare full availability after final gates. Recheck preview requirements and open-source/local distribution eligibility; paid or remotely hosted deployment is a separate decision. [S1]

## Cross-repository changes

| Repository | Change |
|------------|--------|
| propio-providers | src/config.ts, src/configValidation.ts, src/factory.ts, src/index.ts; production subscription adapter and shared Responses hooks; error/capability/trace contracts and tests/docs |
| propio-agent | src/auth/openai/ and credential backends; src/cli/args.ts and src/index.ts auth/setup routing; src/config/providersConfig.ts and src/ui/modelMenu.ts; src/agent.ts selection/dependency wiring |
| propio-agent | src/context/summaryManager.ts, src/sessions/ and recovery handling, src/trace/redaction.ts and diagnostics; bin/propio-sandbox and src/sandboxDelegation.ts broker integration; docs/integration tests |

These are touchpoints identified from current source, not a requirement to refactor every listed file. Keep changes scoped to the acceptance criteria and preserve the agent-core/provider/tool/UI boundaries.

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Preview/account behavior changes | Official sources rechecked before each release; explicit route capabilities; live account-specific gate |
| Rotating-token loss or double refresh | Shared cross-process lock, generation/version checks, atomic secret record, recoverable migration |
| Billing/account surprise | Explicit config mode and pinned account; plan label; no fallback; transcript-transfer choice |
| Native store packaging failure | Early dependency spike and clean-install tests; explicit tested fallback |
| Tool side effect from failed stream | Confirmed terminal completion before exposing calls; adversarial SSE tests and runtime integration |
| Background summary follows new account | Immutable per-operation binding; cancellation and race tests |
| Context recovery breaks under generic plan error | Preserve runtime typed context-length error and distinguish capability/usage failures |
| Docker cannot save renewal | Host broker, scoped credential access, exclude secrets from mounts; full-release gate |
| Auth URL/ID hint leaks | Separate internal URL from safe display URL; redaction tests across all sinks |
| POC registration duplicated on production switch | Explicit locked/journaled same-host migration or fresh-login choice |

## Alternatives considered

- New provider type `openai-subscription`: simpler factory branch but duplicates the user's OpenAI choice and requires more config/menu plumbing; keep one provider type with explicit access mode instead.
- OAuth/storage inside the provider package: makes the package discover application state and weakens standalone usage; retain the application-owned credential boundary.
- Reuse Codex credentials or run Codex app-server: changes registration ownership or introduces another runtime; the POC proves the direct route works through Propio.
- Plain file storage everywhere: convenient POC default but insufficient production platform story; OS storage with explicit protected fallback is preferred.
- Copy subscription tokens into the sandbox/environment once: fails during long sessions and exposes renewable credentials if copied wholesale; use host-mediated renewal.
- Whole POC branch merge: carries experimental naming, a parallel CLI, and unverified storage/recovery choices; port focused behavior into standard workflows.

## Sources and evidence

Official documents fetched October 11, 2026. Implementation choices above are Propio design recommendations; cited service constraints remain preview-dependent.

[S1]: https://developers.openai.com/siwc/token-sharing-open-source
[S2]: https://developers.openai.com/siwc/token-sharing-open-source/sign-in
[S3]: https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions
[S4]: https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
[S5]: https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations
[S6]: https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery
[S7]: https://developers.openai.com/siwc/ui-ux-guidelines

- [S1: Open-source/local integration and host/client lifecycle](https://developers.openai.com/siwc/token-sharing-open-source)
- [S2: Registration, callback, identity, and returning-sign-in hints](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [S3: Accounts, renewal, revocation, and credential security](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
- [S4: Account catalog, public Responses route, and confirmed completion](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [S5: Preview request, tool, and input constraints](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [S6: Admission, stream, grant, consent, and refresh recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)
- [S7: Plan-selection and usage UX](https://developers.openai.com/siwc/ui-ux-guidelines)
- [POC findings and live evidence](../openai-subscription-poc/findings.md)
