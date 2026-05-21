---
description: Scan the entry docs for broken repo-relative paths and stale product-name patterns, classify each finding (fix_now / allowlist / founder_decision / ignore), and emit a structured report. Invoke for "scan for stale doc refs", "doc-path audit", "find doc drift".
canonical_source: skills/canonical/stale-doc-detector/skill.md
---

# Stale Doc Detector (Claude adapter)

You are running the `stale-doc-detector` skill from
`skills/canonical/stale-doc-detector/skill.md`. Follow the canonical
definition.

## Quick reference

1. **Run the helper script.** `scripts/ci/check_doc_paths.sh`.
   Capture stdout + exit code. Each broken line has shape
   `<doc> -> <token>`.

2. **Classify each path finding** as one of:
   - `fix_now` — broken repo-relative path or backtick shorthand
   - `allowlist` — documented runtime-only path (state/, build/, etc.)
   - `founder_decision` — change might affect a real product
   - `ignore` — false positive (URL fragment, illustrative text)

3. **Scan for legacy slugs** in the configured docs plus
   `docs/ios-conventions.md`. Default `legacy_slug_hints` is
   `["fishing-logbook"]`. Resolve the current product id from
   `infra/products.json` and propose a replacement only when the
   context is a clear path; otherwise classify
   `founder_decision`.

4. **Assemble the report** at
   `state/artifacts/stale-doc-detector/<run-id>/report.md`.

5. **Verdict.** `pass` if no `fix_now` findings. `fail` otherwise.

## Disambiguation

- Skill-registry drift → `skill-stocktake`.
- Pre-PR comprehensive verification → `verification-loop` (which
  should call this skill as a sub-check).
- Open-ended search → `Explore` agent.

If two trigger phrases could match, ask the operator.

## Edit boundaries

Read-only outside `state/artifacts/stale-doc-detector/`. **Never
edits docs**, even when `fix_now` is the classification — the
operator (or a downstream editing skill) does the edit. Never opens
files under `products/`.
