import Foundation

/// Path value type for the onboarding `NavigationStack`. Each case maps
/// to a sub-view in the coordinator. The order in this enum is the
/// canonical screen sequence — the coordinator's `next(after:)` helper
/// uses it for forward navigation.
///
/// Telemetry events use the rawValue, so renaming a case is a breaking
/// change for downstream funnel analytics. Add new screens at the end
/// of their phase block when possible.
enum OnboardingScreen: String, Hashable, CaseIterable, Identifiable {
    // Lead-in (Phase 3.5)
    case welcome
    case meetYourClock
    case reactiveSlider

    // Personalize intro
    case goalPick

    // Baseline data collection
    case baselineDOB
    case baselineSex
    case bodyComp
    case smoking
    case alcohol
    case strength
    case cardio
    case sleep
    case diet

    // Sensitive-data block (gated behind consent priming)
    case sensitiveConsent
    case familyMother
    case familyFather
    case stress
    case social

    // Tone + meta
    case tone
    case priorAttempts

    // Reveal escalator
    case analyzing
    case archetypeReveal
    case lifeGridRemaining
    case bigNumberPenalty
    case engineRevealAndDial
    case recoveryPreview

    // Pre-paywall
    case healthKitAuth

    // Paywall
    case paywallPrimary

    var id: String { rawValue }
}

extension OnboardingScreen {
    /// Where the flow goes after `bodyComp`. Adults see the smoking +
    /// alcohol pair; minors (under 18 by reported DOB) skip both and
    /// land directly on `strength`. Mirrors the post-onboarding QuickLog
    /// gate at `LifeClockStore.isAdultUser` and the ASC age-rating
    /// questionnaire claim that under-18 users don't see those prompts.
    /// `birthDate == nil` falls through as "skip" — the picker should
    /// always populate it, but the safer default for an unknown age is
    /// to suppress the alcohol/tobacco questions.
    static func afterBodyComp(
        birthDate: Date?,
        asOf: Date,
        calendar: Calendar
    ) -> OnboardingScreen {
        guard let birthDate,
              AgeGate.isAdult(birthDate: birthDate, asOf: asOf, calendar: calendar)
        else { return .strength }
        return .smoking
    }

    /// Screens removed in later flow revisions, kept here so funnel
    /// dashboards can join historical events to the current step that
    /// absorbed them. Telemetry sinks should consult this map when
    /// reconciling old `screenAppeared` rows with the live taxonomy.
    static let deprecatedScreens: [String: OnboardingScreen] = [
        // 2026-05-03 — `lifeGridFull` merged into `lifeGridRemaining`
        // (single screen showing remaining-weeks dot grid).
        "lifeGridFull": .lifeGridRemaining,
        // 2026-05-05 — v2 routing dropped these abstract lead-in
        // beats. Historical funnel rows roll up to the screen that
        // absorbed their place in the flow.
        "appPreviews": .welcome,
        "visibilityFraming": .goalPick,
        "personalizeIntro": .goalPick,
        // 2026-05-07 — `entryView` (the post-paywall "Setting up your
        // clock…" placeholder) was dropped. The parent `RootView`
        // gate flip happens on profile-write, so the screen was a
        // one-frame safety-net that didn't earn its place.
        // Historical telemetry rolls into `paywallPrimary`.
        "entryView": .paywallPrimary,
    ]
}
