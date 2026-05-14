# WrapUp Pro Depth — Finding + Decision Required

> **Skill:** none (pro-value-audit follow-through; resolves [pro-value-backlog-2026-05-13-standard.md § P9](pro-value-backlog-2026-05-13-standard.md)).
> **Inputs:** [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift) ↔ [MONETIZATION.md § Pro Annual](MONETIZATION.md) ↔ [Shared/ProPerks.swift](../../../products/life-clock-ios/Sources/Shared/ProPerks.swift).
> **Author:** Claude (single-pass walk).
> **Status:** **Finding logged; operator decision required.** No source edit made.

## Finding

`WrapUpSheet.swift` (audited at commit `79a10fe`) renders ONE composition for both Free and Pro users — heading + `ClockHandView` animation + signed-minute readout + tone-aware body line + dismiss CTA. The only Pro-vs-Free difference is the **absence** of the `proSignalRow` upsell for Pro users (`showsProSignal` gates on `!subscriptions.isPro`).

That means Pro users get **the same wrap-up content** as Free, just without the upsell affordance — there is no Pro-only "richer" content inside the wrap-up sheet itself.

### The mismatch

`MONETIZATION.md § Pro Annual` "Unlocks (v1, shipped)" includes:

> **Weekly drivers + next-best lever** — the deeper weekly breakdown in History and **richer weekly wrap-ups** (per Pro-value backlog)

`Shared/ProPerks.swift` (single source of truth for the PaywallSheet header + Profile Pro Perks recap, both shipped this week) renders the same claim verbatim as a paywall bullet:

> **Weekly drivers + next-best lever** — the deeper breakdown in History and richer weekly wrap-ups

The "deeper breakdown in History" half **is** delivered — `HistoryView` Pro state shows weekly drivers cards + the next-best lever card. The "richer weekly wrap-ups" half **is not** delivered. The Pro user's `WrapUpSheet` is structurally identical to the Free user's. The claim does not match the delivery.

This is a `value-claim-unjustified` finding per [pro-value-rule.md § Value-claim accuracy](pro-value-rule.md) — and a borderline `submission-blocker` because [APP_STORE_ASO.md § App Review posture](APP_STORE_ASO.md) reads "Marketing must match the UI." A reviewer comparing the PaywallSheet header claim against the actual Pro wrap-up could flag the mismatch.

## Options

### Option A — retract the claim (recommended)

Edit MONETIZATION.md and `Shared/ProPerks.swift` to drop "and richer weekly wrap-ups" from the bullet. The bullet becomes:

> **Weekly drivers + next-best lever** — the deeper weekly breakdown in History

Two-line change. Aligns marketing with delivery. Future Pro-feature scoping (Option B implementation as v1.1+ work) is unblocked — when the feature ships, the operator re-adds "and richer weekly wrap-ups" alongside the implementation.

**Pros:** small change, restores claim↔delivery alignment, removes the App Review submission-blocker risk, keeps the wrap-up scope tight for v1.
**Cons:** loses a Pro value-prop in pre-purchase copy. The Pro user's wrap-up sheet still looks the same as Free — but at least the marketing doesn't promise otherwise.

### Option B — implement Pro-only weekly wrap-up depth

Extend `WrapUpSheet` (weekly variant) to render an additional section for Pro users: e.g., "Top driver this week: sleep" + "Next-best lever: 30 min more exercise tomorrow." Mirror the `proSignalRow` gate but inverted — `if subscriptions.isPro && case .weekly = wrapUp`.

**Pros:** delivers on the existing marketing claim, gives Pro users a felt depth difference in the weekly ceremony moment.
**Cons:** larger change — needs new copy (3 tone variants × positive/negative/zero × heading/body framings), needs to source "top driver" and "next-best lever" data (likely from existing weekly aggregation in `WrapUpCoordinator` or `LifeClockStore`), needs new `wrap-up-spec.md` section, needs new fixture knobs to drive in audits. Realistically a v1.1+ feature, not a 24h fix.

