import SwiftUI

struct ConfirmationRoomView: View {
    @EnvironmentObject private var store: AfterPlansStore
    let planID: UUID

    var body: some View {
        Group {
            if let plan = store.plan(with: planID) {
                ScrollView {
                    VStack(alignment: .leading, spacing: Spacing.xl) {
                        VStack(alignment: .leading, spacing: Spacing.md) {
                            AppBadge(text: plan.lifecycle.title, tone: .appMomentum)
                            Text("Confirmation room")
                                .font(.system(size: 28, weight: .bold, design: .rounded))
                            Text("This is where the shell shows convergence. Messaging and handoff tooling stay intentionally out of scope for now.")
                                .foregroundStyle(.secondary)
                        }
                        .appSurface(prominent: true)

                        VStack(alignment: .leading, spacing: Spacing.md) {
                            SectionHeader(title: "Locked details", subtitle: "Enough structure to move from soft interest to a real next plan.")
                            Text(plan.title)
                                .font(.headline)
                            InfoRow(icon: "mappin.and.ellipse", text: plan.venueLabel)
                            InfoRow(icon: "clock", text: plan.timeLabel)
                            InfoRow(icon: "person.3", text: "\(plan.joinedCount) joined · \(plan.interestedCount) interested")
                        }
                        .appSurface()

                        VStack(alignment: .leading, spacing: Spacing.md) {
                            SectionHeader(title: "What happens next", subtitle: "Later slices can add handoff, arrival, and richer coordination.")
                            Text("1. The group sees one place and timing.")
                            Text("2. People confirm if they are actually going.")
                            Text("3. Last-mile chatter can hand off to text later.")
                        }
                        .appSurface()

                        Button(plan.lifecycle == .confirmed ? "Already confirmed" : "Mark as confirmed") {
                            store.confirm(plan.id)
                        }
                        .buttonStyle(ActionPillButtonStyle(prominent: true))
                        .disabled(plan.lifecycle == .confirmed || plan.lifecycle == .active)
                    }
                    .padding(Spacing.lg)
                }
                .navigationTitle("Confirmation")
            } else {
                ContentUnavailableView("Plan unavailable", systemImage: "exclamationmark.triangle")
            }
        }
    }
}
