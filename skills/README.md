# Skills

This directory contains the canonical skill layer for `ai-company-os`.

## What is a skill

A skill is a **reusable, bounded procedure** that an agent (Claude, Codex, or a future runtime) can follow to accomplish a specific job. Skills are the repo's way of encoding repeatable workflows as portable definitions rather than one-off prompts.

A skill must have:

- a clear job to be done
- explicit inputs and outputs
- defined edit boundaries (what it may change)
- defined forbidden areas (what it must not touch)
- validation steps that confirm success

## What is NOT a skill

- A vague prompt blob with no structure
- A one-time task that will never repeat
- A policy definition (those live in `packages/policies/`)
- A schema definition (those live in `packages/schemas/`)
- Architecture documentation (that lives in `docs/`)
- App feature code (that lives in `apps/` or `products/`)

## Directory structure

```
skills/
  README.md              # this file
  registry.yaml          # index of all canonical skills
  spec.md                # the canonical skill specification
  canonical/
    shared/              # skills usable across products and lanes
    handoffs/            # skills that manage transitions between lanes
    products/
      fishing-logbook/   # product-scoped skills
  adapters/
    claude/              # Claude Code / .claude compatible skill files
    codex/               # Codex-compatible task packet templates
```

## Canonical vs adapters

The **canonical definition** is the source of truth for every skill. It lives under `skills/canonical/` and uses the format defined in `skills/spec.md`.

**Adapters** are runtime-specific translations of canonical skills. They exist under `skills/adapters/<runtime>/` and derive from canonical definitions. If a canonical definition changes, the adapter should be updated to match.

Adapters must never contain logic or instructions that are absent from the canonical definition.

## How to add a new skill

1. Write the canonical definition under the appropriate `skills/canonical/` subdirectory
2. Follow the format in `skills/spec.md`
3. Add an entry to `skills/registry.yaml`
4. If the skill should be available in a specific runtime, create the adapter under `skills/adapters/<runtime>/`
5. Validate the skill against its own `validation_steps` before merging

## Relationship to repo architecture

Skills respect the existing lane and policy boundaries defined in `AGENTS.md` and `docs/architecture.md`. A skill cannot grant itself authority that the repo architecture does not support.
