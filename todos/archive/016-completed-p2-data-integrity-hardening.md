---
status: completed
priority: p2
issue_id: "016"
tags: [code-review, data-integrity, tokenizer, redaction, ecc-gap-plan]
dependencies: []
---

# Problem Statement

Three data-integrity concerns from the second-pass review that aren't covered by todos 007 or 011. Each is a small, specific hardening for the serialized-report layer.

## Findings

### 1. Tokenizer mismatch guard at the data layer

Plan says "don't compare token counts across tokenizer versions" as prose only. No `fallback_variant` field, no guard in the reader.

**Fix:** Baseline JSON and every report include `tokenizer: Literal["tiktoken:o200k_base", "char_count_fallback"]` AND `tokenizer_version: str`. Any diff/comparison helper raises `TokenizerMismatch` unless both match. (Data-integrity finding #5.)

### 2. Redaction idempotence

Plan describes a regex strip in verification-loop but doesn't require stable ordering or output. Re-runs diff noisily.

**Fix:** Require the redaction helper to (a) sort keys, (b) use a fixed replacement token `"<REDACTED>"`, (c) pass `redact(redact(x)) == redact(x)` and produce stable JSON output. Test fixture asserts this. (Data-integrity finding #6.)

### 3. `known_drift: true` tag for baselines touching pre-existing drift

The plan acknowledges pre-existing drift in `social-post-safety/` (missing contract.yaml) and `post-run-validation` (path mismatch). Phase 2a ships with these unresolved. Phase 4 baseline will encode the known-broken state as "baseline truth", diffing noisily against the eventual fix.

**Fix:** Tag baseline entries touching these two skills with `known_drift: true` so future comparisons don't diff against broken rows. (Data-integrity bonus finding.)

## Proposed Solutions

### Option 1: Fold all three into the shared report dataclass + the redaction helper

- Add `tokenizer: str`, `tokenizer_version: str` to `ContextBudgetReport` and anywhere token counts leave the primitive.
- Add `known_drift: list[str]` to `StocktakeReport` (lists drifted skill ids that are documented pre-existing).
- Redaction helper lives in `packages/tools/primitives/_redact.py` with stable-output guarantees.

Pros:
- One place per rule
- Tests can lock all three invariants independently

Cons:
- Three small changes not one

Effort: small
Risk: low

## Recommended Action

Option 1.

## Acceptance Criteria

- [ ] `ContextBudgetReport` carries `tokenizer` + `tokenizer_version` fields
- [ ] `TokenizerMismatch` exception raised by any comparison helper on mismatch
- [ ] `packages/tools/primitives/_redact.py` exists with idempotent stable-output redaction
- [ ] Redaction fixture asserts `redact(redact(x)) == redact(x)` and sorted JSON output
- [ ] `StocktakeReport` carries `known_drift: list[str]` field
- [ ] Phase 2a baseline tags `social-post-safety` and `post-run-validation` as `known_drift: true`
- [ ] Plan document updated with the three hardenings

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
