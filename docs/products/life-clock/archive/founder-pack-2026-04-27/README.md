# Founder Pack archive — 2026-04-27

This directory preserves the original Life Clock Founder Pack (April 27 2026) and the Codex MVP build prompt. **It is historical context only.** Treat the unnumbered files in `docs/products/life-clock/` as canonical.

## Why these were archived (2026-05-13)

By the time of the 2026-05-12 founder-pack-vs-app audit ([`../../founder-pack-audit-2026-05-12.md`](../../founder-pack-audit-2026-05-12.md)), every numbered file had drifted from its unnumbered counterpart and from the shipped app. Drift epicenters:

- 2026-05-01 IA refactor — Time Ledger and Quests folded into Today; Future tab added later.
- 2026-05-04 tone-mode rename — `mementoMori` → `firmDirect`.
- 2026-05-09 to 2026-05-12 onboarding rebuild + healthspan-engine + Q9 sensitive-consent.

Audit found ~90 drifts across 278 substantive claims (~32% drift rate). Maintaining two near-identical doc sets in the same folder produced drift faster than it was caught. Archive + canonical-unnumbered is the operational lesson.

## What's in here

| File | Notes |
|---|---|
| `00_EXECUTIVE_SUMMARY.md` | Subset of canonical `EXECUTIVE_SUMMARY.md`. |
| `01_BUSINESS_PLAN.md` | Subset of canonical `BUSINESS_PLAN.md`. |
| `02_PRODUCT_STRATEGY.md` | **Regression** — missing principle #8 ("Monetize depth, not comprehension") and the Core product sentence that the canonical `PRODUCT_STRATEGY.md` carries. If you read it, read the canonical first. |
| `03_PRD.md` | Byte-near-equivalent to canonical PRD.md content; the canonical was rewritten 2026-05-13 (Commit 2 of the audit) to reflect the 4-tab IA and Future tab. |
| `04_HEALTH_DATA_STRATEGY.md` | Subset of canonical HEALTH_DATA_STRATEGY.md. |
| `05_CLOCK_MODEL.md` | Predates the V1.2 diet composite inline in the canonical CLOCK_MODEL.md and the Q9 PSS+UCLA additions. |
| `06_UX_GAME_LOOP.md` | Older pre-2026-05-01 IA; "Memento Mori" naming. Superseded by canonical UX_GAME_LOOP.md. |
| `07_MONETIZATION.md` | Lists tone modes as Pro Annual unlocks (stale — they're Free per canonical MONETIZATION.md and the Free/Pro rule). |
| `08_APP_STORE_ASO.md` | Subset of canonical APP_STORE_ASO.md. |
| `09_PRIVACY_COMPLIANCE.md` | Was the only place the COPPA + GDPR-K sections lived. Those sections have been migrated to canonical [`../../PRIVACY_COMPLIANCE.md`](../../PRIVACY_COMPLIANCE.md) (Commit 3 of the audit). |
| `10_GTM_LAUNCH_PLAN.md` | Subset of canonical GTM_LAUNCH_PLAN.md. |
| `11_ROADMAP_METRICS.md` | Subset of canonical ROADMAP_METRICS.md. |
| `12_TECHNICAL_ARCHITECTURE.md` | Pre-implementation architecture spec. Canonical TECHNICAL_ARCHITECTURE.md was substantially rewritten 2026-05-13 to add HealthspanEngine, all V1.7 schema additions, and the Notifications constraints. |
| `13_CODEX_BUILD_PROMPT.md` | The Codex MVP prompt; superseded by the entire post-onboarding rebuild. |
| `14_OPEN_QUESTIONS.md` | Operating ledger moved to `vision.md` § Open questions. Of 19 questions here, 8 are now Decided in vision.md, 7 still open (mappable to vision OQs #1–#6), 2 stale (FP-8, FP-11). |
| `MASTER_FOUNDER_PACKAGE.md` | The single-file merge of the founder pack as delivered 2026-04-27. |
| `codex-build-prompt-2026-04.md` | Renamed from `CODEX_BUILD_PROMPT.md`. The prompt that produced the original MVP skeleton. No longer maps to shipped scope — a fresh agent reading it would build the wrong app. Core rules and exclusion list have been lifted into `vision.md`. |

## Special-case migrations (already done by Commit 3)

- `09b_AGE_COMPLIANCE.md` → renamed to canonical `../../AGE_COMPLIANCE.md` (the legal-compliance content is too operationally live to bury here).
- `09_PRIVACY_COMPLIANCE.md` §§ "Users under 13" + "Users in the EU" → migrated to canonical `../../PRIVACY_COMPLIANCE.md`.
- `app-store-positioning.md` → deleted (byte-identical duplicate of `08_APP_STORE_ASO.md`).

## How to use

If you're new to the project, **do not start here.** Start with `../../founder-brief.md` or `../../EXECUTIVE_SUMMARY.md`. Use this archive only when:

- Tracing the evolution of a specific decision.
- Looking for the original April 2026 sequencing rationale.
- Pulling illustrative copy (e.g. the Time Ledger example entries in `06_UX_GAME_LOOP.md:43–49`) that didn't make it into canonical docs.
