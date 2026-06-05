---
description: Critique a block of website copy against Better Business Web's brand voice and banned-phrase list, then propose an on-voice rewrite. Run on-demand before committing marketing copy edits, or as the demo build's voice self-critique step. Reports only — writes no files.
canonical_source: skills/canonical/copy-review/skill.md
---

# Copy Review

You are running the copy-review skill from `skills/canonical/copy-review/skill.md`.
Follow the canonical definition — it owns the inputs, outputs, the draft →
critique → rewrite procedure, the scope/whitelist/em-dash rules, and the
fail-closed and boundary contracts. This adapter is a quick reference only.

## Quick reference

- Inputs: `copy` (extracted prose), `surface` {marketing|demo}, `voice_guide_path`,
  `proper_nouns[]`, `language` (optional, default `en`).
- Outputs: `verdict` {pass|fail}, `off_voice[]` of `{phrase, reason}`,
  `suggested_rewrite` (str|null).
- The caller extracts prose first — you judge prose, not markup.

## Steps

1. Load `voice.md`; if missing/empty/no `## Banned phrases` → fail closed.
2. Scope by `surface`; whitelist `proper_nouns` (capitalized occurrences only).
3. If `language` != "en": structural judgment only; `suggested_rewrite` = null.
4. Literal pass → judgment pass (constructions, em-dash budget ~1/500, clichés, rhythm).
5. Fail on any finding; produce one rewrite that keeps all claims and invents nothing.

## Boundaries

- May edit: nothing (reports only) — writes no file, including the copy under review.
- Must not touch: `products/`, `packages/`, `apps/`, `infra/`, `state/`.
- `packages.json` is read-only — route fixes to `packages/agency/catalog.yaml`.
- Do NOT inherit the social guardrail's fishing rules ("guarantee", single em-dash, emoji/caps).
