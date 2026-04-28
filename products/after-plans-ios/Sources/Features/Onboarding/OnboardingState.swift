import Foundation

// MARK: - Onboarding state machine
// Tracks position in the multi-step onboarding flow with persistence so
// an abandoned onboarding (background → terminate → relaunch) can pick
// up where it left off. Persistence lives in UserDefaults under
// `OnboardingState.persistenceKey`.

enum OnboardingStep: String, CaseIterable, Equatable, Codable {
    case intro
    case name
    case privacy
    case activityVenue
    case inviteCode
    case complete

    var next: OnboardingStep? {
        switch self {
        case .intro: return .name
        case .name: return .privacy
        case .privacy: return .activityVenue
        case .activityVenue: return .inviteCode
        case .inviteCode: return .complete
        case .complete: return nil
        }
    }

    var previous: OnboardingStep? {
        switch self {
        case .intro: return nil
        case .name: return .intro
        case .privacy: return .name
        case .activityVenue: return .privacy
        case .inviteCode: return .activityVenue
        case .complete: return .inviteCode
        }
    }

    var isTerminal: Bool { self == .complete }
}

struct OnboardingDraft: Equatable, Codable {
    var firstName: String = ""
    var privacyMode: PrivacyMode = .open
    var declaredActivityIDs: [UUID] = []
    var declaredVenueIDs: [UUID] = []
    var inviteCode: String = ""
    var inviteCodeRedeemed: Bool = false

    var hasMinimumName: Bool { firstName.trimmingCharacters(in: .whitespaces).count >= 1 }
}

@MainActor
final class OnboardingState: ObservableObject {
    static let persistenceKey = "afterplans.onboarding.state.v1"

    @Published var step: OnboardingStep
    @Published var draft: OnboardingDraft

    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        if let data = defaults.data(forKey: OnboardingState.persistenceKey),
           let decoded = try? JSONDecoder().decode(Persisted.self, from: data) {
            self.step = decoded.step
            self.draft = decoded.draft
        } else {
            self.step = .intro
            self.draft = OnboardingDraft()
        }
    }

    func advance() {
        guard let next = step.next else { return }
        step = next
        persist()
    }

    func goBack() {
        guard let prev = step.previous else { return }
        step = prev
        persist()
    }

    func skipToEnd() {
        step = .complete
        persist()
    }

    func reset() {
        step = .intro
        draft = OnboardingDraft()
        defaults.removeObject(forKey: OnboardingState.persistenceKey)
    }

    func updateDraft(_ mutate: (inout OnboardingDraft) -> Void) {
        mutate(&draft)
        persist()
    }

    private func persist() {
        let snapshot = Persisted(step: step, draft: draft)
        if let data = try? JSONEncoder().encode(snapshot) {
            defaults.set(data, forKey: OnboardingState.persistenceKey)
        }
    }

    private struct Persisted: Codable {
        let step: OnboardingStep
        let draft: OnboardingDraft
    }
}
