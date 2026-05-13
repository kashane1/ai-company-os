import SwiftUI

/// Pro-only per-day detail view. Lists overridable HealthKit-derived
/// metrics (steps, sleep, exercise, active energy) with the live value, an
/// "Adjusted" chip when an override is in effect, and tap-to-edit access
/// to the `OverrideSheet`. Tap on the chip to reveal the original HK value
/// and a Revert button.
///
/// Free users never reach this view — the History list disables drilldown
/// on locked rows and presents the paywall instead.
struct DayDetailView: View {
    let dayStart: Date
    @Environment(LifeClockStore.self) private var store
    @State private var editingField: SnapshotOverrideMap.Field?
    @State private var revertError: String?

    private static let dateFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateStyle = .full
        f.timeStyle = .none
        return f
    }()

    private var snapshot: DailyHealthSnapshot? {
        store.snapshot(for: dayStart)
    }

    private var dateLabel: String {
        Self.dateFormatter.string(from: dayStart)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                if snapshot != nil {
                    ForEach(SnapshotOverrideMap.Field.allCases, id: \.self) { field in
                        metricRow(field)
                    }
                } else {
                    EmptyStateView(
                        title: "Nothing logged for this day yet",
                        body: "Apple Health hasn't synced data for this date and you didn't log any habits. Once either fires, you'll see the breakdown here.",
                        systemImage: "calendar"
                    )
                    .listRowBackground(Color.clear)
                }

                reflectionRow

                if let revertError {
                    Text(revertError)
                        .font(.caption)
                        .foregroundStyle(DesignTokens.Palette.negative)
                }
            }
            .padding(DesignTokens.Spacing.lg)
            .readableColumn()
        }
        .navigationTitle(dateLabel)
        .navigationBarTitleDisplayMode(.inline)
        .sheet(item: $editingField) { field in
            OverrideSheet(
                field: field,
                dayStart: dayStart,
                currentValue: snapshot?.effectiveValue(for: field),
                onDismiss: { editingField = nil }
            )
        }
    }

    /// Read-only readback of the reflection saved on this day, when one
    /// exists. Reads through `LifeClockStore.reflection(for:)` so the
    /// view stays consistent with the rest of the app's store-mediated
    /// data path (no view-direct `@Query`).
    @ViewBuilder
    private var reflectionRow: some View {
        if let reflection = store.reflection(for: dayStart) {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                Text(store.toneMode.reflectionHeading)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text(reflection.prompt)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                Text(reflection.response)
                    .font(.callout)
            }
            .padding(DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                DesignTokens.Palette.elevated,
                in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
            )
            .accessibilityIdentifier("dayDetail.reflection")
        }
    }

    @ViewBuilder
    private func metricRow(_ field: SnapshotOverrideMap.Field) -> some View {
        let snap = snapshot
        let effective = snap?.effectiveValue(for: field)
        let isOverridden = snap?.isOverridden(field) ?? false
        let original = snap?.originalHealthKitValue(for: field)

        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            HStack(alignment: .firstTextBaseline) {
                Text(field.displayName)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Spacer()
                if isOverridden {
                    adjustedChip
                }
            }
            HStack(alignment: .firstTextBaseline) {
                Text(format(value: effective, for: field))
                    .font(.system(size: 28, weight: .semibold, design: .rounded))
                Spacer()
                if isOverridden {
                    Button("Undo") { revert(field) }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                }
                Button("Edit") { editingField = field }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
            }
            if isOverridden, let original {
                Text("From Health: \(format(value: original, for: field))")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            DesignTokens.Palette.elevated,
            in: RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
        )
    }

    private var adjustedChip: some View {
        Label(store.toneMode.adjustedChipLabel, systemImage: "pencil.circle.fill")
            .font(.caption2)
            .foregroundStyle(.secondary)
            .padding(.horizontal, DesignTokens.Spacing.xs)
            .padding(.vertical, 2)
            .background(
                Capsule().fill(DesignTokens.Palette.elevated.opacity(0.6))
            )
    }

    private func revert(_ field: SnapshotOverrideMap.Field) {
        do {
            try store.revertOverride(field: field, on: dayStart)
            revertError = nil
        } catch {
            revertError = "Couldn't revert that change. Try again."
        }
    }

    private func format(value: Double?, for field: SnapshotOverrideMap.Field) -> String {
        guard let value else { return "—" }
        return field.spec.format(value)
    }
}

extension SnapshotOverrideMap.Field: Identifiable {
    var id: String { rawValue }

    /// Convenience alias for `spec.displayName` so view code stays
    /// readable. Spec is the single source of truth.
    var displayName: String { spec.displayName }
}
