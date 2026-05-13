# Glossary — Life Clock

> **Status:** Onboarding aid. The Life Clock product carries a lot of internal vocabulary — tone modes, reveal escalator, healthspan dial, archetype, plan affinity, anchor, etc. This glossary is the one-page index so new collaborators don't have to triangulate from multiple specs. For canonical rules on each term, follow the linked spec.

## Surfaces / IA

- **Today tab** — Daily ritual surface. Life Clock headline + drivers + Today's Plan + check-in + monthly logging banner. See [`PRD.md`](PRD.md) § Today.
- **History tab** — Retrospection surface: weekly cards, daily list, per-day drill-down (Pro), override editing (Pro). See [`PRD.md`](PRD.md) § History.
- **Future tab** — Long-horizon trajectory + What-If Simulator (Pro). See [`PRD.md`](PRD.md) § Future.
- **Profile tab** — Tone / palette / reminders / HK auth / Subscription / Badges / SafetyNet / Privacy / About. See [`PRD.md`](PRD.md) § Profile.
- **WrapUpSheet** — In-app ceremonial moment for yesterday + weekly wrap-ups. Pull-only on cold-launch, never push. See [`wrap-up-spec.md`](wrap-up-spec.md).
- **PaywallSheet** — Reachable paywall throughout-app (3-tier). See [`paywall-spec.md`](paywall-spec.md).
- **PaywallPrimaryView** — Onboarding-terminal paywall (single-tier annual). Different job from PaywallSheet — see same spec.
- **SafetyNet** — Emotional-safety refuge. Profile → "If this app is making you anxious." See [`safetynet-spec.md`](safetynet-spec.md).
- **QuickLog** — Manual habit logging sheet (Today + toolbar). Fuel / Rhythm / Whole food / Extras / Recovery / Strength / Nicotine.

## Onboarding terms

- **Reveal escalator** — The 29-screen onboarding flow that builds emotional commitment before the first time-delta reveal. See [`reveal-escalator-spec.md`](reveal-escalator-spec.md).
- **Healthspan dial** — The one-time, bounded ±5y anchor adjustment at the end of the reveal escalator. Atomic write to `UserProfile.personalAdjustmentYears` + `anchorAdjustedAt`; not re-editable post-escalator.
- **Archetype** — A persona label computed during the `analyzing` → `archetypeReveal` beats. Stored in `UserProfile.archetype`.
- **Anchor** — The healthspan baseline number the user sets via the dial. The trajectory math projects from this anchor.
- **Q9 inferred-softer rule** — When PSS-10 (stress) or UCLA-3 (loneliness) scores indicate risk, the reveal escalator's later beats automatically soften tone register even if the user picked firmDirect. Vision Decided 2026-05-12.
- **OnboardingDraft** — Transient `@State` holding the user's onboarding inputs. Never persists for under-13-blocked users (`AGE_COMPLIANCE.md` § Item 2).
- **Under-13 hard block** — Terminal screen reached when DOB resolves to age < 13. No HK consent, no SwiftData write, no telemetry value, no paywall. See [`AGE_COMPLIANCE.md`](AGE_COMPLIANCE.md).

## Tone + voice

- **Tone modes** — Three voices the user picks from: `gentle` / `coach` (default) / `firmDirect`. Vision Decided 2026-05-04. The dropped `mementoMori` is gone. See [`microcopy-spec.md`](microcopy-spec.md).
- **firmDirect** — The dramatic register. Short, specific, no hedging. The previously-named "Memento Mori."
- **Tone pools** — Tone-aware copy variants in `Sources/App/ToneMode.swift`. Each user-facing string has 3 variants. See [`microcopy-spec.md`](microcopy-spec.md).
- **Earn time** — The wedge phrasing (not "earn time **back**" — that was dropped 2026-05-11). Forward-pull framing across all marketing + in-app copy.
- **Drama, not cruelty** — Tone rule for the firmDirect register. Direct ≠ mean.
- **Memento Mori** — Dropped tone name. Shipped equivalent is `firmDirect`. References in archived founder-pack docs only.

