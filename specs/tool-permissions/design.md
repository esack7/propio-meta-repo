# Design: tool-permissions

## Overview

Introduce the `policy` primitive and put an operator decision in front of tool
side effects. Scope and acceptance come from the `tool-permissions` section of
[maturity-audit-roadmap/design.md](../maturity-audit-roadmap/design.md).

Sections marked **Proposal** settled what the roadmap left open. They were
drafted from the code at `propio-agent` `efa1de8` and agreed on 2026-11-12,
with one correction to "Modes" recorded there.

## What exists at the baseline

| Piece | Location | Use |
| --- | --- | --- |
| Authorization hook, evaluated on a detached argument snapshot before every dispatch; a throw is a denial | `AgentIntegrations.authorizeTool`, `src/agent-core/types.ts:107`; `src/agent-core/runtime.ts` `authorizeApplicationToolExecution` | Enforcement point. Already async and abortable, so it can wait for an answer. |
| Decision record with actor, rule, reason, argument fingerprint | `recordToolPolicyDecision`, `src/agent-core/runtime.ts` | Trace record. `actor` already admits `"user"`. |
| Application decision: plan-file rule, plan/discover bash classifier, otherwise allow with rule `mode_policy` | `Agent.authorizeToolExecution`, `src/agent.ts:751` | Replaced by a call into `policy` after the existing mode checks. |
| Registry `approve` callback, fail-closed | `ToolRegistryOptions`, `src/tools/execution.ts` | Left as is. Policy goes through `authorizeTool` so MCP tools, which bypass this registry, are covered. |
| Global-install prompt | `BashTool.assertGlobalInstallAllowed`, `src/tools/bash.ts:227`; `src/tools/globalInstallGuard.ts` | Classifier kept; the prompt and the `PROPIO_ALLOW_GLOBAL_INSTALLS` gate move into the rule model. |
| Settings file | `~/.propio/settings.json`, `runtime` object, `src/config/runtimeConfig.ts` | Gains a `permissions` object. |
| Modes | `execute`, `plan`, `discover`; `--mode`; `src/modes` | See "Modes" below. |
| MCP tool names | `mcp__<server>__<tool>`, `src/mcp/toolName.ts` | Rule matching on server and tool. |
| Path resolution | `resolveToolPath`, `src/tools/shared.ts`; absolute paths pass through | Confinement check uses the resolved path. |
| Dependencies | `minimatch`, `zod` present; `ajv` only transitively through the MCP SDK | See "Schema validation". |

## Approach

### Module layout

`src/policy/` is new and is exported as `@propio-ai/agent/policy`. It imports
nothing else from `src/` and nothing that touches the filesystem, process, or
network. Everything environment-specific is passed in.

```
src/policy/
  capabilities.ts   capability vocabulary, ToolMetadata
  rules.ts          rule parsing, matching, precedence
  modes.ts          permission modes
  presets.ts        named presets
  engine.ts         PolicyEngine: evaluate(request) -> decision
  approval.ts       ApprovalRequest, ApprovalAnswer, grant derivation
  store.ts          PermissionStore interface, in-memory implementation
  index.ts
```

File-backed storage, the prompt, the `/permissions` command, and flag parsing
live in the application (`src/config`, `src/ui`, `src/index.ts`, `src/agent.ts`).

### Schema validation

`ToolExecutionRegistry.executeWithStatus` validates arguments against the
tool's advertised schema before `approve` and before the implementation. MCP
calls are validated the same way in `McpManager` against the server's schema. A
failure returns a new status `invalid_arguments` whose content lists each
failing path and reason, so the model can correct the call. Validation runs
before policy: an invalid call is never shown to the operator.

**Proposal: validator.** Add `ajv` as a direct dependency. Tool schemas are JSON
Schema, including arbitrary ones from MCP servers; `zod` would need a
conversion layer. It is already in the install tree through the MCP SDK.
Compiled validators are cached per registry instance, not at module level.

