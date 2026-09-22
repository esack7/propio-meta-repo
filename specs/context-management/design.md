# Design: context-management

## API and dependency direction

Expose the provisional Node API at @propio-ai/agent/context. Its entry point exports
ConversationManager, PromptBuilder, SummaryManager, context contracts, token estimation,
and serializeContext/parseContext. Imports perform no CLI startup or filesystem discovery.

ConversationManager owns core state. ContextManager remains the CLI adapter, retaining
invoked skills in the application's state envelope and rendering them as ordered supplemental
context. Synthetic file-mention recognition stays in that adapter. The original types module
is an application compatibility facade over coreTypes.

TokenEstimator receives text, messages, or raw character counts. Its default preserves the
existing ceil(characters / 4) policy. Custom estimators measure rendered turns for selection
and the final message list. Artifact records remain in memory; optional lookup resolves
caller-owned content. External paths are opaque metadata, never opened by the core.

SummaryManager accepts an injected provider streamChat contract or a callback. Model choice,
provider configuration, cancellation and scheduling belong to the consumer.

## Persistence compatibility

codec owns shared context encoding, validation and restoration. The CLI persistence adapter
adds skill records and session metadata, including mode and plan state. Existing versions
1–4 remain readable; CLI output stays version 4. A separate core document has version 1,
with no implication that it can replace a full CLI session envelope.

Images remain UTF-8 strings or base64 encoded byte arrays. Reasoning continuation strings
remain opaque. Artifact external-storage metadata survives both codec and manager import.
No cross-process ownership or locking is introduced.

## Validation and limits

Retain the existing regression suite and add four legacy wire-format fixtures, retry-level
equivalence, tool associations, injectable estimation/artifact lookup, and callback cancellation
tests. Validate the built npm artifact through a clean consumer and its declarations.

The provisional subpath is a staging boundary inside the existing agent package. Extraction to
a separately published package requires a real repository and a second production consumer.
