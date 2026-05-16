# Polish Session — life-clock — 2026-05-16 — paywall-vision-reconciliation

## Mode

`vision-driven` — decision/reconciliation only. Consumes exactly one backlog
prompt: **PV-P6** from
[pro-value-backlog-2026-05-15-standard.md](pro-value-backlog-2026-05-15-standard.md)
§ 6 ("Vision Q6 + Q12 reconciliation — the revamp drifted ahead of two open
Pro-positioning questions").

**No source change. No `vision.md` edit (Decided constraints are
operator-only; this run does not touch `vision.md` at all).** The deliverable
is this memo: a Q6 decision row, a Q12 decision row, and the complete
enumerated `RevealCopy.paywall*` marketing-review artifact. Iteration cap 3;
no computer-use checkpoint required (decision session, no UI change).

## Context — what `511fd4a` (2026-05-14 onboarding revamp) shipped ahead of vision

The 2026-05-14 onboarding revamp rebuilt the onboarding-terminal paywall
(`PaywallPrimaryView`). In doing so it made two product decisions in *code*
that two formally-**Open** vision questions had reserved for the operator:

- **Q6 — first-paywall placement.** Vision Open Q6: *"After initial reveal,
  after first weekly report, or never auto-show (Profile-only)? Trade: revenue
  vs. trust."* The revamp hard-wired **after the reveal, before the main app,
  with an explicit labeled soft-skip CTA**.
- **Q12 — paywall voice.** Vision Open Q12: *"should the paywall speak in the
  user's tone … or always in a single neutral marketing voice? … Stretch-tier
  — and needs marketing-side review before shipping."* The revamp shipped a
  **fully tone-keyed paywall** (headline, body, soft-skip label, soft-skip
  caption all branch on `ToneMode`) — the exact decision Q12 says needs
  marketing review *before* shipping.

Neither is a code defect. The revamp is good. This is a **vision-ledger
drift**: implementation moved ahead of two open questions and one explicit
"needs review before shipping" rider. This skill cannot edit Decided
constraints; it surfaces the tension for operator reconciliation.

> **Source-state note (does not change PV-P6):** PV-P6's prompt described
> `PaywallPrimaryView` as not enumerating `ProPerks`. At the audited working
> tree the `proPerks` block has since landed
> ([`PaywallPrimaryView.swift:138,214–219`](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift)),
> i.e. PV-P1 appears closed. PV-P6 is independent of that — it is about
> placement (Q6) and voice (Q12), not perks enumeration. Recorded for the
> next audit's accuracy.

---

## 1. Q6 decision row — first-paywall placement

### Current behavior (source-cited; no onboarding walk run — source is unambiguous)

- `PaywallPrimaryView` is the **onboarding terminal**. It fires
  `telemetry.paywallShown(stage: .primary)` on appear
  ([`PaywallPrimaryView.swift:91`](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift)).
  `PaywallStage` has exactly one case: `.primary`
  ([`OnboardingTelemetry.swift:33–35`](../../../products/life-clock-ios/Sources/Services/OnboardingTelemetry.swift))
  — there is no "after weekly report" or deferred-placement stage in the
  telemetry contract. Placement is structurally "after reveal, before main
  app," single occurrence.
- The exit is an **explicit, labeled** soft-skip — `Button(action: softSkip)`
  rendering `RevealCopy.paywallSoftSkipLabel(tone:)` with a caption
  underneath, a11y id `paywall.softSkip`
  ([`PaywallPrimaryView.swift:172–184`](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift)).
  The silent top-right X still exists for early bails.
- `softSkip()` records a **distinct** telemetry signal —
  `PaywallDismissReason.softSkipped` (added 2026-05-14, "Distinct from
  `.closed` so the funnel can separate silent X-close bails from deliberate
  soft-skips")
  ([`OnboardingTelemetry.swift:37–45`](../../../products/life-clock-ios/Sources/Services/OnboardingTelemetry.swift),
  [`PaywallPrimaryView.swift:209–212`](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift)).
- The soft-skip caption is honest and non-dark-pattern: *"Daily clock + 7-day
  view. Pro adds full history, weekly drivers, and corrections."* — it states
  what the free tier keeps, not a guilt frame.

### Decision

| | Option A — **RATIFY (recommended)** | Option B — keep Open / Profile-only on the table |
|---|---|---|
| **What** | "After-reveal, before main app, with an explicit labeled soft-skip" becomes the v1 Decided answer to Q6. | Q6 stays Open; "never auto-show (Profile-only)" remains a live alternative; the shipped placement is accepted-risk-until-[date]. |
| **Revenue/trust trade** | Accepts the revenue/trust trade in the **trust-favorable** direction: the after-reveal slot is the highest-converting moment (MONETIZATION best-moment #1), and the *explicit, labeled, telemetry-distinct* soft-skip materially lowers the trust cost a silent forced paywall would carry — the user is shown the free path in plain words, not trapped. | Defers the trade; preserves the option to move to Profile-only (max-trust, lower-revenue) if real funnel data shows the after-reveal slot harms retention. |
| **Cost** | Locks v1; reversing later is a Vision-question. | Leaves a code-ahead-of-vision item open; the next audit must keep re-surfacing it. |

**Recommended: Option A (ratify).** One-line trade: *the after-reveal slot
captures the highest-intent moment for revenue, and the explicit labeled
soft-skip + distinct `softSkipped` telemetry buy back most of the trust cost
that a silent forced paywall would incur — so the revenue/trust trade is
taken deliberately, in the trust-favorable form.* Alternative (B) is only
preferable if the operator wants to hold Profile-only open pending real funnel
data.

---

## 2. Q12 decision row — paywall voice (tone-keyed copy is LIVE)

### Current behavior

Every user-facing paywall string on `PaywallPrimaryView` branches on
`ToneMode` (gentle / coach / firmDirect): headline (keyed additionally on
`HabitFailureMode`), body (keyed additionally on top `LifeClockLever`),
soft-skip label, soft-skip caption. All centralized in `RevealCopy`
([`RevealCopy.swift:298–407`](../../../products/life-clock-ios/Sources/Features/Onboarding/Copy/RevealCopy.swift)).
Q12 explicitly said this needs **marketing-side review before shipping**; it
shipped on 2026-05-14 without that review.

### Decision

| | Option (a) — ratify retroactively | Option (b) — flag specific strings for marketing revision |
|---|---|---|
| **What** | Marketing review is performed *retroactively* against the shipped strings (the inventory in § 3 is the artifact). If they pass, tone-keyed paywall copy is ratified into Decided; Q12 closes. | Specific strings are flagged for marketing rewrite before Q12 closes; the rest provisionally accepted. |
| **When right** | If the shipped strings already hold the adherence-neutral, non-shaming register the vision and the MacroFactor reference both demand. | If any string risks a shaming/blaming read that contradicts "Default is motivating, not punishing" + the Q1/Q9 drama-not-cruelty rulings. |

### My read on shaming-register risk (I read all the strings — see § 3)

I read every `RevealCopy.paywall*` return verbatim. **None reads as
shaming, accusatory, or punitive.** The register is consistently
forward-looking and capability-framed, not deficit-framed:

- Headlines name a *capability the product offers against the user's stated
  failure mode* ("Never lose the thread.", "Keep the clock visible when
  motivation isn't.", "Rhythm, not reset.", "See the pattern, not just the
  day.") — they describe what Pro does, not what the user failed at. They are
  consistent with the resolved Q9/Q10 "earn time / forward-pull" register and
  do not presuppose adherence (the Q1 2026-05-10 failure mode).
- The `firmDirect` variants are terse ("Clock visible. Motivation optional.",
  "Quick. Clear. Weekly.") but terse ≠ cruel; they make no claim about the
  user's current state and carry no mortality lexicon.
- Body strings lead with "This is your first read" / "First read" — a neutral
  observation, then a Pro capability. The lever-named variant inserts the
  user's own top lever ("around your \<lever\>") — personalization, not
  judgment.
- Soft-skip label/caption are honest and pressure-free.

**Recommended framing: (a) ratify-retroactively is defensible on a register
read, but the rider is marketing's call, not this skill's.** My register
verdict is "no shaming risk found"; whether to *formally* ratify vs. do one
clean marketing pass first is the operator's + marketing's decision. If the
operator wants zero residual risk, (b) with **zero strings flagged by this
review** (i.e. a fast confirmatory marketing pass against § 3) is the
lowest-regret path. The decision is batched in the Ask below.

---

## 3. Marketing-review artifact — every `RevealCopy.paywall*` string, verbatim

Source: [`RevealCopy.swift:298–407`](../../../products/life-clock-ios/Sources/Features/Onboarding/Copy/RevealCopy.swift).
`HabitFailureMode` has 6 cases (`forget`, `loseMotivation`, `overdoAndStop`,
`noProgressVisible`, `chaos`, plus the `unanswered` sentinel —
[`HabitFailureMode.swift:14–25`](../../../products/life-clock-ios/Sources/App/HabitFailureMode.swift)).
Headline is `failureMode × tone`. Counts below are reported two ways: **return
sites** (every branch the code can take) and **distinct strings** (some
branches return identical text).

### 3.1 Headlines — `paywallHeadline(tone:failureMode:)`

18 return sites (6 failure modes × 3 tones). 15 are user-reachable
(the 5 selectable modes × 3 tones — this is the "15" the backlog cites); the
`unanswered` sentinel adds 3 fallback sites. Distinct strings: 14 (collapses
noted).

**forget**
- gentle: `Stay easy to remember.`
- coach: `Never lose the thread.`
- firmDirect: `Never lose the thread.`  *(= coach)*

**loseMotivation**
- gentle: `Keep the clock close, even on flat days.`
- coach: `Keep the clock visible when motivation isn't.`
- firmDirect: `Clock visible. Motivation optional.`

**overdoAndStop**
- gentle: `A steadier rhythm — no reset weeks ahead.`
- coach: `A steady rhythm, not another reset.`
- firmDirect: `Rhythm, not reset.`

**noProgressVisible**
- gentle: `See the pattern, not just the day.`
- coach: `See the pattern, not just the day.`  *(= gentle)*
- firmDirect: `See the pattern. Not just the day.`

**chaos**
- gentle: `Quick check-ins. Weekly clarity.`
- coach: `Quick logging. Weekly clarity.`
- firmDirect: `Quick. Clear. Weekly.`

**unanswered** *(sentinel fallback — fires only if `habitFailureMode`
unstored/unknown)*
- gentle: `Keep your clock sharpening.`
- coach: `Keep your clock sharpening.`  *(= gentle)*
- firmDirect: `Keep the clock sharpening.`

### 3.2 Body — `paywallBody(tone:top:)`

Two branches: `top == .unanswered` (neutral fallback, 3 strings) and the
lever-named template (3 string templates with `\(name)` = the user's top
lever, lowercased). **6 string forms total.**

**top == .unanswered (neutral)**
- gentle: `This is your first read. Pro keeps watching the patterns that actually move your clock, with full history and weekly drivers.`
- coach: `First read. Pro keeps watching the patterns that move your clock — full history, weekly drivers, correction power.`
- firmDirect: `First read. Pro: full history, weekly drivers, correction power.`

**top == a named lever (`\(name)` = `top.displayName.lowercased()`)**
- gentle: `This is your first read. Pro keeps watching the patterns around your \(name) so you see what's actually moving your clock.`
- coach: `First read. Pro keeps watching the patterns around your \(name) — full history, weekly drivers, correction power.`
- firmDirect: `First read. Pro watches your \(name). Full history. Drivers. Corrections.`

### 3.3 Soft-skip label — `paywallSoftSkipLabel(tone:)`

3 return sites, 2 distinct strings.
- gentle: `Continue with the free clock`
- coach: `Continue with the free clock`  *(= gentle)*
- firmDirect: `Skip — free clock for now`

### 3.4 Soft-skip caption — `paywallSoftSkipCaption(tone:)`

3 return sites, 2 distinct strings.
- gentle: `Daily clock + 7-day view. Pro adds full history, weekly drivers, and corrections.`
- coach: `Daily clock + 7-day view. Pro adds full history, weekly drivers, and corrections.`  *(= gentle)*
- firmDirect: `Daily clock + 7-day view. Pro: full history, drivers, corrections.`

### Inventory counts (for the report-back)

| Group | Return sites | User-reachable sites | Distinct strings |
|---|---|---|---|
| Headline | 18 | 15 | 14 |
| Body | 6 | 6 | 6 (3 neutral + 3 lever-templated) |
| Soft-skip label | 3 | 3 | 2 |
| Soft-skip caption | 3 | 3 | 2 |

Out-of-scope but adjacent (NOT part of the Q12 paywall-voice review, listed
so marketing knows the boundary): `healthKitAuthTitle` /
`healthKitAuthBody` ([`RevealCopy.swift:368–385`](../../../products/life-clock-ios/Sources/Features/Onboarding/Copy/RevealCopy.swift))
are tone-keyed but are a *permission* screen, not the paywall. The
auto-renew fineprint on `PaywallPrimaryView` (*"Subscriptions renew
automatically until cancelled in Settings. Lifetime is a one-time
purchase."*, [`PaywallPrimaryView.swift:147`](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift))
is **not** tone-keyed and is intentionally static per Apple 3.1.2(c) — Q12
explicitly says "App Store fineprint stays as-is regardless."

---

## Asks

### Resolved this session

None — this is the reconciliation session that *raises* the batched Ask.

### Outstanding (cycle-end batch — BOTH questions, one prompt)

> **The revamp (`511fd4a`, 2026-05-14) made two product decisions in code
> that vision Q6 and Q12 reserved for you. Please resolve both. This skill
> cannot edit `vision.md` — you paste the resolution into Decided constraints
> manually.**
>
> **Ask 1 — Q6 first-paywall placement.** The onboarding paywall is now
> hard-wired *after the reveal, before the main app*, with an explicit
> labeled "Continue with the free clock" soft-skip (distinct `softSkipped`
> telemetry). Pick one:
> - **(A) Ratify (recommended).** Paste into Decided: *"First-paywall
>   placement is after the reveal, before the main app, with an explicit
>   labeled soft-skip CTA. The revenue/trust trade is accepted in the
>   trust-favorable form: the after-reveal slot is the highest-converting
>   moment, and the explicit labeled soft-skip + distinct softSkipped
>   telemetry materially lower the trust cost vs. a silent forced paywall.
>   Moving to Profile-only or removing the labeled soft-skip is a
>   Vision-question."*
> - **(B) Keep Open.** Q6 stays Open; Profile-only stays on the table; the
>   shipped placement is logged as accepted-risk-until-[your date].
>
> **Ask 2 — Q12 paywall voice (tone-keyed copy is LIVE, shipped without the
> marketing review Q12 required).** I read all `RevealCopy.paywall*` strings
> (full verbatim inventory in § 3 of the memo: 18 headline sites / 6 body
> forms / 3 soft-skip-label / 3 soft-skip-caption). My register read: **no
> shaming, accusatory, or punitive copy found** — strings are forward-looking
> and capability-framed, consistent with the resolved Q9/Q10 "earn time"
> register and the drama-not-cruelty rulings. Pick one:
> - **(a) Ratify retroactively.** The § 3 inventory *is* the marketing
>   review; paste into Decided: *"The paywall speaks in the user's tone
>   (gentle/coach/firmDirect), keyed off habitFailureMode + top lever. The
>   2026-05-16 reconciliation reviewed every RevealCopy.paywall* string and
>   found no shaming/punitive register. App Store fineprint stays neutral and
>   static. A non-tone-keyed paywall, or new tone-keyed strings without a
>   register check, is a Vision-question."*
> - **(b) Flag for revision.** Name the specific string(s) in § 3 you want
>   marketing to rewrite before Q12 closes; the rest are provisionally
>   accepted.
>
> **If you defer either:** the memo records Q6/Q12 as *"Open,
> code-ahead-of-vision, accepted risk until [date you set]"* so the next
> audit doesn't re-surface it blind. (As of this writing, both are recorded
> deferred-pending-your-answer with no date — set one or resolve.)

## Regressions caught

None — no code or screenshots touched this session.

## A11y identifiers added

None — no source change. (Existing relevant ids, for reference:
`onboarding.paywallPrimary`, `paywall.headline`, `paywall.body`,
`paywall.softSkip`, `paywall.purchase`, `paywall.restore`.)

## Vision updates

- Open Questions appended: **none** (skill did not modify `vision.md` this
  run, by explicit instruction).
- Decided constraints proposed (operator-only edit): the two Decided-entry
  drafts in the batched Ask above (Q6 ratify text; Q12 ratify text). The
  operator pastes them — the skill does not.

## Next pass

- After the operator answers: a follow-up session pastes the resolved Decided
  entries (operator-performed) and the next pro-value audit drops Q6/Q12 from
  the Open-Questions ledger. If deferred, the next audit must carry the
  accepted-risk-until date forward, not re-derive the tension blind.
- PV-P6 source-state note: PV-P1 (ProPerks enumeration on `PaywallPrimaryView`)
  appears landed in the audited tree; the next pro-value audit should update
  its coverage matrix accordingly rather than re-emitting PV-P1.
