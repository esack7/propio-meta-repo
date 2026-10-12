# OpenAI subscription POC findings

Investigated October 10, 2026; live subscription checks completed October 11, 2026. Branch: `feature/openai-subscription-poc` in `propio-providers` and `propio-agent`. Base commits: providers `fe34bb5`; agent `946ede9`. These are POC notes for a future full spec, not a claim of production readiness.

Closeout updated October 12, 2026: the full feature is merged and released in providers `0.6.0` and agent `1.4.0`. The user authorized preserving POC source in local-only commits and removing its worktrees. Providers are retained at `5e570123478507300982909809b43fabd6de0fea`; agent at `e66d06d162c8a2af722427c3df7a152d7456fe01`, both on local `feature/openai-subscription-poc` branches. All four feature/POC worktrees are removed. Spec documents and the existing POC credential directory remain; no credentials were committed. Reopen the POC with the bundled prepare-spec helper and explicit retained-branch reuse authorization to access its original launcher/guide. Production closeout and remaining acceptance gaps are in [verification.md](../openai-subscription/verification.md).

## Current evidence

| Finding | Evidence type | Outcome |
| --- | --- | --- |
| Open-source/local apps can request ChatGPT plan usage with their own dynamically registered OAuth client | Official documentation | Supported preview route; eligible user/workspace and actual admission remain service-controlled |
| Public Responses endpoint can accept an authorized plan token | Official documentation | Use api.openai.com/v1/responses; no private backend or imported Codex auth needed |
| Existing provider already sends stateless streamed Responses requests | Source inspection | Reuse adapter rather than introducing Codex's separate runtime |
| Subscription requests impose stricter instruction/tool formats | Documentation + mocked request tests | System instructions become developer messages; functions are namespaced; full history is replayed |
| Text or pending tools can precede a stream failure | Mocked SSE tests | Require response.completed; reject incomplete/error/EOF and prevent pending tool dispatch |
| OAuth must validate more than receipt of credentials | Signed mock-ID-token + real local callback tests | PKCE, state, nonce, signature, issuer, audience, expiry, returning subject/client identity verified |
| Rotation must be serialized and persisted atomically | Concurrent credential-client tests | Cross-process lock; newest refresh token retained; terminal errors clear only selected account |
| Identity sign-in does not guarantee plan permission | Mocked OAuth tests | Plan scopes checked before inference; no silent API fallback |
| Revocation can fail independently of local logout | Mocked logout tests | Clear local tokens, preserve registration, report unconfirmed remote revocation |
| OpenAI authentication discovery is reachable | Live unauthenticated probe | HTTP 200; issuer auth.openai.com, JWKS /.well-known/jwks.json, revocation /api/accounts/oauth/revoke |
| Real account sign-in and inference work for this user | Live authenticated test | User completed browser login in a separate terminal; saved default profile connected with plan permission; model discovery and text/tool/history smoke stages passed on gpt-6.1-sol |

## Verification record

- Final provider suite: 19 suites / 423 tests passed.
- Final agent suite: 109 suites / 1,650 tests passed, including 16 new POC authentication/CLI tests.
- Both TypeScript builds and full repository formatting checks passed.
- Fallow changed-file audits against origin/main passed in both repositories after simplifying POC functions; no issues in the changed files.
- The launcher passed shell syntax validation, help, and signed-out status checks. A signed-out smoke invocation exited with the login instruction before any inference. Regular CLI help also worked.
- At the October 11 verification checkpoint, both checkouts were on `feature/openai-subscription-poc` with the local provider link active and uncommitted, unpublished changes. The October 12 closeout above preserves those source changes in local-only commits and removes the worktrees.
- After the user's browser login, the agent verified saved sign-in status and live model discovery, then ran subscription inference through the smoke command. All three stages passed. No API-key fallback or existing credential import was used. Requests used the account's authorized plan access; exact allowance or enabled-credit consumption was not measured.

## Live test log

After reopening the retained POC branches, follow `docs/openai-subscription-poc.md` in the restored agent checkout. Record one row per outcome without tokens, authorization URLs, email, or conversation content.

| Date/time | Account label | Model slug | Command/stage | Result | Error code / HTTP status / request ID | Implication |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-11 | default | — | login → status | User completed login in a separate terminal; status confirmed connected and planUsageEnabled | — | Browser sign-in produces usable plan credentials for the local app |
| 2026-10-11 | default | gpt-6.1-sol (plus six other visible models) | models | Model catalog returned seven visible model slugs | — | Account-specific model discovery works with the saved subscription token |
| 2026-10-11 | default | gpt-6.1-sol | smoke: text | PASS; text stream completed | — | Public Responses inference accepted the subscription credential |
| 2026-10-11 | default | gpt-6.1-sol | smoke: tool execution and replay | PASS; one local tool call executed and result replay completed | — | Namespaced function calling works through Propio's shared agent runtime |
| 2026-10-11 | default | gpt-6.1-sol | smoke: conversation continuation | PASS | — | Multi-turn history after a tool round works for this model/account |
| Pending | default | User-selected | interactive chat → refresh → logout/relogin | Not yet verified live | — | Check terminal UX, token rotation, and revocation separately; retain sign-in for user testing |

## Implications for the full spec

1. Add an explicit OpenAI authentication/billing choice. Default existing configurations to API access and make subscription selection visible in status/model UX.
2. Keep interactive sign-in and OS-backed storage in the application, with a typed renewable credential interface consumed by the provider. Do not make provider construction perform browser or filesystem discovery.
3. Specify account/workspace registration ownership, stable host IDs, account switching, consent disabled/re-enabled, refresh concurrency, revocation, and failure recovery separately.
4. Model selection needs account-specific discovery plus documented model capacity. The POC's configurable 128000-token prompt budget is an assumption, not account-catalog capacity data.
5. Define request capabilities for the subscription route independently from API access. Retain tool namespaces and exact provider continuation internally, and reject unsupported hosted tools rather than treating local MCP as hosted Responses MCP.
6. Preserve structured admission/stream errors, request IDs, and app-specific usage limits. Specify when retry is safe before a stream and prohibit silent billing fallback.
7. Evaluate macOS Keychain, Linux credential storage, and Windows ACLs. Decide recovery for forcibly terminated lock owners without racing rotating refresh tokens.
8. Design Docker/headless flows explicitly. Existing sandbox config is mounted read-only and cannot persist rotated tokens through that mount; the POC targets local native use.
9. Preserve live integration coverage for model/tool/history behavior, now confirmed for one account on gpt-6.1-sol. Broaden to other models/accounts and verify renewal, cancellation, revocation, and partial-output failures; the successful smoke run does not establish those behaviors.
10. Review preview/distribution requirements before hosted or paid deployment. The branch adds an experimental explicit adapter, not a stable production auth schema.

## Sources

- [Overview and eligibility](https://developers.openai.com/siwc/token-sharing-open-source)
- [Registration, PKCE, and ID-token validation](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Model discovery and confirmed inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Preview request/tool restrictions](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Accounts, renewal, revocation, and shared usage](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
- [Admission/stream/refresh errors](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)