Dialect (decided 2026-11-12, after review): `$schema` must name the 2020-12,
2019-09, or draft-07 meta-schema; any other declared dialect makes the tool
uncallable. A schema without `$schema` is read as 2020-12. For MCP tools that
is final, as the MCP specification requires; other tools are retried as
draft-07 if they do not compile as 2020-12. The owner of a tool supplies its
check (`ExecutableTool.validateArguments`, `AgentToolExecutor.validateArguments`),
so the runtime applies MCP rules to MCP tools before policy runs.

### Tool metadata

```ts
type Capability = "read" | "workspace_write" | "process" | "network" | "external";

interface ToolMetadata {
  readonly capabilities: readonly Capability[];
  readonly readOnly: boolean;
  readonly concurrencySafe: boolean;
}
```

`ExecutableTool` gains an optional `metadata`. A tool without it is treated as
`{ capabilities: ["external"], readOnly: false, concurrencySafe: false }`, which
is also the MCP default, so an undeclared tool always asks.

| Tool | Capabilities | Read-only | Concurrency-safe |
| --- | --- | :-: | :-: |
| `read`, `grep`, `find`, `ls` | `read` | yes | yes |
| `write`, `edit` | `workspace_write` | no | no |
| `bash` | `process` | no | no |
| `skill` | `read` | yes | no |
| MCP | `external` | no | no |

`network` is in the vocabulary for `tools-hardening` (web fetch); nothing
declares it yet.

### Rule syntax — Proposal

A rule is a string, `Tool` or `Tool(pattern)`, placed in an `allow`, `ask`, or
`deny` list.

| Form | Matches |
| --- | --- |
| `read`, `bash` | Every call to that tool |
| `edit(src/**)` | File tools: `minimatch` glob against the resolved path. Relative patterns are relative to the workspace; `/abs/**` and `~/**` are absolute. |
| `bash(npm run test:*)` | `bash`: command prefix. A trailing `:*` matches the prefix followed by end of string or a space. Without it the match is exact. |
| `mcp__github` | Every tool of one MCP server |
| `mcp__github__create_issue` | One MCP tool |
| `capability:workspace_write` | Every tool declaring that capability |

A `bash` allow rule never matches a command containing `;`, `&&`, `||`, `|`, a
newline, backticks, or `$(`, so `bash(git status:*)` cannot approve
`git status; rm -rf x`. Such commands fall through to `ask`. Deny and ask rules
match on the same prefix test applied to each segment, so a deny cannot be
evaded by chaining.

Precedence: any matching deny, then any matching ask, then any matching allow,
then the mode default. Sources are merged before precedence is applied: preset
rules, user rules, session grants. A session grant is an allow rule with session
lifetime, so a deny from any source beats it.

A rule that fails to parse is reported with its text and position, and the
store load fails; it is never silently dropped.

### Modes — Proposal

Permission mode is a second axis beside the existing agent mode. The agent mode
(`execute`, `plan`, `discover`) keeps selecting the tool surface and the plan
and bash classifiers. The permission mode selects the default for calls no rule
matched. The roadmap listed all five as one set; two settings were chosen so
that `policy` knows nothing about plan mode and leaving plan mode returns to
the permission mode that was active.

In `plan` and `discover` the existing checks run first and their denials stand,
including under `bypass`. Two things those checks approve are allowed without a
prompt, with rule `agent_mode:<mode>`: a `bash` command the classifier passes
as read-only, and a write or edit to the approved plan file. Explicit deny and
ask rules still apply to both. Every other call continues into policy.

| Permission mode | `read` in workspace | `read` outside | `workspace_write` in workspace | `process`, `external`, `network` |
| --- | --- | --- | --- | --- |
| `ask` (default) | allow | ask | ask | ask |
| `accept-edits` | allow | ask | allow | ask |
| `bypass` | allow | allow | allow | allow |

`plan` and `discover` in the roadmap's list are the existing agent modes with
permission mode `ask` underneath. `bypass` shows a persistent label in the
footer and is recorded on every decision as rule `mode:bypass`.

