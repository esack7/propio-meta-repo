# Design: tools-abstraction

The public tools entry point exposes ExecutableTool, ToolExecutionContext, ToolRegistry, LocalToolOptions, createLocalTools, createExecutableTool, and executeNodeShell. Provider schemas remain the existing shared contract. The execution registry has no rendering methods; the CLI registry subclasses it to retain optional labels and display adapters.

createLocalTools requires an absolute workspaceRoot and shellExecutor and supplies focused path/shell options to the existing implementations. The CLI manifest uses the same factory implementation and adds skill invocation itself. Direct legacy constructors retain compatibility defaults but are not exported by the public entry point.

The registry supports caller-owned approval and output processing. Approval receives detached arguments, with a separate execution snapshot to prevent mutations during review from changing the executed request. Enabled state and cancellation are rechecked after approval. Output processing can replace content with a preview and attach an opaque storage reference; failures preserve the execution result with an outputPersistenceError field.

The public generic integration adapter accepts schema and invocation callbacks. The existing MCP runtime adapter uses it, while the public MCP package remains independent of tool contracts. Optional structured execution preserves MCP error statuses in a shared registry.

Cancellation reaches local tool implementations and shell execution. Pre-cancelled operations do not start; writes check before atomic replacement and grep between files. Cancellation is cooperative, not rollback or guaranteed process-tree termination. Existing four statuses remain compatible with session codecs. Shell nonzero exits retain their existing JSON representation and registry success classification.

No new package is published. The example and clean-install consumer validate the provisional subpath; a real second production consumer is still required before stabilizing or extracting the boundary.
