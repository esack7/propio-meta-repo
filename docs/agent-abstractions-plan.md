# Propio agent abstractions plan

Status: proposed architecture and migration roadmap

## Objective

Extract reusable capabilities from `propio-agent` so other Propio applications can use consistent context management, skills, MCP connections, tools, and agent execution without depending on the CLI.

Preserve the current agent behavior while establishing explicit package boundaries. Extract one capability at a time, validate it through the existing agent, and use a second real consumer to confirm that its public API is useful before treating the boundary as stable.

This document is a planning artifact. Package and repository names below are proposals; it does not create repositories, select a feature spec's `repos.txt`, or authorize publishing packages.

## Current baseline

The reviewed reference clones of `propio-agent` and `propio-providers` were up to date when this plan was prepared. The project map currently identifies these two repositories as members of the Propio family. Desktop apps, editor integrations, chat services, and background workers are potential consumers, not verified existing integrations.

`@propio-ai/providers` is already extracted. It owns provider adapters, streaming contracts, capabilities, errors, retries, diagnostics, and provider configuration validation. The agent owns Propio-specific configuration paths and application behavior. Preserve that division.

The agent already has recognizable subsystems under `src/context`, `src/skills`, `src/mcp`, and `src/tools`. However, their boundaries still include local configuration, UI metadata, and agent-specific state. `src/agent.ts` also combines orchestration with local sessions, attachments, skills, and execution modes.

## Proposed packages and sequence

| Order | Proposed repository / package | Responsibility | Readiness |
| --- | --- | --- | --- |
| Existing | `propio-providers` / `@propio-ai/providers` | LLM adapters and shared provider contracts | Keep existing boundary |
| 1 | `propio-context` / `@propio-ai/context` | Conversation state, prompt planning, memory, summaries, serialization | Highest strategic value; requires removal of agent-specific state dependencies |
| 2 | `propio-skills` / `@propio-ai/skills` | Skill loading, discovery, validation, matching, and metadata | Relatively independent; likely easiest extraction |
| 3 | `propio-mcp` / `@propio-ai/mcp` | MCP connection lifecycle and tool discovery/calls | Clear scope; separate configuration and tool adaptation |
| 4 | `propio-tools` / `@propio-ai/tools` | Executable tool contracts, registry, reusable local tools | Requires explicit execution dependencies |
| 5 | `propio-agent-core` / `@propio-ai/agent-core` | Headless agent orchestration and runtime events | Establish boundary inside agent first |

Sequence is a recommendation, not a requirement to create five repositories immediately. If a second application urgently needs skills or MCP, move that extraction ahead of context after its dependency boundary is established.

## Boundary rules

- Consumers provide configuration, workspace roots, storage locations, and execution policy explicitly. Libraries must not silently discover `~/.propio` or use the caller's working directory as application policy.
- Keep CLI commands, terminal rendering, menus, and startup wiring in `propio-agent`.
- Keep provider SDK types internal to providers; continue using its common message and streaming contracts where appropriate.
- Dependencies must flow toward reusable packages. Providers must not depend on context, tools, or agent core.
- Separate portable behavior from Node filesystem/process adapters. Initial extraction can remain Node-based; browser compatibility is a separate requirement to validate.
- Avoid a general-purpose shared-utilities repository. Place helpers with the capability that owns their semantics.
- Preserve behavior during extraction. Improvements that change retries, permissions, prompts, or serialization require separate, explicit compatibility decisions.

## Phase 1: Context management

### Scope

Start with `src/context/contextManager.ts`, `promptBuilder.ts`, `memoryManager.ts`, `summaryManager.ts`, `persistence.ts`, `types.ts`, and supporting context utilities. Move the token measurement helpers from `src/diagnostics.ts` only where they belong to prompt planning; retain agent runtime diagnostic events with the agent.

The package should own conversation turns, artifact references, prompt budgets, history selection, context reduction, rolling summaries, pinned memory, and versioned serialization.

### Required separation

1. Remove direct knowledge of agent modes and skill invocation implementation from the core conversation model. Define an explicit, versioned extension mechanism or keep those fields in the application's session envelope.
2. Accept rendered supplemental context or typed contributions without importing the skills package. This permits context to be extracted first.
3. Make token estimation injectable. Preserve the current character-based estimate as a documented fallback, including its limitations for images and provider-specific overhead.
4. Define artifact lookup/storage boundaries. Keep local output files and scratchpad paths in application adapters.
5. Separate session encoding and validation from filesystem storage, workspace discovery, process markers, and slash commands.
6. Allow summarization through an injected provider or callback, without loading provider configuration inside the package.

### Acceptance criteria

- Equivalent inputs produce equivalent prompt plans, selected turns, and artifact behavior after migration.
- Tool-call/result associations remain valid when history is reduced.
- Existing supported session versions load through compatibility fixtures; new serialization does not silently lose skill, mode, image, or continuation state.
- Pinned memory and rolling-summary behavior retain existing coverage.
- A minimal consumer can plan a prompt without loading CLI configuration or writing local files.

Sharing serialization does not establish safe simultaneous writes by multiple applications. Cross-process locking, conflict resolution, and shared session ownership are separate design work if a consumer needs them.

## Phase 2: Skills

### Scope

Extract `src/skills` parsing, discovery, diagnostics, registry, precedence, path matching, and invocation metadata.

Consumers supply ordered discovery roots and source information. The CLI can continue translating Propio conventions into those inputs. Keep menus, `/skill` command handling, and actual agent execution in the application.

Skill metadata describes requested behavior; the consuming runtime decides how it is enforced. Loading a skill must not automatically grant permissions or run instructions.