File tools writing outside the workspace ask in every mode except `bypass`.

### Presets — Proposal

A preset is a name for a permission mode plus rules. User rules layer on top and
a preset can never remove a user deny.

| Preset | Mode | Rules |
| --- | --- | --- |
| `read-only` | `ask` | deny `capability:workspace_write`, `capability:process`, `capability:external`, `capability:network` |
| `ask` (default) | `ask` | none |
| `accept-edits` | `accept-edits` | none |
| `bypass` | `bypass` | none |

Selection, highest first: `--permissions <preset>` flag, `/permissions preset
<name>` for the running session, `permissions.preset` in settings, then `ask`.

Each preset has one table-driven test naming the calls it allows, asks about,
and denies (criterion a7).

### Settings schema — Proposal

In `~/.propio/settings.json`, beside `runtime`:

```json
{
  "permissions": {
    "preset": "ask",
    "allow": ["bash(npm run test:*)", "edit(src/**)"],
    "ask": [],
    "deny": ["read(~/.ssh/**)", "bash(git push:*)"]
  }
}
```

Validated with `zod` in the application's store implementation. An invalid file
fails startup with the file and field. "Always allow" from the prompt appends to
`allow` using the existing atomic JSON writer (`src/config/jsonFile.ts`), leaving
other keys untouched.

### Store

```ts
type PermissionSettingsChange = (current: PermissionSettings) => PermissionSettings;

interface PermissionStore {
  /** The settings as of the latest completed update. */
  load(owner: OwnerScope): Promise<PermissionSettings>;
  /** Apply a pure change to the current stored settings atomically. */
  update(owner: OwnerScope, change: PermissionSettingsChange): Promise<PermissionSettings>;
}
```

The original proposal had `save(owner, settings)`. Review of `policy-core`
replaced it: whole-snapshot saves let concurrent edits, from one engine or
several, drop each other's deny rules.

`OwnerScope` is an opaque string. The CLI passes a constant and maps it to the
settings file. `policy` ships an in-memory implementation for tests and the
server. A `PolicyEngine` is constructed with a store and an owner scope and
holds its rules and session grants as instance state (criterion a12).

### Approval request and answer — Proposal

```ts
interface ApprovalRequest {
  readonly id: string;
  readonly sessionId: string;
  readonly toolCallId: string;
  readonly toolName: string;
  readonly args: JsonObject;
  readonly capabilities: readonly Capability[];
  readonly reason: string;               // why it asked: rule text or mode default
  readonly suggestions: readonly GrantSuggestion[];  // exact pattern, tool, capability/server
}

type ApprovalAnswer =
  | { requestId: string; decision: "allow_once" }
  | { requestId: string; decision: "allow_session"; rule: string }
  | { requestId: string; decision: "allow_always"; rule: string }
  | { requestId: string; decision: "deny"; reason?: string };
```

Both are plain JSON. The engine does not call the terminal. It returns
`{ outcome: "ask", request }`; the application's `authorizeTool` implementation
hands the request to an `ApprovalChannel` and awaits the answer:

```ts
interface ApprovalChannel {
  request(request: ApprovalRequest, signal?: AbortSignal): Promise<ApprovalAnswer>;
}
```

The interactive CLI supplies a channel backed by the prompt. Non-interactive
runs supply one that answers `deny` immediately with reason "approval required;
not available in non-interactive mode" (criterion a8). The a11 test supplies a
channel that writes the serialized request to a child process and reads the
answer back. `turn-steering` later replaces the channel with the
answer-approval command; `tool-call-rendering` adds the display payload to the
request.

The resulting `AgentToolPolicyDecision` carries `actor: "user"` when an answer
decided, `actor: "application"` when a rule or mode decided, and `rule` set to
the rule text, `mode:<name>`, `session_grant:<rule>`, or `non_interactive`.

The runtime's wait is already abortable. Escape during a prompt cancels the
turn as it does today.

### Session grants