## Engines + math

- **ClockEngine** — Additive minutes ledger. `calculateBaseline / calculateDailyDelta / calculateWeeklyTrend`. See [`CLOCK_MODEL.md`](CLOCK_MODEL.md) § Two engines.
- **HealthspanEngine** — Years-based healthspan projection. The headline projection number. Coefficient table in [`healthspan-coefficients.md`](healthspan-coefficients.md). See [`CLOCK_MODEL.md`](CLOCK_MODEL.md).
- **QuestEngine** — Generates Today's Plan actions (formerly "quests"). The label is internal; user sees "Today's Plan."
- **AffinityEngine** — Picks the most-relevant Today's Plan actions for the user based on prior behavior. See [`plan-quest-generation-affinity.md`](plan-quest-generation-affinity.md).
- **NarrativeEngine** — Composes long-form narrative copy on Future tab + WrapUp Pro. See [`narrative-engine-spec.md`](narrative-engine-spec.md).
- **HealthKitAggregator** — Rolls per-type HK presence into `sourceCompleteness` for the confidence model.
- **ConfidenceModel** — High / Medium / Low buckets keyed off `sourceCompleteness`. See [`confidence-model-spec.md`](confidence-model-spec.md).
- **WrapUpCoordinator** — Decides whether to present yesterday or weekly wrap-up. Pure function. See [`wrap-up-spec.md`](wrap-up-spec.md).
- **OverrideService** — Atomic write path for Pro correction power. See [`override-contract.md`](override-contract.md).
- **MonthlyLoggingCalculator** — Computes the calendar-month logged-days count (replaced the dropped `DietStreakCalculator`). Vision Decided 2026-05-06: monthly count, no streak.
- **AgeGate** — Pure functions for under-18 / under-13 routing. See [`AGE_COMPLIANCE.md`](AGE_COMPLIANCE.md).
- **SubscriptionStore** — `@Observable` source of truth for Pro entitlement via StoreKit 2.

## Data model

- **UserProfile** — Identity, baseline survey, onboarding completion, dial anchor, prefs, PSS-10 / UCLA-3 scores, parental longevity. See `LifeClockSchema.swift`.
- **DailyHealthSnapshot** — Per-day HK-derived signals + `overridesData` + `originalHealthKitValuesData` + `lastRecomputedAt`.
- **HabitLog** — Daily user-entered habit signals (alcohol / smoking / diet quality / diet rhythm / whole-food anchor / stress / strength / notes).
- **LifeClockEstimate** — Projected age + projected date + healthspan score + daily delta + confidence + explanation.
- **TimeLedgerEntry** — One ledger row (id / date / title / delta / source / confidence / driverType / questSlug).
- **Quest** — Quest-pool entry (slug / date / title / target / progress / reward / genre / completedAt). User-facing label is "Today's Plan."
- **WeeklyReport** — Net delta + drivers + lever + confidence.
- **DailyReflection** — Tone-aware reflection prompt response (short text).
- **QuestEvent** — Completion telemetry per Today's Plan action.
- **CumulativeSummaryCache** — Derived rollups for History performance. Cache-invalidation contract in schema header.

## Pro + monetization

- **Pro Annual** — The shipped Pro subscription tier ($49.99/yr). Headlines + 5 v1 unlock bullets. See [`MONETIZATION.md`](MONETIZATION.md).
- **Pro Monthly / Lifetime** — Same Pro entitlement, different cadence ($7.99/mo / $129.99 one-time).
- **Free/Pro rule** — "Free = understanding, Pro = depth, archive, and correction power." See [`MONETIZATION.md`](MONETIZATION.md) § Free vs Pro Rule.
- **Best conversion moments** — 5 named moments where Pro signals fire. 3 wired / 2 deferred as of 2026-05-13. See [`paywall-spec.md`](paywall-spec.md) § Upsell moments.
- **No trial in v1** — `Products.storekit` has `introductoryOffer: null` for both subscriptions. See [`MONETIZATION.md`](MONETIZATION.md) § Trial stance.
- **Pro touchpoints** — The 7 surfaces where Pro signaling lives. See [`pro-value-rule.md`](pro-value-rule.md) § Pro touchpoint inventory.

