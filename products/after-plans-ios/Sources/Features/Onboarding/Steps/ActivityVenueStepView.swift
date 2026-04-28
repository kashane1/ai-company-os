import SwiftUI

// MARK: - ActivityVenuePickerView (shared between Onboarding + CreatePlan)
//
// Multi-row entry: pick an activity from the taxonomy, then either
// search Apple's MKLocalSearch for a venue or provide freeform text.
// Adds the (activity, venue) pair to a list that the caller manages.

struct ActivityVenuePickerView: View {
    @Binding var declaredActivityIDs: [UUID]
    @Binding var declaredVenueIDs: [UUID]
    @State private var selectedActivity: Activity?
    @State private var venueQuery: String = ""
    @State private var freeformVenueName: String = ""

    private let activities = ActivityTaxonomy.children

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            Text("Activities you do regularly")
                .font(.headline)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: Spacing.sm) {
                    ForEach(activities) { activity in
                        Button {
                            toggle(activity)
                        } label: {
                            HStack(spacing: 6) {
                                Image(systemName: activity.iconSystemName)
                                Text(activity.title)
                                    .font(.subheadline)
                            }
                            .padding(.vertical, Spacing.xs)
                            .padding(.horizontal, Spacing.sm)
                            .background(
                                Capsule().fill(declaredActivityIDs.contains(activity.id)
                                               ? Color.appAccent.opacity(0.15)
                                               : Color.appBackground)
                            )
                            .overlay(Capsule().stroke(
                                declaredActivityIDs.contains(activity.id) ? Color.appAccent : Color.appBorder,
                                lineWidth: 1
                            ))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            Text("\(declaredActivityIDs.count) selected")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private func toggle(_ activity: Activity) {
        if let idx = declaredActivityIDs.firstIndex(of: activity.id) {
            declaredActivityIDs.remove(at: idx)
        } else {
            declaredActivityIDs.append(activity.id)
        }
    }
}

struct ActivityVenueStepView: View {
    @Binding var declaredActivityIDs: [UUID]
    @Binding var declaredVenueIDs: [UUID]
    var onContinue: () -> Void
    var onBack: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.xl) {
            Spacer(minLength: 0)
            VStack(alignment: .leading, spacing: Spacing.md) {
                AppBadge(text: "Step 3 of 4", tone: .appMomentum)
                Text("What do you do — and where?")
                    .font(.system(size: 30, weight: .bold, design: .rounded))
                Text("Pick the things you do regularly. We'll match you with people who do the same — but only after you've been around long enough to feel like a real human.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                ActivityVenuePickerView(
                    declaredActivityIDs: $declaredActivityIDs,
                    declaredVenueIDs: $declaredVenueIDs
                )
            }
            .appSurface(prominent: true)
            Spacer(minLength: 0)
            VStack(spacing: Spacing.sm) {
                Button("Continue") { onContinue() }
                    .buttonStyle(ActionPillButtonStyle(prominent: true))
                Button("Skip for now") { onContinue() }
                    .buttonStyle(ActionPillButtonStyle())
                Button("Back") { onBack() }
                    .buttonStyle(ActionPillButtonStyle())
            }
        }
        .padding(Spacing.xl)
    }
}
