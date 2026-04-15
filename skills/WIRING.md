# Skill Wiring: Canonical to Claude Code

How canonical skills become Claude Code project skills.

**Layout contract:** `docs/adr/2026-04-14-canonical-skill-layout.md` is
the authoritative decision on per-skill-directory vs flat-file layouts.
New skills use the per-skill-directory layout; Phase 0 flat-file skills
stay flat and get fixtures via sibling `<skill-id>.fixtures.yaml` files.

**Agent-callable primitives:** `docs/adr/2026-04-14-primitives-subpackage.md`
defines the `packages/tools/primitives/` convention for stateless,
side-effect-free, typed helpers that any worker or canonical skill can
import directly.

## Source-of-truth order

```
canonical definition  →  adapter  →  project skill
skills/canonical/         skills/adapters/claude/    .claude/skills/
(owns the logic)          (translates for Claude)    (discovery routing only)
```

**Canonical** is the source of truth. Adapters translate. Project skills route.

## How it works

Each `.claude/skills/<name>.md` is a **thin pointer** — it contains:

- Frontmatter with `description`, `canonical_source`, and `adapter_source`
- A single instruction: "Read and follow the adapter file"
- No skill logic of its own

This means:

- Skill logic lives in exactly one place (canonical + adapter)
- `.claude/skills/` only handles Claude Code discoverability
- Updating a skill means editing the canonical definition and/or adapter — not the project skill file

## When to update what

| Change | Edit | Then |
|--------|------|------|
| Skill logic changes | `skills/canonical/...` | Update adapter if the change affects Claude-facing instructions |
| Claude-specific phrasing | `skills/adapters/claude/...` | No other changes needed |
| Skill description changes | `skills/adapters/claude/...` | Mirror the description into `.claude/skills/<name>.md` frontmatter |
| New skill added | Canonical + adapter + registry | Create new `.claude/skills/<name>.md` pointer |
| Skill removed | Remove from registry | Delete `.claude/skills/<name>.md` |

## Adding a new Claude project skill

1. Canonical definition exists in `skills/canonical/`
2. Claude adapter exists in `skills/adapters/claude/`
3. Skill is registered in `skills/registry.yaml` with `claude` in `target_runtimes`
4. Create `.claude/skills/<skill-id>.md` with this template:

```markdown
---
description: <copy from adapter frontmatter>
canonical_source: <path to canonical definition>
adapter_source: <path to claude adapter>
---

<!-- This is a Claude Code project skill. It routes to the canonical skill via its adapter. -->
<!-- Do not add skill logic here. Edit the adapter or canonical source instead. -->

Read and follow the skill instructions at `<adapter_source>`.

That adapter implements `<canonical_source>` — the canonical source of truth for this skill.
```

## Drift prevention

- Project skill files contain no logic — they can't drift from canonical
- The only field that can drift is `description` — keep it synced with the adapter frontmatter
- `registry.yaml` tracks which skills have project skill wiring via `project_skill` field
- If a canonical skill changes significantly, review the adapter — the project skill needs no change

## What `.claude/skills/` is NOT

- Not the source of truth for skill definitions
- Not a place to write new skill logic
- Not independently maintained from the canonical layer
- Not a replacement for `skills/adapters/claude/`
