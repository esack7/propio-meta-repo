# Requirements: tools-abstraction

Implement phase 4 of docs/agent-abstractions-plan.md in propio-agent only, as explicitly confirmed by the user.

- Establish a provisional @propio-ai/agent/tools public API inside the existing package. No separate destination repository or production second consumer is identified.
- Expose execution contracts, results, registry and reusable read/write/edit/grep/find/list/shell behavior with focused options.
- Require explicit workspace and shell dependencies; allow path resolution, cancellation, approval and output storage callbacks.
- Keep terminal presentation, runtime configuration, skills, mode policy and session paths outside the reusable API.
- Preserve CLI defaults, schemas, output formats and serialization-compatible statuses. Document cooperative cancellation as an explicit behavior improvement.
- Cover denial, cancellation, execution failures, large output and MCP adaptation through public APIs. Run build, tests, formatting, Fallow and packed clean-install checks.
- Document runtime requirements, side effects, protections and limitations. Publication and second-production-consumer validation are separate milestones.
