# Requirements: tool-permissions

## Summary

Introduce the `policy` primitive and put an operator decision in front of tool
side effects.

This is phase 1 of the roadmap in
[maturity-audit-roadmap/design.md](../maturity-audit-roadmap/design.md). The
problem is finding 1 of
[maturity-audit-roadmap/audit.md](../maturity-audit-roadmap/audit.md): execute
mode allows every enabled tool, nothing asks the operator, and tool arguments are
never validated. The runtime already evaluates an `authorizeTool` integration
before every dispatch and journals the decision; the CLI never supplies it with
an operator decision.

## Goals

- Validate every tool call against its JSON Schema before dispatch and return a
  structured validation error to the model.
- Give every tool metadata: a capability set (`read`, `workspace_write`,
  `process`, `network`, `external`), a read-only flag, and a concurrency-safe
  flag. MCP tools default to `external` and not concurrency-safe.
- A rule model of `allow` / `ask` / `deny`, matched on tool name plus an argument
  pattern (path glob for file tools, command prefix for `bash`, server and tool
  for MCP). Deny wins over ask, ask over allow.
- Permission modes: `ask` (default), `accept-edits`, `plan`, `discover`, and
  `bypass` (today's behavior, explicit and visibly labeled).
- Workspace confinement for file tools by default; paths outside the workspace
  ask.
- An approval prompt in the TUI showing the exact operation, offering: allow
  once; allow for the session (this pattern, this tool, or this capability /
  MCP server); always allow (persisted rule); deny with an optional reason
  returned to the model.
- Rules in the user settings file, editable by hand, and a `/permissions` command
  to list, add, and remove rules, list and revoke session grants, and show which
  rule decided the last call.
- Named presets that expand to a mode plus a rule set (read-only, ask, accept
  edits, bypass), selectable by flag, setting, or command, with user rules
  layered on top.
- Non-interactive runs resolve `ask` to deny unless a flag or rule allows it.
- Fold the global-install prompt into the rule model.
- Every decision keeps its trace record, with actor `user` where the operator
  decided.
- An `ask` decision is a serializable approval request and a later answer, not a
  callback into terminal code.
- Rules load and save through an injected store that takes an owner scope.

## Non-goals

- Changing the plan and discover bash classifiers (`src/modes/bashPolicy.ts`).
  They stay as they are.
- Project-level settings. Rules are user-global until `project-config` (phase 10).
- Concurrent tool execution. The concurrency-safe flag is recorded here and used
  by `tools-hardening` (phase 11).
- Redefining skill `allowed-tools` semantics. It keeps narrowing the tool
  surface; the decision belongs to `subagents-and-skills` (phase 13).
- The typed command set of the session protocol (`turn-steering`, phase 2) and
  the display payload (`tool-call-rendering`, phase 3). This spec defines only
  the approval request and answer, shaped so those phases can adopt them.
- Sandboxing. Rules guard against unintended actions; they are not a security
  boundary against a hostile command.
- Authentication or tenancy. The owner scope is an opaque value; the CLI passes
  a constant.
- Publishing `policy` as its own package (`primitive-packages`, phase 14).

## Acceptance criteria

IDs match [delivery.json](delivery.json).

- [ ] **a1** No tool implementation is reachable with schema-invalid arguments.
- [ ] **a2** In `ask` mode, `write`, `edit`, `bash`, and any MCP call produce a
      prompt before executing; `read`, `grep`, `find`, and `ls` inside the
      workspace do not.
- [ ] **a3** A denial returns to the model as a tool result and the turn
      continues.
- [ ] **a4** A persisted allow rule suppresses the prompt in a new session; a
      deny rule cannot be overridden by an allow rule, a session grant, or a
      preset.
- [ ] **a5** Approving a tool or a request type for the session suppresses
      further prompts of that kind until the session ends, is restored on
      resume, and does not carry into a new session.
- [ ] **a6** A fresh install with no configuration starts in `ask`.
- [ ] **a7** Every preset is covered by a test that states which calls it
      allows, asks about, and denies.
- [ ] **a8** Non-interactive mode never blocks on a prompt.
- [ ] **a9** Each decision appears in the trace with rule and actor.
- [ ] **a10** `policy` imports nothing from the application and passes a
      guarded-import test.
- [ ] **a11** An approval request survives a JSON round trip, and a test answers
      one from outside the process that raised it.
- [ ] **a12** Two policy instances with different owner scopes in one process do
      not see each other's rules.

## Constraints from later phases

- Approval requests and answers must survive a JSON round trip.
- No primitive may hold process-level state.
- `policy` imports no other primitive. `tools` may import `policy`.

## Affected repositories

<!-- Confirmed names are listed in repos.txt -->

`propio-agent`, as named for this phase in the roadmap.

## Open questions

The roadmap section is a brief; [design.md](design.md) settles what it left
open.

Agreed on 2026-11-12 as proposed in the design: rule syntax, settings schema,
preset definitions, the approval request and answer, and `ajv` as the
validator. No upgrade notice is needed for the change of default to `ask`.

Permission mode is a separate setting from the existing `execute` / `plan` /
`discover` agent mode. In plan and discover, classifier-approved read-only
`bash` commands and writes to the approved plan file do not prompt.

Open (raised in review of `policy-core` on 2026-11-13, needed before
`enforcement`):

1. Whether exact command grants should be bound to the working directory and
   environment overrides. Today `bash(npm test)` matches that text whatever
   the call's `cwd` or `env`. The options put to the owner:
   - **A.** Leave text matching as it is; it is documented in the README.
   - **B.** Add a working-directory part to the rule syntax, for example
     `bash(npm test @ /work/project)`.
   - **C.** Keep text matching, but let no allow rule cover a `bash` call whose
     `cwd` is outside the workspace or that sets `env`; such calls always ask,
     as compound commands do. No new syntax. Implemented in `enforcement`,
     where `bash` arguments become a policy target.

   Recommended: **C**. Not yet decided by the owner.
