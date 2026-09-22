# Requirements: context-management

Establish the phase 1 context boundary described in docs/agent-abstractions-plan.md.
Confirmed repository: propio-agent. Worktree: specs/context-management/repos/propio-agent.

## Scope

- Reusable conversation state, prompt budgets, history reduction, artifact references,
  pinned memory, rolling summaries, and a versioned context codec.
- Separate CLI skill state and synthetic mention cleanup through an application adapter.
- Inject token estimation, rendered supplemental context, artifact lookup, and summarization.
- Preserve supported CLI session versions 1–4 and continue writing version 4.

## Acceptance criteria

- Existing prompt, artifact, memory, summary, session, and agent behavior passes regression coverage.
- Retried prompt plans preserve tool-call/result associations.
- Legacy fixtures retain images, reasoning continuation, skill records and mode metadata.
- A minimal consumer imports the packaged context entry point and plans a prompt without CLI
  configuration, workspace discovery, or local writes.
- Build, full tests, formatting, Fallow audit, declarations and packed consumption are verified.

## Non-goals and release boundary

No new repository, provider changes, npm publication, shared-session locking, browser guarantee,
or separate production consumer is included. The project map contains no context repository
or concrete second consumer. This implementation establishes the internal boundary and a
minimal consumer; the architecture plan's published-package completion criteria remain a
later release milestone.