`allow_session` adds a rule to the engine's session set. The set is written
into the session snapshot and restored on resume, and a new session starts
empty (criterion a5). Grants are listed and revocable in `/permissions`.

### Global-install prompt

`classifyGlobalInstallCommand` stays. In the engine's `bash` evaluation a
matched global install is treated as `ask` with the classifier's reason, unless
an allow rule matches the command, and it asks in every mode except `bypass`.
`BashTool.assertGlobalInstallAllowed` and the gate config are removed.
`PROPIO_ALLOW_GLOBAL_INSTALLS=1` keeps working as a deprecated alias that adds
a session allow for classified installs, with a warning.

### `/permissions` command

`/permissions` lists the preset, mode, rules by source, session grants, and the
last decision with the rule that made it. Subcommands: `allow <rule>`,
`ask <rule>`, `deny <rule>`, `remove <rule>`, `revoke <grant>`, `preset <name>`,
`mode <name>`.

## As implemented in `policy-core`

Merged 2026-11-13 as propio-agent#103. Three review rounds changed or added
the following; where this list and the proposals above disagree, this list is
current. The code is in `src/policy/` and the README section "Reusable policy
API (provisional)".

- **Store:** `update(owner, change)` replaces `save` (see "Store"). An engine
  runs its own store reads and writes one at a time and adopts each result
  before the next starts, so a slow read cannot undo a later write. Engines
  cache settings; `reload()` reads again.
- **Answers:** `answer()` claims the request before anything is awaited and
  reopens it if the answer fails, so only the first answer counts. Allow
  answers re-read the stored rules and are refused (outcome `deny`, actor
  `application`) when a deny added while the request waited now matches. An
  always-allow grant is never written over a matching deny and never moves a
  rule out of `deny`; it is removed from `ask`.
- **Exact grants:** exact path grants are absolute and glob-escaped (braces
  included), so they cover one file and do not follow the owner into another
  workspace. No exact grant is offered for a compound command or one ending in
  `:*`. Exact command grants match the command text regardless of `cwd` or
  `env` (open question 1 in requirements.md).
- **Paths:** the workspace root and home directory are matched literally;
  patterns never negate. A `~/` rule fails the load when no home directory was
  supplied. Paths are POSIX only.
- **Compound commands:** besides the operators listed under "Rule syntax", a
  lone `&` and the redirections `<` and `>` keep an allow rule from matching.
- **Approval request:** `sessionId` and `toolCallId` are optional; the request
  also carries `target` and `rule`. Ids default to random UUIDs, so an answer
  for one engine never matches a request raised by another.
- **Targets:** policy never inspects arguments by tool name. The caller passes
  a `PolicyTarget`: `{ kind: "path", path }` (absolute, normalized, symbolic
  links resolved), `{ kind: "command", command }`, or `{ kind: "mcp",
  serverPrefix }`.
- **Presets** are deep-frozen. **Tool metadata** is `ExecutableTool.metadata`;
  `ToolRegistry.getToolMetadata(name)` resolves undeclared tools, including
  MCP tools, to `external`, not read-only, not concurrency-safe. `src/mcp`
  does not import `policy`.
- **Dialect rules from `schema-validation`** are under "Schema validation".

## Notes for enforcement

Things the next slice must handle that the proposals above do not spell out:

- **Where the pieces live.** `ApprovalChannel`, the `authorizeTool`
  implementation, and the mapping from tool arguments to a `PolicyTarget` are
  application code, not `policy`. Keep the wiring in a new module that `Agent`
  calls, not in `src/agent.ts` itself.
- **Targets.** File tools: resolve the path the way the tool will
  (`resolveToolPath`), then resolve symbolic links (including for a file that
  does not exist yet, via its parent) before passing it. `bash`: the command
  text, plus whatever open question 1 decides about `cwd` and `env`. MCP: the
  `mcp__<server>` prefix; `src/mcp/toolName.ts` builds the names.
