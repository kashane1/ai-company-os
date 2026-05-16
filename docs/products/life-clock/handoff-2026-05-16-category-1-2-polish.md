# Handoff — Life Clock Category 1 + 2 Polish — 2026-05-16

**Branch:** `claude/dazzling-roentgen-dfcc33` (worktree `.claude/worktrees/dazzling-roentgen-dfcc33`)
**Base:** `ec1361e` (main tip at session start)
**Source backlogs:** `premium-feel-backlog-2026-05-15-standard.md`, `pro-value-backlog-2026-05-15-standard.md` (both still **untracked** — left alone deliberately; commit them if you want them in the PR)

## What was requested

Batch the two 2026-05-15 audit backlogs into 3 categories, then execute Category 1 (all 7) and Category 2 (all 6) via the canonical `simulator-driven-polish` skill — one prompt per session, build-verified between each, operator Asks batched.

## Status at a glance

| Item | Tier | State |
|---|---|---|
| PV-P1 enumerate 5 ProPerks on onboarding paywall | Cat 1 | ✅ Done, committed, build-green |
| PF-P1 SupportMomentToast → lighting convention | Cat 1 | ✅ Done, committed, build-green |
| PF-P2 RevealEscalator + chart Motion.Duration migration | Cat 1 | ✅ Done, committed, build-green |
| PF-P7 OverrideSheet error copy → tone-aware | Cat 1 | ✅ Done, committed, build-green |
| PF-P5 WrapUp clock-face lighting visual verify | Cat 1 | ✅ Passed (a/b/c); item (d) was blocked, now unblocked by new knob |
| PV-P4 Profile Pro-perks recap visual verify | Cat 1 | ✅ Passed clean, no source change |
| PV-P6 Q6+Q12 vision reconciliation memo | Cat 1 | ✅ Memo produced; **operator ratified both** → written to vision.md |
| PF-P3 off-tier 0.32 + .snappy onboarding sweep | Cat 2 | ✅ Done, committed, build-green |
| PF-P4 numeric-display token + AccessibilityXXXL clamp | Cat 2 | ✅ Done, committed, build-green |
| **PV-P2 PaywallPrimaryView ↔ PaywallSheet shared-core extraction** | Cat 2 | ⚠️ **INCOMPLETE — uncommitted, BUILD FAILING** (see below) |
| PV-P3 Future proFooter full14plus visual verify | Cat 2 | ⛔ Not yet run |
| PF-P8 cross-surface motion-hierarchy sweep | Cat 2 | ⛔ Not yet run |
| PF-P6 Reduce-Motion visual verify | Cat 2 | ⛔ Not yet run (must run LAST — verifies migrated P2/P3/P4 state) |

## Commits on the branch (19, `371ff5a` → `4f47ea7`)

Cat 1 code: `371ff5a` `da05537` (PV-P1), `360b8bc` (PF-P1), `41e77fc` (PF-P2), `d9bec15` (PF-P7).
Cat 1 decisions/infra: `9464006` (SEED_BAD_YESTERDAY knob + vision Q6/Q12 ratification), `af72343` (PF-P5/PV-P4/PV-P6 deliverables), `2d244f5` (recon drivers), `407b2b6` `e057516` `4944b74` `d6284b9` (logs/recon).
Cat 2 code: `f661166` `97e7dae` (PF-P3), `ce7b307` `952d155` (PF-P4), plus `7d3c537` `736eedb` `4f47ea7` (PF-P3/PF-P4 logs).

Every committed item was independently re-verified with a headless `xcodebuild` (BUILD SUCCEEDED) after its session — the SourceKit editor diagnostics seen throughout are false positives (no checked-in `.xcodeproj`; xcodegen generates it only at build time).

## Operator decisions applied

- **Q6 (first-paywall placement) → ratified** as "after-reveal, before main app, with explicit labeled soft-skip." Written to `vision.md` Decided constraints (Monetization); Open question #6 struck/resolved.
- **Q12 (paywall voice) → ratified retroactively.** PV-P6's verbatim register review (no shaming/punitive copy) accepted as the marketing pass. Written to `vision.md`; Open question #12 struck/resolved.
- **PF-P5 fixture gap → fixed.** Added `LIFECLOCK_SEED_BAD_YESTERDAY=1` in `LifeClockLaunchConfiguration.swift` (mirrors `SEED_BAD_DAY` onto yesterday's seeded log, which is what WrapUp reads). Build-green. The negative-delta WrapUp lighting capture is now *reachable* but **was not yet run**.
- **Housekeeping → done.** Verification/memo deliverables + research captures committed; 3 throwaway test-recon drivers kept tracked for reviewers (matches the `d6284b9` precedent).

## ⚠️ PV-P2 — incomplete, do not trust as-is

The PV-P2 session (shared paywall-core extraction, iteration cap 6, the heaviest item) **crashed with a server error mid-refactor**. It never committed and never wrote a session log. Current uncommitted working-tree state:

- **New (untracked):** `products/life-clock-ios/Sources/Features/Paywall/PaywallProductsView.swift` (~15.5 KB extracted shared view)
- **Modified (uncommitted):** `PaywallPrimaryView.swift`, `PaywallSheet.swift`

**This state does NOT compile.** `xcodebuild` → BUILD FAILED with two real Swift errors (not SourceKit noise):

```
PaywallProductsView.swift:67:65: error: main actor-isolated property 'isPro'
  can not be referenced from a nonisolated autoclosure
PaywallProductsView.swift:67:30: error: main actor-isolated property 'lastError'
  cannot be accessed from outside of the actor
```

The refactor's no-behavior-change golden-lock contract (pricing/restore/fineprint byte-identical on both entry paths, `SubscriptionStore` re-injected at the new view boundary, Apple 3.1.2(c) equal-prominence) was **never verified**. Do not assume parity. Resuming PV-P2 means: fix the actor-isolation errors, complete and golden-verify both entry paths (onboarding terminal + Profile/History re-engagement), run the existing paywall UITests unmodified, then commit + session log. The partial work is preserved (uncommitted) — it has not been reverted.

## Outstanding Asks / follow-ups (none release-gating)

- **PV-P2** must be finished or explicitly reverted before this branch is PR-ready (currently the working tree won't build).
- **Negative-delta WrapUp lighting capture** — now unblocked by `SEED_BAD_YESTERDAY`; the actual capture (PF-P5 item d) has not been run.
- **PV-P1 `paywall.perks` CI assertion** is blocked by a *pre-existing* `testOnboardingV2FlowReachesPaywall` harness flake (fails at screen 1 on baseline `ec1361e`; not introduced by this work). `ProPerksTests` covers the verbatim guarantee in the meantime.
- **PF-P3** flagged `RevealEscalatorScreens.swift:428` bare `.snappy` (out of PF-P3 scope) as a next-pass migration.
- **PF-P4** flagged a repo-wide migration of the remaining role-family literals to `DesignTokens.Typography` (the enum now exists to make it mechanical).
- **Cat 2 remaining:** PV-P3, PF-P8, then PF-P6 last.

## How to resume

Working tree builds green if PV-P2's 3 uncommitted paths are set aside; with them it fails. Resume order: finish PV-P2 to green+committed → PV-P3 → PF-P8 → PF-P6 (PF-P6 must be last; it verifies the migrated motion state of PF-P2/P3/P4).
