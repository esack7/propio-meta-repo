# Requirements: maturity-audit-roadmap

## Summary

Audit `propio-agent` and `propio-providers` for maturity as a daily-driver CLI and
as reusable primitives, and deliver a roadmap and follow-on spec plans for the
future state.

The agent is a CLI modeled on tools such as Claude Code, Codex CLI, and pi. The
owner wants to use it as their primary driver and to reuse its parts in future
Propio AI projects. Four problems stand in the way, as reported by the owner:

1. The agent runs with little to no permission control, so sessions are hard to
   steer.
2. The terminal interface is clunky, tool calls most of all.
3. Tools, MCP, and skills are integrated but immature.
4. Traceability has improved but is still awkward to use.

## Goals

- Record the current state of both repositories against a single maturity scale,
  with file-level evidence.
- Confirm or correct each of the four reported problems from the code.
- Define the target set of primitives, their responsibilities, and their
  dependency direction.
- Sequence the work into follow-on specs, each with scope, affected repositories,
  dependencies, and acceptance criteria concrete enough to start from.
- Identify the decisions the owner must make before the first follow-on spec
  starts.

## Non-goals

- Changing code in either repository. This spec is assessment and planning only.
- Creating repositories, packages, or releases.
- Live provider calls, paid smoke tests, or outcome trials.
- Comparison against `mature-agent-cli`.
- Re-auditing areas closed by `runtime-traceability` beyond checking that their
  conclusions still hold.

## Acceptance criteria

- [x] **a1** `audit.md` rates every subsystem of both repositories on one scale
      and cites the files behind each rating.
- [x] **a2** `audit.md` addresses permissions, TUI tool-call rendering,
      tools/MCP/skills maturity, and trace usability individually.
- [x] **a3** `design.md` defines the target primitives, what each owns, and the
      allowed dependency direction between them.
- [x] **a4** `design.md` contains an ordered roadmap in which every phase names
      its follow-on spec, repositories, dependencies, and acceptance criteria.
- [x] **a5** Open decisions are listed with a recommendation for each.
- [x] **a6** The owner has reviewed the roadmap and answered the open decisions,
      and the answers are recorded here.

## Affected repositories

<!-- Confirmed names are listed in repos.txt -->

`propio-agent` and `propio-providers`, as named in the request. Both are read
only for this spec.

## Decisions

Recorded on 2026-11-11. Detail is in `design.md`.

- **Package layout.** npm workspace inside `propio-agent` for the primitives and
  the CLI; a separate repository for the server and web chat.
- **Second consumer.** A web chat that calls a Propio backend server and uses MCP
  tools. Single user for now, designed so multi-user can be added. MCP tools
  only for now. Resumable CLI sessions are required; remote sessions are wanted
  later.

- **Default permission posture.** Ask by default. Permissions must be
  configurable, come with predefined settings, and allow approving all calls of a
  tool or request type for the whole session.
- **Terminal rendering.** Keep the hand-written renderer and fix its data model.
- **Server repository.** Named `propio-server`. It is in
  `project-repositories.yaml` as a commented, planned entry until the repository
  exists and has a clone URL.
- **Prior documents.** The August audit and harness guide are removed.
  `docs/agent-abstractions-plan.md` is kept because earlier specs cite it; this
  spec supersedes its package layout.

## Open questions

None. The `propio-server` clone URL is needed before `chat-server-spike`, not
before the first phase.
