# Age Compliance — Apple App Review + COPPA + GDPR-K

> **Companion to [09_PRIVACY_COMPLIANCE.md](09_PRIVACY_COMPLIANCE.md).** That doc covers the HealthKit + general privacy posture. This doc covers the *minor-handling* surface specifically — what Apple requires, what US/EU law requires, and where the lines actually are.

> **Status:** Operator-approved 2026-05-10. Items 1/2/5 are pre-launch blockers. Items 6–11 are deferred risk-mitigation; not required for v1.

> **Source research:** [polish-2026-05-09-age-gate-thresholds.md](polish-2026-05-09-age-gate-thresholds.md) (the audit of what the app does today) + the 2026-05-09 best-practices research synthesis cited inline below.

---

## TL;DR

The app's existing 12+ rating no longer exists in Apple's taxonomy — it was deprecated in July 2025 and Life Clock was auto-mapped to **13+**. Three things are *binding* for v1:

1. **Hard-block under-13 users at the DOB picker.** US COPPA "actual knowledge" doctrine attaches the moment we collect a DOB indicating age <13. The FTC February 2026 policy statement blesses "ask DOB → block" as a safe harbor that does NOT itself trigger verifiable-parental-consent obligations, *as long as we act on the result and don't proceed to collect personal info*.
2. **Re-run the App Store Connect age-rating questionnaire** on the new 4+/9+/13+/16+/18+ tiers and update [ASC_CHECKLIST.md](ASC_CHECKLIST.md). The Jan 31 2026 deadline has passed.
3. **Add an explicit "we do not knowingly collect data from users under 13" statement** to the privacy policy and update [PRIVACY_COMPLIANCE.md](09_PRIVACY_COMPLIANCE.md).

Everything else (parental gates before the paywall, EU 16-floor, symmetric input-side gating for 13–17, mortality-framing softening for teens) is risk mitigation that Apple does not currently require and that the operator has explicitly chosen to defer.

---

## 1. The rating system change you may have missed

**Before July 2025:** 4+ / 9+ / 12+ / 17+. Life Clock targeted 12+.

