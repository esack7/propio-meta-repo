# Requirements: openai-subscription-poc

## Summary

Runnable OpenAI ChatGPT subscription sign-in POC and evidence for a future implementation spec

Closeout: October 12, 2026. The full implementation is merged and published in providers `0.6.0` and agent `1.4.0`. Both POC worktrees were removed with the bundled helper after preserving source in local-only commits; branches, findings, and credentials remain. Detailed POC acceptance gaps below are unchanged.

## Goals

- Provide a runnable, local POC of documented ChatGPT plan access alongside existing API-key access.
- Let the user sign in and test the POC themselves without changing their normal provider configuration.
- Gather evidence for a future full implementation spec, rather than treating mocked tests as proof of service eligibility.

## Non-goals

- Production account/configuration UX, publishing, hosted commercial distribution, or Docker support.
- Reading existing Codex credentials or using private ChatGPT backend endpoints.

## Acceptance criteria

- [x] Separate `feature/openai-subscription-poc` worktrees in both confirmed repositories.
- [x] Browser sign-in, protected file storage, renewal, status, profile selection, and logout commands.
- [x] Subscription provider retains the existing streaming contract and receives credentials from its caller.
- [x] Runnable text/tool/continuation smoke test and interactive chat through Propio's shared agent runtime.
- [x] Automated OAuth identity, state, token rotation, failure, and stream-completion checks.
- [x] User completes actual ChatGPT login; live model discovery and all three inference smoke stages pass on gpt-6.1-sol. Results are recorded in findings.md.

## Affected repositories

<!-- Confirmed names are listed in repos.txt -->

`propio-providers` and `propio-agent`, explicitly confirmed by the user.

## Open questions

- Selected account admission, live function execution/result replay, and conversation continuation passed October 11, 2026. Broader model/account and encrypted-continuation cases still need coverage.
- Live token renewal, logout/relogin, and interactive terminal chat remain follow-up checks.
- Production model-capacity and usage-control design is proposed in the [full implementation spec](../openai-subscription/design.md).