- **Global installs.** The engine knows nothing about them. The application
  calls `classifyGlobalInstallCommand` and turns an `allow` whose `source` is
  `mode` (no explicit rule) into an `ask` with the classifier's reason, except
  in `bypass`. Then remove `BashTool.assertGlobalInstallAllowed` and keep
  `PROPIO_ALLOW_GLOBAL_INSTALLS=1` as a deprecated session grant.
- **Cache freshness.** `evaluate()` uses the engine's cached rules. Decide
  when to `reload()`; once per turn is the simplest. Answers already reload.
- **Plan and discover.** Their existing checks run first; classifier-approved
  read-only `bash` and writes to the approved plan file are allowed with rule
  `agent_mode:<mode>` without consulting policy (see "Modes").
- **Order in the runtime.** Tool scope, then argument validation, then
  `authorizeTool`, which is where policy runs (`src/agent-core/runtime.ts`).
- **Session grants** go into the session snapshot via `listSessionGrants()`
  and come back with `restoreSessionGrants()` on resume.
- **File store (for `approval-ui`).** `update` must be atomic across processes
  (lock file plus the existing atomic JSON writer), and `load` must return the
  latest completed update.


## As implemented in `enforcement`

Where this list and the proposals above disagree, this list is current. The
code is in `src/permissions/`, `src/ui/approvalPrompt.ts`, and the README
section "Tool permissions".

- **Wiring.** `ToolPermissions` (`src/permissions/toolPermissions.ts`) owns
  the engine for one `Agent`. `Agent.authorizeToolExecution` runs the plan and
  discover checks, then calls it. The engine loads on first use and reloads at
  the start of each turn.
- **Open question 1 (option C).** `PolicyTarget` for a command gained
  `detached?: boolean`. The application sets it when the resolved `cwd` is
  outside the workspace or `env` is non-empty. A command pattern, exact or
  prefix, never allows a detached command, and no exact grant is offered for
  one. "As compound commands do" is read literally: a whole-tool rule (`bash`)
  or capability rule still covers it, as it covers a compound command, because
  such a rule names no command text. Deny and ask rules match as before.
- **Unknown tools** are allowed through with rule `unknown_tool`, so execution
  reports "not found" and the operator is not asked about a call that cannot
  run.
- **No channel.** The design had non-interactive runs supply a channel that
  answers `deny`. Instead an `Agent` without a channel denies without asking,
  with rule `non_interactive` and actor `application`, so the trace does not
  attribute the denial to a user. The interactive CLI sets a channel.
- **Global installs.** Only the reason changes: a classified install that
  asks by mode default shows the classifier's reason. `BashTool` no longer
  gates installs and `shell.globalInstallGate` is gone from the tools API, so
  a consumer of `@propio-ai/agent/tools` that does not put policy in front
  now runs them. The deprecated setting allows classified installs with rule
  `env:PROPIO_ALLOW_GLOBAL_INSTALLS`, never over an explicit ask or deny rule.
- **`--permissions <preset>`** moved here from `approval-ui`. Without it,
  once the default became `ask`, a non-interactive run had no way to write or
  run commands until the file-backed store landed.
- **Minimal prompt.** Allow once or deny (`y`/`N`). Session and always grants
  from the prompt are `approval-ui`; session grants are exercised here through
  the channel in tests, and persist in the snapshot as
  `metadata.sessionGrants`.
- **Cancelling.** `PromptConfirmRequest` takes a `signal`; aborting the turn
  closes the prompt, and an answer that arrives after the abort is discarded.
- **Agent API.** `setGlobalInstallApprovalCallback` is replaced by
  `setApprovalChannel`; the constructor takes `permissions` (`store`, `owner`,
  `preset`, `mode`, `approvalChannel`). `AgentToolAuthorizationRequest` carries
  `toolCallId`. The trace configuration snapshot reports
  `approvalChannelConfigured`, `permissionPreset`, and `permissionMode` in
  place of `globalInstallApprovalCallbackConfigured`.
