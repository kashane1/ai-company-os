# Canonical Skill Specification

Every skill in this repo follows this format. Keep it lean.

## Required fields

```yaml
id: kebab-case-unique-id
name: Human-readable name
purpose: One sentence describing the job this skill does.
owner_agent: Which worker or agent type runs this skill.
  # Valid: supervisor, engineering, ios, appstore, claude, codex, any
target_runtimes:
  - claude     # Claude Code / Claude agent
  - codex      # Codex CLI
stage: draft | active | deprecated
```

## Scope fields

```yaml
inputs:
  - description of each required input

outputs:
  - description of each expected output

allowed_edit_boundaries:
  - directories or file patterns this skill may modify

forbidden_areas:
  - directories or file patterns this skill must not touch
```

## Execution fields

```yaml
dependencies:
  - other skills or repo assets required before this skill can run

validation_steps:
  - concrete checks to confirm the skill succeeded

handoff_contract:
  what_is_handed_off: what the next step receives
  handed_to: which lane or agent picks up next
  # omit if the skill is terminal
```

## Instruction body

After the YAML frontmatter, include the skill's instructions as markdown.

These instructions should be:

- imperative ("Do X", not "You should do X")
- bounded (stay within `allowed_edit_boundaries`)
- concrete (reference real paths, schemas, and conventions from the repo)

## Adapter notes (optional)

```yaml
claude_adaptation_notes: |
  Notes for packaging this skill as a Claude Code SKILL.md
codex_adaptation_notes: |
  Notes for rendering this skill as a Codex task packet
```

## Example

```yaml
id: example-skill
name: Example Skill
purpose: Demonstrates the canonical skill format.
owner_agent: engineering
target_runtimes: [claude, codex]
stage: draft
inputs:
  - a task ID referencing an existing engineering task
outputs:
  - a validated diff artifact in state/artifacts/
allowed_edit_boundaries:
  - state/worktrees/
  - state/artifacts/
forbidden_areas:
  - packages/policies/
  - infra/
dependencies: []
validation_steps:
  - diff artifact exists and is non-empty
  - no files modified outside allowed boundaries
handoff_contract:
  what_is_handed_off: validated diff artifact path
  handed_to: supervisor for review
```

## Format rules

- Use YAML frontmatter delimited by `---`
- Instruction body follows the closing `---`
- One skill per file
- Filename matches the skill `id` with `.md` extension