## Recommendation

**Option A (retract).** Strong recommendation but escalating because MONETIZATION.md is operator-owned per the skill rubric and modifying a marketing claim — even to align it with reality — is product-grade.

Specifically I recommend Option A because:

1. The asymmetry was created by the WrapUp Pro affordance ship in commit `7ebee94` — the affordance added "See the full week →" for Free users, which made Pro users notice they DON'T get a "full week" thing inside the wrap-up itself. The marketing claim predates the affordance and was never fully shipped.
2. Option B is real feature work that should be scoped, designed (`wrap-up-spec.md` extension), tested (fixture knobs, golden captures, UITests), and roadmapped — not crammed in to back-fill a claim.
3. App Store submission posture explicitly says "marketing must match UI"; the safer move pre-submission is align-the-claim-down, not race-to-build-the-feature.
4. After Option A, the operator has a clean conscience to scope Option B as a v1.1 ratchet if Pro-user retention data suggests the wrap-up needs more Pro-side juice.

If the operator agrees, the edit is:

- **MONETIZATION.md** — drop "and richer weekly wrap-ups (per Pro-value backlog)" from the Pro Annual "Unlocks (v1, shipped)" bullet "Weekly drivers + next-best lever".
- **Shared/ProPerks.swift** — change `Perk(title: "Weekly drivers + next-best lever", detail: "the deeper breakdown in History and richer weekly wrap-ups")` to `Perk(title: "Weekly drivers + next-best lever", detail: "the deeper breakdown in History")`.

Both edits flow through automatically — PaywallSheet header bullets + Profile Pro Perks recap both read from `ProPerks.perks` after the Sprint A2 + 2026-05-13 P8 refactor.

## Why I did not make this call myself

The user asked me to make autonomous judgment calls unless I genuinely believe operator input is required. I believe operator input IS required here because:

- MONETIZATION.md is operator-owned by skill convention (yesterday's pro-value backlog § P9 explicitly tagged this decision operator-grade).
- The same artifact (PaywallSheet header) was the subject of yesterday's submission-blocker P2 closure, which the operator carefully shipped verbatim from MONETIZATION.md — touching it again 24h later, even to drop two words, deserves explicit sign-off.
- Option B is a real alternative the operator may prefer. I have a strong opinion, but A vs B is a scope-and-roadmap decision, not a code-style decision.

## Next steps after operator decision

- **If Option A:** I'll make the two-line edit (MONETIZATION.md + ProPerks.swift) in a fresh diff. UITest changes are likely needed against `paywall.header` accessibility tree (bullet text changes). Re-run [polish-2026-05-13-aso-drift-recheck.md](polish-2026-05-13-aso-drift-recheck.md) to confirm the claim↔delivery walk is clean.
- **If Option B:** scope the feature in `wrap-up-spec.md` Pro signal section; add fixture knobs; design the visual treatment; ship as separate Sprint E or v1.1 work.

## Cross-references

- [pro-value-backlog-2026-05-13-standard.md § P9](pro-value-backlog-2026-05-13-standard.md) — the audit prompt
- [pro-value-rule.md § Value-claim accuracy](pro-value-rule.md) — the rubric
- [MONETIZATION.md § Pro Annual](MONETIZATION.md) — the claim source
- [Shared/ProPerks.swift](../../../products/life-clock-ios/Sources/Shared/ProPerks.swift) — the in-app single source of truth
- [PaywallSheet.swift § header](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift) — bullet rendering site
- [ProfileView.swift § Pro Perks recap](../../../products/life-clock-ios/Sources/Features/Profile/ProfileView.swift) — same bullet rendering, Pro-only state
- [WrapUpSheet.swift](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift) — the audited file
- [APP_STORE_ASO.md § App Review posture](APP_STORE_ASO.md) — the binding constraint
