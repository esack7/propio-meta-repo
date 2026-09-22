# Design: agent-core-abstraction

Expose a provisional `@propio-ai/agent/agent-core` package subpath. `AgentRuntime`
owns the existing streaming/model/tool loop and its bounded recovery logic.
Its dependencies are injected, and its input contract is `{ text, images? }`.
The context parameter is a structural subset of the public ConversationManager;
the executor supports the public tools registry and caller-owned integrations.

`Agent` constructs this runtime for each turn using its currently selected
provider and existing context. CLI adapters supply policy, prompt planning,
attachments, skill activation, summary refresh, session markers, output storage
and scratchpads. Mode management and session codecs remain in Agent. Terminal
formatting transforms plain runtime events into the existing CLI event shapes.

Runtime lifecycle events cover start, text, completion, cancellation and failure.
Existing provider/tool/status/reasoning events retain ordering. Runtime tool
results include raw content for consumer rendering; CLI events retain previews.
Opaque reasoning continuation stays in conversation history and never becomes
visible reasoning text.

One active turn is allowed per runtime or CLI Agent. Default headless cancellation
discards incomplete history; CLI policy preserves Escape-only discard. Provider
and tool waits race cancellation; failed/idle streams use best-effort iterator
cleanup so an uncooperative return cannot block cancellation. Integration code
owns external cleanup and must not mutate shared context after cancellation.

Compatibility corrections: prevent tool dispatch when a tool-start callback
cancels, reject overlapping turns, avoid hanging on idle-stream cleanup, and
preserve executor external-storage metadata. No session schema, provider retry
policy, product prompt or published dependency changes are introduced.

The public API remains provisional, Node.js 20+, and follows the agent package's
version. Production second-consumer validation and standalone publication remain
separate milestones.
