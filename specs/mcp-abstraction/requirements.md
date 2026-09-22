# Requirements: mcp-abstraction

Implement phase 3 of docs/agent-abstractions-plan.md in propio-agent only, as confirmed by the user.

- Establish a provisional @propio-ai/agent/mcp public API within the existing package. No destination repository or second production consumer is identified.
- Inject configuration, client identity, connection/tool-call/cleanup timeouts, and optional configuration persistence. The reusable API must not read or modify Propio configuration files.
- Retain stdio transport scope and existing naming and text result behavior. Keep provider/tool schema adaptation and CLI configuration wiring local to the agent.
- Keep SDK client and transport internals out of public types. Replace private transport process access with public lifecycle APIs.
- Cover connection, paginated discovery, execution, failures, deadlines, reconnect, enable/disable, shutdown, name collisions, and child-process termination with regression tests.
- Document supported transport, result representations, side effects, extension points, runtime requirements, and provisional versioning. Validate a packed clean-install standalone consumer.
- No publication or new repository creation is included. Production second-consumer validation remains a release milestone.
