# CLAUDE.md

## What this repo is

`ai-company-os` — a local-first platform for running an AI-driven software business from an always-on Mac. See `README.md` for full context.

## Key architecture rules

- The platform owns orchestration. Codex writes code. Workers specialize.
- Policies live in `packages/policies/`. Workers do not own policy.
- Runtime state lives in `state/`, never in source folders.
- iOS implementation and App Store release are separate lanes.
- Product artifacts live in `docs/products/<product-id>/`.
- Product source lives in `products/<product-id>/`.
- See `AGENTS.md` (stub) and `docs/agent-model.md` (full) for worker boundaries and roles.

## Repository layout

- `apps/` — worker and API entrypoints
- `packages/` — shared code (config, db, policies, queue, schemas, tools)
- `products/` — managed product source (e.g. `catchbook-ios/`)
- `docs/` — architecture docs, product artifacts, decisions
- `infra/` — local infrastructure (db, scripts, fastlane, launchd)
- `state/` — runtime data (repos, worktrees, artifacts, checkpoints, logs)
- `skills/` — canonical skill definitions, adapters, and registry

## Skills

This repo has a canonical skill system. Skills are reusable, bounded procedures with explicit inputs, outputs, and edit boundaries.

```
skills/canonical/    — source-of-truth skill definitions
skills/adapters/     — runtime-specific translations (claude/, codex/)
skills/registry.yaml — index of all skills with metadata
.claude/skills/      — Claude Code project skill discovery (routing pointers)
```

Files in `.claude/skills/` are **thin routing pointers**, not content forks. Each one tells you to read and follow the corresponding adapter file, which implements the canonical definition. **Do not add skill logic to `.claude/skills/` files.** Edit the adapter or canonical source instead. See `skills/WIRING.md` for the full convention.

**Disambiguation rule (binding):** if multiple trigger phrases could apply to a user's message, Claude MUST ask which skill to invoke rather than guess. Do not silently route to the first match.

The full skill catalog and trigger phrases live in `docs/skills-index.md`. Read it when you need to know which skill to invoke. Following the named adapter is not optional — the protocols encode boundaries, pre-flight checks, and failure modes that aren't obvious from the user's request alone.

## Conventions

- Python-first for platform code
- Lightweight frameworks until architecture proves itself
- No hidden orchestration in prompts
- Structured task I/O with typed payloads
- Approval gates on irreversible actions
