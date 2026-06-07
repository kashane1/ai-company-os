# CLAUDE.md

`ai-company-os` — a local-first platform for running an AI-driven software
business from an always-on Mac. See `README.md` for full context.

> This file is loaded into every Claude session, so it stays lean: it links to
> the canonical docs instead of restating them. Keep it that way — add detail to
> the linked source, not here.

## Orient first

1. [REPO_MAP.md](REPO_MAP.md) — the **single source** for the five-zone model,
   repository layout, where files go, edit boundaries, and the canonical
   read-first order. Don't duplicate that content elsewhere; link to it.
2. [docs/preflight-for-agents.md](docs/preflight-for-agents.md) — boundaries to
   respect before mutating anything.
3. [docs/agent-model.md](docs/agent-model.md) — worker roles and the
   orchestration model (canonical; [AGENTS.md](AGENTS.md) is the stub).

## Binding rules (enforced every session)

- **Skill disambiguation:** if multiple trigger phrases could apply to a
  message, ASK which skill to invoke — never silently route to the first match.
- **Skill edits:** logic lives in `skills/canonical/` (source of truth) and
  `skills/adapters/` (per-runtime translation). `.claude/skills/*` are thin
  routing pointers — never add skill logic there. See [skills/WIRING.md](skills/WIRING.md).
- **Edit boundaries:** `packages/policies/`, `packages/schemas/`,
  `skills/canonical/`, and `skills/registry.yaml` require explicit founder
  approval. `state/` is runtime-only, never source. Full list lives in REPO_MAP
  under "Where things must NOT go".
- Skill catalog + trigger phrases: [docs/skills-index.md](docs/skills-index.md).

## Conventions

- Python-first for platform code; lightweight frameworks until the architecture
  proves itself.
- No hidden orchestration in prompts. Structured task I/O with typed payloads.
- Approval gates on irreversible actions.