### Acceptance criteria

- Existing parsing, precedence, matching, and diagnostic tests pass through the package API.
- A second consumer discovers the same skills from the same supplied roots.
- Importing the package causes no directory scan; discovery happens through explicit calls.
- Unsupported execution features remain explicit rather than being silently interpreted as supported.

## Phase 3: MCP

### Scope

Extract `src/mcp/manager.ts`, configuration validation, naming, and public connection/tool summaries. Retain the current stdio transport scope for the first release.

Inject configuration, client identity, timeouts, and configuration persistence. Keep the Propio executable-tool adapter in the agent initially so MCP does not depend on private agent tool types. Once tools is extracted, locate that adapter in the consuming runtime or a deliberate integration entry point without creating a dependency cycle.

Keep SDK client/transport internals out of the public API. Review cleanup code that accesses transport internals and cover it with lifecycle tests.

### Acceptance criteria

- Connection, discovery, execution, reconnect, enable/disable, and shutdown behavior retain coverage.
- Failed or timed-out connections clean up child processes predictably.
- Tool naming remains stable and collisions are tested.
- Consumers can supply configuration without reading or modifying `~/.propio/mcp.json`.
- The public API clearly states supported transports and result representations; extraction does not imply HTTP, resources, or prompts support.

## Phase 4: Tools

### Scope

Extract `src/tools/interface.ts`, result contracts, registry, and reusable read/write/edit/search/list/shell implementations. Replace dependence on the complete agent runtime configuration with focused options for each tool.

Make workspace resolution, shell execution, cancellation, approval callbacks, and output persistence explicit dependencies. Keep presentation optional and separate from execution results. Keep skill invocation wiring in the runtime integration layer.

The package must document which protections it enforces. A workspace path parameter alone is not a sandbox, and a policy classifier alone is not process isolation.

### Acceptance criteria

- Existing filesystem, search, shell, registry, and approval behavior remains covered.
- Tests cover denied execution, cancellation, large output, and execution failures where supported.
- The same tool can execute without terminal rendering or CLI configuration.
- MCP and built-in tools can be adapted to the same public execution contract without either package importing agent internals.

## Phase 5: Agent core

### Scope

First create a headless boundary inside `propio-agent`, then extract it after the boundary is validated. The runtime should accept a provider, context manager, tool executor, execution policy, and optional integrations. It should emit typed lifecycle events for consumers to render or record.

Move the input submission contract out of `src/ui` before making it part of a runtime API. Separate configuration loading, local session management, process markers, scratchpad allocation, and terminal event formatting from the model/tool loop.

Keep product-specific prompts and plan-mode UX in the CLI initially. Expose policy and instruction hooks rather than assuming every consumer is a coding CLI.

### Acceptance criteria

- A programmatic consumer can run and cancel a turn without starting the CLI.
- Provider/tool event ordering and final results remain compatible.
- Tool failures, context-length recovery, reasoning continuation, and interrupted turns retain regression coverage.
- The CLI becomes a consumer of the same public API used by the second application.

## Providers: preserve and refine

Keep `@propio-ai/providers` as one package. Do not split individual adapters without evidence that dependency size or independent release requirements warrant the additional maintenance.

Preserve explicit configuration paths and normalized streaming contracts. Document continuation-state persistence and capabilities so context and runtime consumers can use them correctly.

Review the existing retry-without-tools behavior as a separate policy question. It changes available model actions and should be controllable by consumers. Do not silently change it as part of an unrelated extraction.

## Migration and release workflow

For each phase:

1. Identify a concrete second consumer and its required use cases. If none is ready, improve the internal boundary before committing to a new repository.
2. Define the smallest public API, dependency direction, compatibility fixtures, and explicit non-goals.
3. Add the approved repository to the canonical project map when its real repository details exist; do not invent clone URLs or branches.
4. Create and prepare a feature spec using the meta-repo workflows and confirmed repository selection. Implement in feature worktrees, preserving reference clones.
5. Establish the boundary with adapters inside the agent, then move implementation and relevant tests into the destination package.
6. Link package and consumer worktrees with `link-local-packages` in the same spec context. Do not mix feature worktrees with reference clones.
7. Run both package and consumer validation: relevant regression tests, build, formatting, and required Fallow audit. Use live-provider tests only where provider behavior changed and credentials are available.
8. Verify package exports, declarations, packaged files, and clean-install consumption using the release workflow. Ensure imports have no CLI startup side effects.
9. Release the library before updating the agent to its published version. Coordinate approval and publication separately from implementation.
10. Keep extraction changes separate from new features so rollback can restore the prior agent dependency and adapter wiring. If persistence changes, document reader/writer compatibility before rollout.

## Deferred areas

- Terminal UI and input editing: retain locally until another terminal product needs the same behavior.
- Docker launcher and sandbox packaging: retain with deployment/runtime integration.
- Product identity, system prompt wording, and slash commands: retain with the application.
- Workspace instruction discovery and file attachments: possible later workspace-context package, after a second consumer establishes requirements. Avoid prematurely bundling them with conversation memory.
- Generic config helpers and tiny utilities: share only when their ownership and maintenance benefit are clear.

## Completion criteria

An extraction is complete when the agent uses the published public API, relevant behavior and compatibility checks pass, a real second consumer validates the boundary, and the new package requires no imports from agent internals. Each package should document its runtime requirements, side effects, extension points, and versioning policy.

The immediate next implementation target is context management. The first deliverable should be a focused context API and migration spec covering session compatibility, skill/mode state separation, and artifact/token-estimation interfaces.
