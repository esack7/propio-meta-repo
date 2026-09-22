# Design: skills-abstraction

## Public boundary

@propio-ai/agent/skills exports loadSkills, parseSkillDocument, SkillRegistry, renderSkillDiscoveryBlock and skill contracts. parser.ts handles YAML metadata without filesystem access. nodeLoader.ts discovers immediate child skill directories of caller-provided roots and reads bodies when materialized. loader.ts remains the CLI convention adapter, supplying project and home .propio/skills roots.

Consumers supply workspaceRoot and ordered roots of { skillRoot, source }. Paths must be absolute. Discovery sorts skill metadata names and file paths within each root but preserves root order; source labels never reorder generic discovery. Unscoped duplicate names retain last-entry-wins behavior (the CLI supplies project then user). Matching path-scoped entries retain the existing deepest-root rule. The registry keeps its discovery order across activation and refresh. Roots are copied at construction, while refresh and materialization read current files.

Skill metadata is descriptive. Parsing and materialization never run shell substitutions, grant permissions, spawn agents, or apply models. Unknown fields remain diagnostic; supported metadata values such as context: fork remain visible for consuming runtimes to reject or implement. CLI runtime enforcement is unchanged.

## Compatibility and validation

The existing loader suite runs against both the CLI adapter and explicit public loader. Registry and discovery tests import the public entry point. New boundary tests cover caller order, refresh, relative path matching, metadata preservation and configuration independence. A standalone catalog example imports the packaged subpath, providing a second minimal consumer rather than claiming a production integration.

Build, full tests, formatting and Fallow audit are required. Pack and install the artifact in a clean temporary consumer, verify public declarations and example equivalence, and prohibit implicit home/cwd access and directory scans during import.

No cross-repository linking is needed because the provisional API and CLI reside in the same package. Separate extraction/publication awaits a real destination repository and production consumer.