- **Review of #104.** `grep` and `find` walk the approved directory
  themselves (`src/tools/containedFiles.ts`): policy approves the root, so
  the walk opens only directories under it that the pattern can still match,
  never enters a link, and keeps a linked file only when it resolves under
  the root. `fast-glob` is gone; `tsconfig.json` declares the Node types,
  which TypeScript 6 no longer includes by default. Every untrusted field is
  shown with control and invisible characters escaped (`src/ui/visibleText.ts`),
  in the approval question and in tool-call lines at the `TerminalUi`
  boundary. The deprecated install setting covers only what
  `isUnambiguousGlobalInstall` recognizes: one command, no wrapper, whose
  subcommand is the manager's own install. For npm and pnpm every argument
  must be on an allowlist (the subcommand, `-g`, `--global`,
  `--location=global`, `--location global`, `--`, packages), because npm's
  parser takes separate boolean values, stops at `--`, and expands
  abbreviations. The command must also be plain literal words (no quoting,
  escapes, expansions, or other shell syntax), since the heuristic tokenizer
  does not split words the way the shell does. The broader classifier still
  supplies the prompt's reason. The PR is marked breaking (`!` and a
  `BREAKING CHANGE:` footer), which makes the squash commit a major release.
- **Tests.** `createTestAgent` and the direct constructions in
  `agent.test.ts` pass the `bypass` preset; tests about permissions construct
  their own.

## Notes for approval-ui

- The prompt renders from `ApprovalRequest` only; `request.suggestions` holds
  the grants to offer. `allow_always` needs the file-backed store first.
- `ToolPermissions.describe()` and `listSessionGrants()` exist for
  `/permissions`; revoking and rule edits need pass-throughs to the engine.
- The typed text of a confirm prompt is not echoed while a turn runs, because
  the cancel listener holds the terminal in raw mode. The full prompt should
  handle keys itself.
- The non-interactive denial message names `--permissions` only; add the
  settings rule once the file store exists.

## As implemented in `approval-ui`

Where this list and the proposals above disagree, this list is current.

- **Store.** `FilePermissionStore` (`src/config/permissionStore.ts`) serves one
  owner from the `permissions` object of `~/.propio/settings.json`. `update`
  holds an operating-system lock on `settings.json.lock`
  (`src/config/fileLock.ts`, `os-lock`), reads inside it, and writes with the
  existing atomic JSON writer, leaving other keys untouched. The lock file is
  never removed.
- **Validation.** The store checks shape with `zod` (unknown keys under
  `permissions` are errors) and also parses each rule and checks the preset,
  so an error names the file and field (`permissions.deny.1: ...`). The CLI
  loads rules at startup and exits on an unusable file.
- **Prompt.** `askOperator` (`src/ui/approvalPrompt.ts`): `y` once, `s`
  session, `a` always, `n` deny with an optional reason; `s` and `a` list
  `request.suggestions` to choose from. Only an explicit choice allows. It
  reads through `readLineFromKeys` (`src/ui/keyLineReader.ts`), which echoes
  and edits a line a key at a time, because the terminal is in raw mode while
  a turn runs. It does not go through the prompt composer.
- **`/permissions`** (`src/ui/permissionsCommand.ts`) uses
  `ToolPermissions.overview()`, `addRule`, `removeRule`, `revokeSessionGrant`,
  `setPreset`, and `setMode`; the agent exposes them as `agent.permissions`.
  `preset` and `mode` last for the session and are not stored. Edits record a
  `permissions_changed` configuration change in the trace.
- **Footer.** The permission mode is shown when it is not `ask`; bypass is
  shown as `BYPASS`.
- **Non-interactive denial** names the narrowest rule that would allow the
  call and the settings file, as well as `--permissions`.
