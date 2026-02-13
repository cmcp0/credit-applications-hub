# AGENTS.md instructions for /Users/carloscaceres/local/marius/code_samples/credit-applications-hub

<INSTRUCTIONS>
## Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. Below is the list of skills that can be used. Each entry includes a name, description, and file path so you can open the source for full instructions when using a specific skill.

### Available skills
- agent-creation-guide: Comprehensive guide for creating Cursor subagents. Use when creating agents, designing agent architectures, or when detailed agent creation guidance is needed. (file: /Users/carloscaceres/local/marius/code_samples/credit-applications-hub/.agents/skills/agent-creation-guide/SKILL.md)
- code-slop-removal: Guide for removing AI-generated code slop. Use when cleaning up AI-generated code, removing unnecessary comments, defensive code, type casts, or style inconsistencies. (file: /Users/carloscaceres/local/marius/code_samples/credit-applications-hub/.agents/skills/code-slop-removal/SKILL.md)
- context-compilation-guide: Comprehensive guide for generating and maintaining AGENTS.md. Use when compiling project context, discovering agents and skills, or maintaining living documentation. (file: /Users/carloscaceres/local/marius/code_samples/credit-applications-hub/.agents/skills/context-compilation-guide/SKILL.md)
- design-doc-creation-guide: Comprehensive guide for creating design documents from PRD phases. Use when creating design docs, defining functional specifications, or translating PRD phases into implementation plans. (file: /Users/carloscaceres/local/marius/code_samples/credit-applications-hub/.agents/skills/design-doc-creation-guide/SKILL.md)
- prd-creation-guide: Comprehensive guide for creating Product Requirements Documents. Use when defining products, creating PRDs, or when detailed product planning guidance is needed. (file: /Users/carloscaceres/local/marius/code_samples/credit-applications-hub/.agents/skills/prd-creation-guide/SKILL.md)
- credit-app-mvp-guide: Workflow for implementing and reviewing this repository's credit application MVP goals, including country rules, provider routing, async processing, and near-real-time updates. (file: /Users/carloscaceres/local/marius/code_samples/credit-applications-hub/.agents/skills/credit-app-mvp-guide/SKILL.md)
- compile-agents-context: Codex-native version of the init command for generating or refreshing AGENTS.md context and optional auto-watch rules. (file: /Users/carloscaceres/local/marius/code_samples/credit-applications-hub/.codex/skills/compile-agents-context/SKILL.md)

### How to use skills
- Discovery: The list above is the skills available in this session (name + description + file path). Skill bodies live on disk at the listed paths.
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description shown above, you must use that skill for that turn. Multiple mentions mean use them all. Do not carry skills across turns unless re-mentioned.
- Missing/blocked: If a named skill is not in the list or the path cannot be read, say so briefly and continue with the best fallback.
- How to use a skill (progressive disclosure):
1) After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
2) When `SKILL.md` references relative paths (for example, `scripts/foo.py`), resolve them relative to the skill directory listed above first, and only consider other paths if needed.
3) If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed for the request; do not bulk-load everything.
4) If `scripts/` exist, prefer running or patching them instead of retyping large code blocks.
5) If `assets/` or templates exist, reuse them instead of recreating from scratch.
- Coordination and sequencing:
  - If multiple skills apply, choose the minimal set that covers the request and state the order you'll use them.
  - Announce which skill(s) you're using and why (one short line). If you skip an obvious skill, say why.
- Context hygiene:
  - Keep context small: summarize long sections instead of pasting them; only load extra files when needed.
  - Avoid deep reference-chasing: prefer opening only files directly linked from `SKILL.md` unless blocked.
  - When variants exist (frameworks, providers, domains), pick only the relevant reference file(s) and note that choice.
- Safety and fallback: If a skill cannot be applied cleanly (missing files, unclear instructions), state the issue, pick the next-best approach, and continue.

</INSTRUCTIONS>
