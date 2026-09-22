# Requirements: agent-core-abstraction

Implement phase 5 of `docs/agent-abstractions-plan.md` inside `propio-agent`.
The user confirmed the exact repository selection, `propio-agent`, on 2026-09-10.

- Establish a headless runtime accepting a provider, model, context, tool executor,
  execution policy and optional application integrations.
- Move provider-ready input out of UI ownership. Keep UI buffer metadata local.
- Preserve the CLI's model/tool ordering, return value, reasoning continuation,
  context-length recovery, tool-failure handling and interrupted-turn behavior.
- Keep configuration, sessions, markers, scratchpads, product prompts, plan UX,
  skills, attachments and terminal formatting in the CLI adapter.
- Demonstrate direct public-API use and cancellation without starting the CLI.
- Validate regression coverage, build, formatting, Fallow and packed consumption.

A standalone record-lookup example is the concrete second consumer for this
internal boundary. No second production application or separate repository is
available in the project map. Publishing or creating a standalone agent-core
repository is outside this implementation's scope.