- **Review of #105.** In sandbox mode the store reads
  `/app/.propio/settings.json`, the read-only copy the wrapper mounts, and
  refuses to save (`resolveSettingsLocation`). Saving is offered only where
  `savingUnavailableReason()` is undefined: not in the sandbox, and not
  without the optional `os-lock`. The Dockerfile's build stage builds
  `os-lock` (toolchain plus `-Wno-error=incompatible-pointer-types`) and
  fails if it cannot be loaded. The settings file is replaced with mode
  `0600` or stricter. `PolicyEngine.answer` and `PermissionStore.update` take
  a `signal`; the store checks it inside the lock as it commits. An explicit
  `"permissions": null` is an error. The non-interactive denial for a matched
  ask rule names that rule instead of suggesting an allow rule or preset.
- **Not changed.** `runtimeConfig` still reads `runtime` settings from the
  container's home in sandbox mode, so those are ignored there; only
  permissions read the mounted file. That predates this spec.
- **Not done.** Rules are user-wide (project settings are phase 10). If the
  settings file becomes unusable between turns, the turn fails with the right
  message under the provider's error heading.

## Slices

One PR each, in order. Status lives in [delivery.json](delivery.json).

| Slice | Content | Criteria |
| --- | --- | --- |
| `schema-validation` | Validation in the registry and MCP path; `invalid_arguments` status | a1 |
| `policy-core` | `src/policy` and its subpath export: metadata, rules, modes, presets, engine, approval types, store interface, in-memory store. Tool metadata on built-ins and MCP. No behavior change in the CLI. | a7, a10, a12 |
| `enforcement` | Engine wired into `authorizeTool`; approval channel; non-interactive denial; workspace confinement; session grants in the snapshot; global-install folding; trace actor; `--permissions` flag. Interactive CLI uses a minimal prompt so the default can flip in this PR. | a2, a3, a5, a6, a8, a9, a11 |
| `approval-ui` | Full prompt with grant choices, file-backed store, `/permissions`, footer label, README | a2, a4, a5 |

## Checks by risk

| Risk area | Check |
| --- | --- |
| Rule matching | Table tests for each rule form; chained and substituted `bash` commands never match an allow; path traversal (`..`, symlinked parents) resolved before matching |
| Precedence | Deny beats session grant, persisted allow, and every preset |
| Async approval | Abort while waiting; channel throws (fails closed); answer for an unknown request id rejected |
| Serialization | `JSON.parse(JSON.stringify(request))` deep-equals the request; answer supplied by a child process |
| Isolation | Two engines, two owner scopes, one process; guarded-import test forbids `fs`, `process`, `net`, and application imports from `src/policy` |
| Regression | Existing plan and discover mode tests pass unchanged |

Repository checks for every slice: `npm test`, `npm run build`,
`npm run format:check`, `npx fallow audit`.

## Cross-repository changes

| Repository | Change |
|------------|--------|
| propio-agent | All four slices. |

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Prompts become tedious and `bypass` becomes the habit | Read-only tools in the workspace never ask; session and persisted grants; `accept-edits`; grant suggestions offered on every prompt |
| Default flips to `ask` and breaks existing non-interactive scripts | Denial message names the flag and rule that would allow it; changelog entry; open question 6 |
| `bash` prefix rules approve more than intended | Allow rules refuse compound commands; documented as a guard, not a boundary |
| Validation rejects calls that worked before because a schema is stricter than its tool | Run the existing suite and fixtures through validation in `schema-validation` and fix schemas there |
| Prompt work collides with `tool-call-rendering` | The prompt renders from the approval request only; phase 3 swaps in the display payload |
| `src/agent.ts` grows again | Wiring goes in a new application module that `Agent` calls, not into `Agent` itself |

## Alternatives considered

- **Enforce in the registry `approve` callback.** Rejected: MCP tools do not go
  through that registry, and the callback returns a boolean with no rule or
  actor for the trace.
- **A prompt callback passed into the engine.** Rejected: it cannot be answered
  from another process, which the session protocol and the server require.
- **Structured rule objects in settings instead of strings.** Rejected for now:
  harder to edit by hand and to type in `/permissions`. The parser produces a
  structured form internally, so a second syntax can be added later.
- **`zod` for argument validation.** Rejected: schemas arrive as JSON Schema,
  including from MCP servers.