**After July 2025 (deadline Jan 31 2026):** 4+ / 9+ / **13+ / 16+ / 18+**. Apple [auto-mapped](https://developer.apple.com/news/?id=ks775ehf) every existing app's rating; legacy 12+ became 13+.

What this means for Life Clock:
- The codebase still references "12+" in [README.md](../../../products/life-clock-ios/Sources/Engines/AgeGate.swift), [ASC_CHECKLIST.md](ASC_CHECKLIST.md), and [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md). Update during the next polish pass.
- The questionnaire content categories changed shape. Operator must re-answer in App Store Connect.
- Apps that ignored the deadline lost the ability to ship updates ([Apple Developer News, July 2025](https://developer.apple.com/news/?id=ks775ehf)). **Verify Life Clock's rating status in ASC before next submission.**

| Tier | What triggers it | Life Clock fit |
|---|---|---|
| 4+ | No objectionable content | Too clean — Life Clock has alcohol/tobacco self-report and mortality framing |
| 9+ | Health/wellness topics; infrequent crude humor | Too low — alcohol/tobacco crosses 13+ line |
| **13+** | Infrequent alcohol/tobacco/drug refs; infrequent medical/treatment info | **Probably correct** for Life Clock |
| 16+ | **Frequent** medical/treatment info; unrestricted web access | Borderline — depends on whether reviewer reads "~N years on the table" reveal as "frequent medical info" |
| 18+ | Frequent alcohol/tobacco/drug; gambling | Not Life Clock |

**Ambiguity flag:** the questionnaire asks about *frequency*. Life Clock's mortality reveal is shown once per onboarding then suppressed — that is "infrequent" by any reasonable reading. The operator should answer the questionnaire honestly and document the answers.

**Critical point Apple does not bury:** age ratings are content advisories, not download gates. A 13-year-old can download a 16+ or 18+ app unless a parent has activated Screen Time / Ask to Buy. The rating's job is informational labeling and OS-level parental controls — not gating who can install. That changes the framing of the operator's original concern: "12-year-olds can download a 12+ app" was the wrong worry. The right worry is **what happens inside the app once any minor is there**, which is what items 1 and 5 address.

---

## 2. The COPPA actual-knowledge doctrine (US, under-13)

**The rule** ([FTC COPPA FAQ](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions)): general-audience apps must comply with COPPA *only if they have actual knowledge* a user is under 13. **Asking DOB creates actual knowledge** — the moment a user enters a DOB resolving to age <13, COPPA attaches.

**The escape valves:**

- **Verifiable parental consent (VPC).** Hard to implement, requires real-world-mappable verification (signed consent form, credit card check, government-ID check). Not viable for a wellness app at v1.
- **Don't have actual knowledge.** Don't ask DOB — but the app's lifespan calculation requires it, so this is not viable either.
- **Ask DOB *solely to determine age* and act on it.** The [FTC February 2026 policy statement](https://www.ftc.gov/news-events/news/press-releases/2026/02/ftc-issues-coppa-policy-statement-incentivize-use-age-verification-technologies-protect-children) explicitly creates a safe harbor for this: asking DOB does not itself trigger VPC obligations *if the operator acts on the result and does not collect personal info from under-13 users*.

**This is the cleanest defensible posture for Life Clock**, and it is item 1 in the implementation list below.

**What "act on it" means concretely:**
- The under-13 user reaches a terminal block screen and cannot proceed.
- Their reported birthDate is NOT persisted off-device (already true — `OnboardingDraft` is transient `@State`, never reaches `materialize()` for a blocked user).
- No HealthKit consent prompt fires for a blocked user.
- No subscription flow is reached.
- No telemetry event captures the under-13 DOB itself (only an `under13Block` screenAppeared event with no value bucket).

---

## 3. GDPR-K (EU, under-16) — what we are NOT doing in v1

GDPR Article 8 sets a minimum age for valid consent for "information society services" at **16, with member-state discretion to lower to 13.** Effective thresholds today:

| Country | Threshold |
|---|---|
| Germany, Netherlands, Luxembourg, Slovakia | 16 |
| Austria, Bulgaria, Czechia, Hungary, Italy, Lithuania, Poland | 14–15 |
| Belgium, Denmark, Estonia, Finland, France, Greece, Ireland, Latvia, Malta, Portugal, Romania, Spain, Sweden, UK | 13 |

**Operator decision (2026-05-10):** v1 ships with a uniform 13+ floor across all storefronts. This is non-compliant with GDPR-K in countries where the threshold is 14–16 in the strict reading. The defense:

- The app is local-first; no personal data is *transmitted* off-device. GDPR-K's verifiable-parental-consent requirement bites on processing that involves the user's data leaving the data subject's control. Local-only processing arguably falls outside Article 8's bite — but this is an unsettled reading.
- Once the app adds backup, sync, or analytics, this defense collapses. **Adding any off-device data flow without first implementing per-jurisdiction age floors is a regression on this posture.**
- Operator-accepted residual risk for v1.

This is item 7 in the deferred list.

---

## 4. Cal AI (April 2026) — the real present rejection vector

[Cal AI was pulled from the App Store on April 15 2026 and reinstated April 17](https://www.macrumors.com/2026/04/21/apple-cal-ai-app-store-removal/). The removal was for **§3.1.1 / §3.1.2 deceptive billing design**, not age handling:

- Weekly-equivalent pricing displayed more prominently than the actual charge.
- Free-trial toggle obscured auto-renewal.
- Second-chance subscription modal appeared after the user declined.

**This is currently the highest-probability rejection vector for wellness apps**, age aside. [PaywallPrimaryView](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift) was deliberately designed against this precedent (its docstring calls out the dropped two-stage paywall and the dropped "I'd rather pay full price" dismissal pattern). Operator should confirm:

- [x] No strikethrough pricing (deceptive without a real prior price). — already met
- [x] No "limited time" / countdown timer language. — already met
- [x] Auto-renewal terms always visible (not gated behind a toggle). — already met per docstring
- [x] Total amount the user will be billed shown with EQUAL prominence to per-period breakdown. — confirm against current UI
- [x] No second-chance modal after onClose. — already met (close just completes free fallback)

---

## 5. What v1 ships (the binding three)

### Item 1 — Under-13 hard block at DOB picker

- New `Under13BlockView` — terminal screen reached when `BaselineDOBView.onContinue` resolves to age <13.
- `OnboardingScreen.afterBaselineDOB(birthDate:asOf:calendar:)` — single source of truth, returns `.under13Block` or `.baselineSex`.
- `Under13BlockView` is in `noBackScreens` for forward navigation but allows the persistent-header back chevron so a user who mis-entered can correct. Going back lands on `BaselineDOBView` with the picker reset to its default 1990-06-12.
- No HealthKit prompt, no paywall, no profile materialization for blocked users.
- Tests: 4 cases pinning the routing decision (12-year-old → block, exactly-13 → proceed, 17 → proceed, nil DOB → block as safer default).

Implementation is in [polish-2026-05-10-under-13-block-and-asc-update.md](polish-2026-05-10-under-13-block-and-asc-update.md).

### Item 2 — ASC age-rating questionnaire re-run

[ASC_CHECKLIST.md](ASC_CHECKLIST.md) updated to reflect the new 4+/9+/13+/16+/18+ tiers. Recommended answers documented inline so the operator can run through ASC quickly. Recommended result: **13+**.

### Item 5 — Privacy policy under-13 statement

[09_PRIVACY_COMPLIANCE.md](09_PRIVACY_COMPLIANCE.md) updated with an explicit "We do not knowingly collect personal information from users under 13. If a user enters a date of birth indicating age <13, the app blocks them at the onboarding step before any data collection or HealthKit consent occurs. No DOB is persisted for blocked users." paragraph.

The actual public-facing privacy policy (the URL Apple's privacy nutrition label points to) needs the equivalent text. Operator-owned task; the doc-side is ours.

---

## 6. Deferred — risk mitigation NOT shipping in v1 (operator decision 2026-05-10)

Documented here so the rationale is preserved and these can be re-opened later without re-research.

| # | Item | Rationale for deferral |
|---|---|---|
| 6 | Symmetric input-side gating for 13–17 (suppress UCLA-3 / PSS / parent-ages-at-death) | Operator priority is compliance, not press resilience. Inputs are local-only — no off-device exposure. |
| 7 | Per-jurisdiction GDPR-K thresholds (EU 16-floor) | Local-first defense; revisit when any off-device flow is added. |
| 8 | Parental-style gate before the subscription paywall for 13–17 | Apple delegates to Family Sharing's Ask to Buy. Self-imposed gate is press-defense, not Apple-required. |
| 9 | Restrict `firmDirect` tone for 13–17 | §1.1.1 ("mean-spirited / distressing") risk is theoretical; no precedent. |
| 10 | Soften reveal escalator (`lifeGridRemaining` / `recoveryPreview` / `engineRevealAndDial`) for 13–17 | Pure product/tone question; no Apple rule. |
| 11 | Disable iCloud backup for the SwiftData store holding HealthKit-derived data | v1 has no CloudKit container (already `.none`). Only relevant when sync is added. |
| 12 | Internal §5.1.3 "not human-subject research" posture statement | Defensive; only relevant if Apple Review challenges the UCLA-3/PSS framing. |

---

## 7. Bottom line

For v1, the operator is shipping:

- **Apple-required:** age-rating questionnaire re-run (item 2).
- **Law-driven (US COPPA):** under-13 hard block (item 1).
- **Disclosure-required:** explicit privacy-policy under-13 statement (item 5).

The operator has explicitly chosen to defer items 6–12 as risk-mitigation rather than compliance-blockers. This is a defensible v1 posture given:

- The local-first architecture removes most COPPA / GDPR-K bite (no off-device data flow).
- The under-13 block + DOB-action approach is the FTC-blessed safe harbor.
- Cal-AI-style paywall design is already addressed in [PaywallPrimaryView.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift).
- Apple has not published rejections of mortality/wellness apps for under-18 audit-failures specifically; the residual risk is hypothetical.

If the app later adds backup, sync, off-device analytics, an in-app DOB-editable profile field for an existing user, or a Kids Category submission, **re-open this doc** — items 6–12 become binding under those conditions.

---

## Sources

- [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) — Apple
- [Age Ratings Values and Definitions (App Store Connect Help)](https://developer.apple.com/help/app-store-connect/reference/app-information/age-ratings-values-and-definitions/) — Apple
- [Updated Age Ratings in App Store Connect (July 2025)](https://developer.apple.com/news/?id=ks775ehf) — Apple Developer News
- [Apple Overhauls App Store Age Ratings](https://www.macrumors.com/2025/07/25/apple-overhauls-app-store-age-ratings/) — MacRumors, July 2025
- [Apple Pulled Cal AI for Deceptive Billing Design](https://www.macrumors.com/2026/04/21/apple-cal-ai-app-store-removal/) — MacRumors, April 2026
- [Complying with COPPA: FAQ](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions) — FTC
- [FTC COPPA Age-Verification Policy Statement](https://www.ftc.gov/news-events/news/press-releases/2026/02/ftc-issues-coppa-policy-statement-incentivize-use-age-verification-technologies-protect-children) — FTC, February 2026
- [Building Apps for Kids — Parental Gates](https://developer.apple.com/app-store/kids-apps/) — Apple Developer
- [Family Privacy Disclosure for Children](https://www.apple.com/legal/privacy/en-ww/parent-disclosure/) — Apple Legal
- [Approve what kids buy with Ask to Buy (105055)](https://support.apple.com/en-us/105055) — Apple Support
