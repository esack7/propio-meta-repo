# Tasks: maturity-audit-roadmap

This spec is assessment and planning only. It changes no code in either
repository, so [delivery.json](delivery.json) records the working agreement and
plans no repository slices. Acceptance is tracked in
[requirements.md](requirements.md). Implementation is delivered by the follow-on
specs listed in [design.md](design.md), each with its own delivery record.

- [x] Refresh both reference clones and record baseline commits.
- [x] Read prior audit, abstraction plan, and traceability reassessment.
- [x] Audit both repositories: [audit.md](audit.md).
- [x] Define target primitives, dependency direction, and roadmap: [design.md](design.md).
- [ ] Owner review of findings 2 and 3 (derived from code, not observed sessions).
- [x] Package layout and second consumer decided (2026-11-11).
- [x] Remaining open questions answered (2026-11-11).
- [x] Create the first follow-on spec (`tool-permissions`) with `create-spec`: [tool-permissions](../tool-permissions/requirements.md).

## Baseline checks (2026-11-11, Node 22.23.3)

Run in the reference clones at the commits recorded in [audit.md](audit.md).

- `propio-providers`: build passed; 21 suites, 462 tests passed.
- `propio-agent`: 114 of 116 suites passed (1,701 of 1,733 tests). The two
  failing suites are `src/auth/openai/__tests__/storage.test.ts` and
  `auth.test.ts`, and `npm run build` reports one type error in
  `src/auth/openai/secrets.ts`. All three have one cause: the clone's
  `node_modules` predates the commit that added `os-lock` and
  `@napi-rs/keyring`, so those modules are not installed. This is a stale
  install in the reference clone, not a defect at that commit. A feature
  worktree with a fresh `npm ci` should be green; confirm that before changing
  anything.
- The clone's `node_modules/@propio-ai/providers` is a symlink to the providers
  reference clone, left by `link-local-packages`. `npm ci` removes it.

Still not done: no provider was called and the CLI was not driven interactively.
Findings 2 and 3 in the audit therefore rest on the rendering code. The owner
should confirm them in a real session before `tool-call-rendering` is specified,
and note which behaviors are the most disruptive.

## Starting the next session

**Current (2026-11-13):** phase 1, `tool-permissions`, is under way: two of
its four slices are merged. Resume from
[tool-permissions/tasks.md](../tool-permissions/tasks.md), section
"Resuming". The steps below describe how that spec was started.

1. Read [audit.md](audit.md), then [design.md](design.md). Decisions are in
   [requirements.md](requirements.md) and are settled; do not reopen them.
2. This spec is complete once committed. It plans no code. Do not run
   `prepare-spec` on it.
3. Create the first follow-on spec with `create-spec`, named `tool-permissions`,
   repository `propio-agent`. Its scope and acceptance criteria are the
   `tool-permissions` section of the design. That section is a brief, not a
   design: the new spec still has to settle the rule syntax, the settings schema,
   the preset definitions, and the shape of the approval request and answer.
4. Two constraints from later phases bind the first three: approval requests,
   commands, and events must survive a JSON round trip, and no primitive may
   hold process-level state. See "Second consumer" and "Session protocol".
5. Each later phase gets its own spec in roadmap order. `chat-server-spike`
   needs the `propio-server` repository created first, and its planned entry in
   `project-repositories.yaml` uncommented with the real clone URL.
