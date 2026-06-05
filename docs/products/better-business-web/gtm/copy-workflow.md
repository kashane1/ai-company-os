# Better Business Web — Copy Review Workflow

How the voice system is used day to day. Two surfaces, one shared anti-slop list
(the `## Banned phrases` section in `voice.md`).

## Before committing marketing copy

Run `/copy-review` over any copy you changed in:

- `products/better-business-web/site/src/components/LandingBody.astro` (inline copy)
- `products/better-business-web/site/src/data/portfolio.json` (the prose fields)

Call it with `surface: marketing`, `voice_guide_path:
docs/products/better-business-web/gtm/voice.md`, and the brand
(`"Better Business Web"`) in `proper_nouns`. Apply the suggested rewrite, re-run
until `pass`. This is **advisory** — one author editing his own copy, so it's a
habit, not a hard gate (plan D4).

**Do not** edit `products/better-business-web/site/src/data/packages.json` copy
directly — it is generated/synced from `packages/agency/catalog.yaml`. Fix package
copy upstream in the catalog, then regenerate (plan D5).

## Generated client demos

Handled inside the demo build, not here: the playbook injects the voice framework
at generation and runs the AI-tell gate at verify. See
`docs/demo-site-build-playbook.md` (§5) and `gtm/demo-voice-framework.md`.

## One-time operator setup (plan D8)

`/copy-review` is registered in `skills/registry.yaml`, but its Claude
project-skill pointer is operator-owned and not yet created. Once:

1. Create `.claude/skills/copy-review.md` (strict WIRING pointer — copy the format
   from `.claude/skills/gtm-artifact-refresh.md`, pointing at
   `skills/adapters/claude/copy-review.md` + `skills/canonical/copy-review/skill.md`).
2. Add `project_skill: .claude/skills/copy-review.md` to the `copy-review` entry in
   `skills/registry.yaml`.

Until the pointer exists, invoke the skill by reading its adapter at
`skills/adapters/claude/copy-review.md`.
