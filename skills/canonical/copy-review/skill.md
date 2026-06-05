# Skill: copy-review

Kind: agentic
Owner: gtm
Runtimes: claude

## Purpose

Critique a block of website copy against Better Business Web's documented voice
and the `## Banned phrases` list in `voice.md`, then propose an on-voice rewrite.
Runs a draft → critique → rewrite loop over already-extracted prose. Reports only
— makes no file writes. Standalone; does not wrap the social-shaped
`content-voice-guardrail`.

## Contract

Inputs:

- `copy`: str — prose under review, already extracted from its source (the caller
  extracts; this skill judges prose, not markup).
- `surface`: "marketing" | "demo" — `marketing` applies the whole banned list;
  `demo` skips the "Agency-site only" subsection.
- `voice_guide_path`: str — path to `docs/products/<product>/gtm/voice.md`.
- `proper_nouns`: list — brand/business name tokens to whitelist before any
  literal match (e.g. `["Elevate Fitness"]`).
- `language`: str (optional, default "en") — the caller declares it; the skill
  does not auto-detect (unreliable on short fragments).

Outputs:

- `verdict`: "pass" | "fail".
- `off_voice`: list of `{phrase, reason}` objects. Empty on pass.
- `suggested_rewrite`: str or null. Null on pass, or when `language` != "en".

## Procedure

The loop is draft → critique → rewrite, applied to the supplied `copy`:

1. **Load** `voice_guide_path` as opaque text (read-only file I/O); parse its
   `## Banned phrases` subsections. If missing, empty, or unparseable → fail
   closed (below).
2. **Scope** by `surface`: `marketing` applies both subsections; `demo` skips
   "Agency-site only".
3. **Whitelist** `proper_nouns` before any literal match — match only the
   proper-noun (capitalized) occurrences; a lowercased standalone use of the same
   token (e.g. the verb "elevate") is still flagged.
4. **Language gate** — if `language` != "en": skip the literal lists (English
   only), run only the structural judgment, and return `suggested_rewrite` = null.
5. **Critique — literal:** flag any in-scope banned word or opener that survives
   the whitelist. Each is an `off_voice` entry with the matched phrase + reason.
6. **Critique — judgment:** banned constructions ("It's not just X, it's Y" and
   the contrast-reveal family); the em-dash budget (~1 per 500 words — count,
   never grep for `—`); clichés and unbacked claims; uniform sentence rhythm.
7. **Verdict:** `fail` if any `off_voice` entry exists; otherwise `pass`.
8. **Rewrite:** on `fail` (and English copy), produce one `suggested_rewrite` that
   removes every finding while preserving the copy's claims. Invent no new facts,
   prices, services, or superlatives.

## Banned patterns (hard fails)

- Any in-scope phrase from `voice.md`'s `## Banned phrases`, after whitelisting
  `proper_nouns`.
- Any banned construction; em-dash density over the ~1-per-500-words budget; a
  claim or superlative with no concrete fact behind it.
- **Explicitly NOT hard fails** (the social guardrail's fishing-specific rules,
  not inherited here): the word "guarantee" (bbw leads with a guarantee), a single
  legitimate em-dash, and emoji/all-caps limits.

## Fail-closed rule

If `voice.md` is unparseable, empty, or missing its `## Banned phrases` section,
the skill returns `verdict=fail` with
`off_voice=[{phrase: "", reason: "voice guide unparseable"}]` and
`suggested_rewrite=null`, rather than letting the copy through unreviewed.

## Allowed edit boundaries

- None. This skill is read-only: it reads `voice_guide_path` and returns a report.
  It writes no files. Rewrites are *suggested* in the output for a human (or the
  calling playbook) to apply.

## Forbidden areas

- Does not write or edit any file, including the copy under review.
- Does not edit `products/`, `packages/`, `apps/`, `infra/`, or `state/`.
- `packages.json` copy is read-only even as a review target: report findings but
  route fixes upstream to `packages/agency/catalog.yaml`.
- Never attach a real reviewer's name to a paraphrase (demo attribution rule).
