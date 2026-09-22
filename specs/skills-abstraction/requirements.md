# Requirements: skills-abstraction

Implement phase 2 of docs/agent-abstractions-plan.md in propio-agent only, as confirmed by the user.

- Establish a provisional @propio-ai/agent/skills API inside the existing package, following phase 1. No destination repository or second production application has been identified.
- Separate parsing, explicit discovery, diagnostics, registry, matching, precedence and invocation metadata from Propio configuration and execution policy.
- Accept ordered absolute discovery roots with source labels and an explicit absolute workspace root. Imports must not scan directories or start the CLI.
- Preserve CLI parsing, diagnostics, duplicate behavior, deepest matching path activation and invocation behavior. Relative touched paths resolve against the supplied workspace, matching the existing CLI absolute-path behavior without using process.cwd().
- Keep menus, slash commands, model/effort warnings, fork rejection and permission enforcement in the application.
- Exercise the public API with existing regression tests and a standalone catalog consumer. Verify declarations and clean-install consumption of the packed package.
- Do not publish packages or invent repository details. A separate package and real second production consumer remain release milestones.
