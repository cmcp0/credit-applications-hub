---
name: compile-agents-context
description: "Generate and maintain AGENTS.md - a living document of project context and agent ecosystem"
args:
  - name: scan_depth
    description: "How deep to scan project structure (shallow|medium|deep)"
    isRequired: false
    default: "medium"
  - name: include_dependencies
    description: "Include external dependencies context (true|false)"
    isRequired: false
    default: "true"
  - name: auto_watch
    description: "Set up automatic cursor rule watcher (true|false)"
    isRequired: false
    default: "true"
---

# AGENTS.md Context Compilation

Create and maintain AGENTS.md - a living document of project context and agent ecosystem.
This command is backed by the Codex skill `compile-agents-context`.

## Process

1. Analyze project holistically (structure, purpose, tech stack, patterns)
2. Discover and catalog all agents and skills
3. Extract conventions (coding standards, architectural patterns, testing, deployment)
4. Generate AGENTS.md following structure in `.codex/skills/compile-agents-context/SKILL.md`
5. Create cursor rule for auto-maintenance if `auto_watch` is true

## Reference

For detailed guidance, refer to the **compile-agents-context** Codex skill at `.codex/skills/compile-agents-context/SKILL.md`.
For extended template guidance, also refer to the **context-compilation-guide** skill at `.agents/skills/context-compilation-guide/SKILL.md`.
These skills include:
- Complete project analysis process
- AGENTS.md structure template
- Context update decision logic
- Cursor rule specification
- Generation workflow
- Quality standards

## Output

Generate AGENTS.md with all sections populated. If `auto_watch` is true, also create `.cursor/rules/agents-maintainer.md`.

Provide summary with statistics, files created, and next steps.