## Notifications + reminders

- **Daily reminder** — One opt-in local notification. Evening 8…22 hour clamp. Vision Decided 2026-05-09.
- **Pull-not-push** — Wrap-ups present as in-app sheets on cold-launch; never push notifications. Vision Decided 2026-05-09.
- **Mortality lexicon ban** — Notification copy may never carry the dramatic register. See [`microcopy-spec.md`](microcopy-spec.md) § Safety registers.

## Premium / craft

- **Premium-feel audit** — Read-only audit against [`premium-bar.md`](premium-bar.md). Emits elevation prompts. Sibling to pro-value-audit.
- **Premium-readiness** — Green / Yellow / Red flag computed against the premium-bar rubric.
- **Motion vocabulary** — `Motion.Duration.{instant, beat, breath}` + named curves. See [`motion-spec.md`](motion-spec.md).
- **Lighting convention** — World-fixed shadow from upper-left, opacity 0.22, offsets 0.35×/0.85× of reference size. See [`lighting-spec.md`](lighting-spec.md).

## Compliance + safety

- **Pro-value audit** — Read-only audit against [`pro-value-rule.md`](pro-value-rule.md). Emits monetization prompts. Sibling to premium-feel-audit.
- **Submission-blocker** — Cross-sibling escalation tier for findings that block App Store submission (a11y failures, dark patterns, value-claim mismatches, age-gate gaps).
- **COPPA actual-knowledge posture** — The legal defense for the under-13 hard block. See [`PRIVACY_COMPLIANCE.md`](PRIVACY_COMPLIANCE.md) § Users under 13.
- **GDPR-K** — EU under-16 (or per-jurisdiction floor) consent threshold. v1 ships a uniform 13+ floor with the local-first defense. See [`PRIVACY_COMPLIANCE.md`](PRIVACY_COMPLIANCE.md) § Users in the EU.
- **Cal AI rejection vector** — April-2026 active-rejection pattern for wellness apps. PaywallPrimaryView design hardened against this. See [`AGE_COMPLIANCE.md`](AGE_COMPLIANCE.md) § Item 4.

## Build + fixtures

- **JUMP_TO fixtures** — UITest scaffolding for jumping to specific screens / states without walking the full onboarding flow.
- **MockHealthKitService** — Simulator-default HK service. Real reads come from `LiveHealthKitService`.
- **`LIFECLOCK_SIMULATOR_PRO_DISABLED=1`** — Env flag forcing the Free state in DEBUG sim. Default is Pro (yes, counter-intuitively).
- **`LIFECLOCK_USE_MOCK_HEALTH=1`** — Force `MockHealthKitService` even on a real device.
- **xcodegen** — Project generation from `project.yml`. Regenerate with `xcodegen generate` after schema or target changes.

## Documents and skills

- **Founder pack** — The original 2026-04-27 numbered docs (`00_..14_`). Now archived at `archive/founder-pack-2026-04-27/`. Canonical docs are unnumbered.
- **Vision.md** — The operating ledger. Decided constraints (operator-only ratchet) + Open Questions (active list).
- **Premium-bar.md / Pro-value-rule.md** — The two audit rubrics. Read-only — operator owns; audits never edit.
- **Premium-feel-backlog / pro-value-backlog** — Audit output files. Dated; consumed by `simulator-driven-polish`.
- **simulator-driven-polish** — Skill that consumes audit-emitted prompts and runs the polish loop.
- **PHASE_STATUS.md** — Current sequencing source of truth. Beats `GTM_LAUNCH_PLAN.md`'s 90-day plan.
- **CLAUDE_HANDOFF.md** — Handoff doc for new Claude sessions joining the work.
- **ASC_CHECKLIST.md** — App Store Connect setup walkthrough.
