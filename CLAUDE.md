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
- See `AGENTS.md` for worker boundaries and roles.

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

### How skills are organized

```
skills/canonical/    — source-of-truth skill definitions
skills/adapters/     — runtime-specific translations (claude/, codex/)
skills/registry.yaml — index of all skills with metadata
.claude/skills/      — Claude Code project skill discovery (routing pointers)
```

### How Claude project skills work

Files in `.claude/skills/` are **thin routing pointers**, not content forks. Each one tells you to read and follow the corresponding adapter file, which implements the canonical definition.

**Do not add skill logic to `.claude/skills/` files.** Edit the adapter or canonical source instead.

### Wiring convention

See `skills/WIRING.md` for the full convention. The short version:

- Canonical definition is the source of truth
- Claude adapter translates for Claude's runtime
- Project skill file handles Claude Code discoverability only
- `registry.yaml` tracks which skills have project skill wiring

### Available Claude project skills

- **product-artifact-chain** — validate/extend the founder-to-spec artifact chain
- **codex-claude-handoff** — transfer work between Codex and Claude
- **ios-ui-polish-review** — review iOS code for UI polish and platform conventions
- **ios-to-appstore-handoff** — prepare handoff from iOS build to App Store release
- **supervisor-goal-decomposition** — decompose founder goals into structured worker tasks
- **app-store-positioning-pack** — generate App Store positioning outputs from product artifacts
- **niche-research-brief** — research a product niche and produce a scored, classified research brief with persistent memory
- **gtm-artifact-refresh** — consume a research brief and refresh all GTM artifacts with archetype mix balance
- **content-factory** — generate finished slide images from authored backlog items (Gemini backgrounds + Pillow text overlay)
- **content-scheduler** — push generated slides to Postiz as draft posts for human review

## Trigger phrases → skills

When the user's message matches one of these patterns (including paraphrases), read and follow the named skill's Claude adapter before doing anything else:

- "hand this to codex" / "dispatch to codex" / "delegate to codex" / "queue a task for codex" / "find tasks for codex" / "have codex fix X" / "send this to codex" / "run this through codex" → `skills/adapters/claude/codex-claude-handoff.md` (local dispatch, on-device worker)
- "use codex cloud" / "dispatch via codex cloud" / "queue this on codex cloud" / "open a PR via codex cloud" → `docs/codex-cloud-dispatch.md` (Chrome-MCP-driven chatgpt.com/codex/cloud → PR against `staging`)
- "decompose this goal" / "break this down into tasks" / "turn this into worker tasks" → `skills/adapters/claude/supervisor-goal-decomposition.md`
- "validate the artifact chain" / "check product artifacts" → `skills/adapters/claude/product-artifact-chain.md`
- "review the iOS code" / "polish review" → `skills/adapters/claude/ios-ui-polish-review.md`
- "prep the app store handoff" / "cut a release" → `skills/adapters/claude/ios-to-appstore-handoff.md`
- "generate app store copy" / "positioning pack" → `skills/adapters/claude/app-store-positioning-pack.md`
- "research the niche" / "run niche research" / "research this audience" / "build a research brief" / "what does this audience care about" → `skills/adapters/claude/niche-research-brief.md`
- "refresh the GTM artifacts" / "update the content backlog" / "propagate the research" / "refresh content from brief" / "balance the content mix" → `skills/adapters/claude/gtm-artifact-refresh.md`
- "create content" / "generate slides" / "make posts" / "run the content factory" / "generate images for the backlog" → `skills/adapters/claude/content-factory.md`
- "schedule posts" / "push to postiz" / "send to drafts" / "schedule content" / "queue drafts" → `skills/adapters/claude/content-scheduler.md`

Following the adapter is not optional — the protocols exist because they encode boundaries, pre-flight checks, and failure modes that aren't obvious from the user's request alone.

## Conventions

- Python-first for platform code
- Lightweight frameworks until architecture proves itself
- No hidden orchestration in prompts
- Structured task I/O with typed payloads
- Approval gates on irreversible actions
