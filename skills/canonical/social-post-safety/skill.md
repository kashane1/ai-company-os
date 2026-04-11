# Skill: social-post-safety

Kind: validator (pure Python; deterministic)
Owner: gtm
Runtimes: claude

## Purpose

Hard gate before `SOCIAL_POST_SCHEDULE`. Checks FTC disclosure presence on
paid campaigns, platform-TOS compliance, dead-link detection, and a
profanity/PII scan. Fails closed — any exception is treated as `fail`.

## Contract

Input: a dict with keys `draft`, `platform`, `campaign` (dict with at
least `paid: bool`), and `links` (list of URLs).

Output: `{verdict: pass | fail, reasons: [str, ...]}`.
