# AGENTS Maintainer Rule

Keep `AGENTS.md` current as a living project context document.

## Trigger Conditions
Refresh context when any of the following changes:
- Agent or skill files in `.agents/`, `.codex/skills/`, `.cursor/skills/`
- Command files in `.cursor/commands/`
- Root/project structure (new top-level folders, major moves/renames)
- Architecture/messaging docs in `docs/`
- Build/test/dependency/deployment config files

## Non-Triggers
Do not refresh AGENTS.md for:
- Normal feature code edits without structural/tooling impact
- Minor text changes that do not affect conventions/workflows
- Generated artifacts

## Refresh Action
Run the init workflow using compile-agents-context defaults:
- `scan_depth=medium`
- `include_dependencies=true`
- `auto_watch=true`

Update:
- `/Users/carloscaceres/local/marius/code_samples/credit-applications-hub/AGENTS.md`
- `/Users/carloscaceres/local/marius/code_samples/credit-applications-hub/.cursor/rules/agents-maintainer.md` (this file) only if rule behavior needs adjustment.

## Verification Checklist
- Paths and section references in `AGENTS.md` still exist.
- Skill registry reflects current discovered skills.
- Agent/skill counts are recalculated.
- Timestamp is updated.
