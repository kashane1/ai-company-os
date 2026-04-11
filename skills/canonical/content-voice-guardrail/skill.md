# Skill: content-voice-guardrail

Kind: agentic
Owner: gtm
Runtimes: claude

## Purpose

Before any `CONTENT_DRAFT` result is persisted, check the draft against
the product's `gtm/voice.md`. Output is `pass`/`fail` plus, on fail, a
diff of off-voice phrases and suggested rewrites.

## Contract

Inputs:

- `draft`: str — the full post body including any trailing hashtags.
- `voice_guide`: str — the raw text of `docs/products/<product>/gtm/voice.md`.
- `platform`: "tiktok" | "instagram" | "threads" | "x".

Outputs:

- `verdict`: "pass" | "fail".
- `off_voice`: list of `{phrase, reason}` objects. Empty on pass.
- `suggested_rewrite`: str or null. Only when verdict is "fail".

## Fail-closed rule

If the voice guide is unparseable, empty, or missing required sections, the
skill returns `verdict=fail` with `off_voice=[{phrase: "", reason: "voice guide unparseable"}]`
rather than letting the draft through.

## Banned patterns (hard fails)

- Any phrase in the voice guide's "Banned phrases" section.
- ≥3 consecutive identical emoji.
- All-caps words longer than 4 characters.
- "guaranteed" or "guarantee" applied to fishing results.
