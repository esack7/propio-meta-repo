# Design: mcp-abstraction

The `@propio-ai/agent/mcp` entry point exports `McpConnectionManager`, explicit options, public configuration and summary/descriptor/result contracts, pure validation, and stable naming helpers.

`connectionManager.ts` owns stdio connection/discovery/call lifecycle. Public descriptors carry JSON input schemas and results retain the CLI's status/string representation. `internalTypes.ts` holds SDK runtime types; they are not exported through the public entry point. Configuration validation moves to `validation.ts`; filesystem defaults and persistence stay in `config.ts`.

The existing `McpManager` becomes the Propio adapter, supplying configuration and persistence and constructing `McpExecutableTool` adapters for provider schemas and invocation labels. The core imports neither agent tool contracts nor providers nor CLI configuration.

Configuration is validated and copied on entry. Persistence callbacks receive detached snapshots and the targeted server/enabled change record, and are awaited before state changes. Toggle operations are serialized. The default core behavior is in-memory mutation. The CLI adapter continues writing enabled state to its configured file while preserving unrelated file settings.

Connection generations prevent stale startup work from repopulating disconnected runtimes. Pending connections are registered before initialization so shutdown can clean them up. Cleanup uses an isolated SDK 1.29.0 compatibility shim to capture the original child-process handle before closing, allows a configurable grace period, then uses the handle to SIGKILL a still-running direct child and waits again. Exit and signal state are checked independently of stdio closure; the public PID API alone cannot safely identify the child after exit. This private `_process` dependency is covered by a real inherited-pipe regression test and stays outside public API types. Closing is terminal and concurrent closes share the cleanup promise.

Tests use real local stdio servers, including handshake and discovery hangs, PID liveness checks, pagination, collisions, media/text/structured results, persistence failures, reconnect and unexpected process exit. Existing CLI MCP tests remain regression coverage. A standalone catalog example and packed clean-install checks validate package exports and declarations.

Compatibility fixes: an omitted mcpServers field now correctly validates as an empty configuration; supplied configurations are validated rather than bypassing checks; duplicate identical remote tool names retain the first descriptor, including across overlapping pages; genuine normalization collisions still fail discovery. Explicit shutdown is terminal. These changes are documented and tested rather than silently changing prompts, provider behavior, or transport scope.

Review follow-up: CLI adapters cache by catalog generation/status, and invocation labels use a map lookup. A successful persistence write resolves with disabled status if shutdown occurs during the write, without restarting a connection. Callback rejection still leaves runtime state unchanged; the callback owns durable-storage atomicity.
