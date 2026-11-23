# Design: openai-subscription-poc

## Overview

Runnable OpenAI ChatGPT subscription sign-in POC and evidence for a future implementation spec

This records the experimental architecture used for the live checks. The [full implementation](../openai-subscription/design.md) has since been released. POC worktrees were closed October 12, 2026; source is preserved on local `feature/openai-subscription-poc` branches, with recovery details in [findings.md](findings.md).

## Approach

Expose an experimental `OpenAiSubscriptionProvider` through explicit construction rather than changing the stable factory/config schema. Reuse the Responses adapter with opt-in confirmed-completion validation, caller-supplied bearer credentials, developer instructions, and namespaced tools.

The agent's dedicated `openai-poc` command owns OAuth, verified identity, stable host/client IDs, file storage, cross-process rotation locks, and account labels. It invokes the existing `AgentRuntime` with an in-memory conversation and a demo lookup tool. This keeps real inference testable without changing the regular CLI's configuration, MCP connections, sessions, or normal tool permissions.

## Cross-repository changes

| Repository | Change |
|------------|--------|
| propio-providers | Subscription adapter, request compatibility, strict SSE completion/error handling, regression tests |
| propio-agent | POC command, OAuth and storage, model discovery, smoke/chat harness, user guide, tests |

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Preview access differs by account or rollout | Keep live eligibility pending until completed inference; retain errors/request IDs |
| Rotating credentials race across processes | Exclusive lock and atomic replacement; no automatic lock stealing |
| Stream ends after a pending tool call | Require response.completed before emitting tools; fail on incomplete/error/EOF |
| Unexpected subscription usage | Explicit plan labeling and usage link; no API-key fallback |
| Shared adapter regression | Completion rules are opt-in to the subscription profile; run all provider tests |

## Alternatives considered

- Codex app-server: documented, but adds another agent runtime/process; unnecessary for validating Propio's own provider/tool loop.
- Existing Codex credential reuse/private endpoints: excluded; the documented SIWC flow grants this application its own plan permission.
