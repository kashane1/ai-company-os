import SwiftData
import SwiftUI

struct HomeView: View {
    @Environment(\.modelContext) private var modelContext
    @Binding var selectedTab: AppTab

    @Query(sort: \Trip.startAt, order: .reverse) private var trips: [Trip]
    @Query(sort: \CatchRecord.caughtAt, order: .reverse) private var catches: [CatchRecord]
    @Query(sort: \PersonalBest.updatedAt, order: .reverse) private var personalBests: [PersonalBest]

    @State private var backupDocument = LogbookBackupDocument(package: .placeholder())
    @State private var showingBackupExporter = false
    @State private var exportPreparationError: String?

    private var activeTrip: Trip? {
        HomeDashboardLogic.activeTrip(from: trips)
    }

    private var latestCompletedTrip: Trip? {
        HomeDashboardLogic.latestCompletedTrip(from: trips)
    }

    private var latestCompletedSpotTrip: Trip? {
        HomeDashboardLogic.latestCompletedSpotTrip(from: trips)
    }

    private var latestSpotSummary: SpotRecallSummary? {
        guard let latestSpot = latestCompletedTrip?.spot else { return nil }
        return SpotRecallSummary.build(for: latestSpot, trips: trips, catches: catches)
    }

    private var latestCompletedTripCatches: [CatchRecord] {
        guard let latestCompletedTrip else { return [] }
        return catches.filter { $0.trip?.id == latestCompletedTrip.id }
    }

    private var lastTripSummary: HomeLastTripSummary? {
        guard let latestCompletedTrip else { return nil }
        return HomeDashboardLogic.lastTripSummary(
            trip: latestCompletedTrip,
            catches: latestCompletedTripCatches
        )
    }

    private var latestCompletedSpotTripCatches: [CatchRecord] {
        guard let latestCompletedSpotTrip else { return [] }
        return catches.filter { $0.trip?.id == latestCompletedSpotTrip.id }
    }

    private var suggestedMemoryCard: HomeMemoryCard? {
        HomeDashboardLogic.suggestedMemoryCard(
            latestCompletedTrip: latestCompletedTrip,
            summary: latestSpotSummary,
            totalCompletedTrips: totalTrips
        )
    }

    private var lastTimeHereCard: HomeReplayCard? {
        HomeDashboardLogic.lastTimeHereCard(
            trip: latestCompletedSpotTrip,
            catches: latestCompletedSpotTripCatches
        )
    }

    private var totalCatches: Int { HomeDashboardLogic.totalCatchCount(from: catches) }
    private var totalTrips: Int { HomeDashboardLogic.completedTripCount(from: trips) }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.xl) {
                    // Active Trip or Start CTA
                    if let activeTrip {
                        ActiveTripHero(
                            activeTrip: activeTrip,
                            catchCount: HomeDashboardLogic.catchCount(for: activeTrip.id, catches: catches)
                        ) {
                            selectedTab = .log
                        }
                        .padding(.horizontal)
                    } else {
                        StartTripCTA {
                            selectedTab = .log
                        }
                        .padding(.horizontal)
                    }

                    // Quick Stats
                    if totalTrips > 0 {
                        HStack(spacing: Spacing.md) {
                            QuickStatCard(value: "\(totalTrips)", label: "Trips", icon: "water.waves")
                            QuickStatCard(value: "\(totalCatches)", label: "Catches", icon: "fish")
                            QuickStatCard(
                                value: "\(personalBests.count)",
                                label: HomeDashboardLogic.personalBestLabel(count: personalBests.count),
                                icon: "trophy"
                            )
                        }
                        .padding(.horizontal)
                    }

                    // Last Trip
                    if let latestCompletedTrip {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            HomeSectionHeader(title: "Last Trip")
                                .padding(.horizontal)

                            NavigationLink {
                                TripDetailView(trip: latestCompletedTrip)
                            } label: {
                                LastTripCard(
                                    trip: latestCompletedTrip,
                                    catchCount: HomeDashboardLogic.catchCount(for: latestCompletedTrip.id, catches: catches),
                                    summary: lastTripSummary
                                )
                            }
                            .buttonStyle(.plain)
                            .padding(.horizontal)
                        }
                    }

                    if let suggestedMemoryCard {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            HomeSectionHeader(title: "Suggested Memory")
                                .padding(.horizontal)

                            SuggestedMemoryCard(card: suggestedMemoryCard)
                            .padding(.horizontal)
                        }
                    }

                    if let latestCompletedSpotTrip, let spot = latestCompletedSpotTrip.spot, let lastTimeHereCard {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            HomeSectionHeader(title: "Last Time Here")
                                .padding(.horizontal)

                            NavigationLink {
                                SpotDetailView(spot: spot)
                            } label: {
                                LastTimeHereCard(card: lastTimeHereCard)
                            }
                            .buttonStyle(.plain)
                            .padding(.horizontal)
                        }
                    }

                    // Private Recall
                    if
                        let latestSpotSummary,
                        HomeDashboardLogic.shouldShowRecall(
                            latestCompletedTrip: latestCompletedTrip,
                            summary: latestSpotSummary
                        ),
                        let spot = latestCompletedTrip?.spot
                    {
                        VStack(alignment: .leading, spacing: Spacing.sm) {
                            HomeSectionHeader(title: "Recall for \(spot.title)")
                                .padding(.horizontal)

                            VStack(spacing: Spacing.sm) {
                                ForEach(latestSpotSummary.cards.prefix(3), id: \.id) { card in
                                    DeterministicInsightCardView(card: card)
                                }
                            }
                            .padding(.horizontal)
                        }
                    }

                    VStack(alignment: .leading, spacing: Spacing.sm) {
                        HomeSectionHeader(title: "Personal Bests")
                            .padding(.horizontal)

                        if personalBests.isEmpty {
                            EmptyPersonalBestsCard()
                                .padding(.horizontal)
                        } else {
                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: Spacing.md) {
                                    ForEach(personalBests.prefix(6), id: \.id) { record in
                                        let linkedTrip = sourceTrip(for: record)
                                        if let linkedTrip {
                                            NavigationLink {
                                                TripDetailView(trip: linkedTrip)
                                            } label: {
                                                PersonalBestCard(record: record)
                                            }
                                            .buttonStyle(.plain)
                                        } else {
                                            PersonalBestCard(record: record)
                                        }
                                    }
                                }
                                .padding(.horizontal)
                            }
                        }
                    }
                }
                .padding(.vertical, Spacing.lg)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Home")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    let action = HomeToolbarAction.exportLogbookBackup
                    Button(action.label) {
                        prepareBackupExport()
                    }
                    .accessibilityIdentifier(action.accessibilityIdentifier)
                }
            }
        }
        .fileExporter(
            isPresented: $showingBackupExporter,
            document: backupDocument,
            contentType: .fishingLogbookBackup,
            defaultFilename: LogbookBackupExporter.defaultFilename
        ) { _ in }
        .alert("Backup export unavailable", isPresented: exportPreparationAlertIsPresented) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(exportPreparationError ?? "We couldn't prepare your backup right now.")
        }
    }

    private var exportPreparationAlertIsPresented: Binding<Bool> {
        Binding(
            get: { exportPreparationError != nil },
            set: { isPresented in
                if !isPresented {
                    exportPreparationError = nil
                }
            }
        )
    }

    private func prepareBackupExport() {
        do {
            backupDocument = try LogbookBackupExporter.makeDocument(context: modelContext)
            showingBackupExporter = true
        } catch {
            exportPreparationError = "We couldn't prepare your backup right now."
        }
    }

    private func sourceTrip(for record: PersonalBest) -> Trip? {
        let sourceCatchID = record.heaviestCatchID ?? record.longestCatchID
        guard let sourceCatchID else { return nil }
        return catches.first(where: { $0.id == sourceCatchID })?.trip
    }
}

// MARK: - Start Trip CTA

private struct StartTripCTA: View {
    let action: () -> Void

    var body: some View {
        VStack(spacing: Spacing.lg) {
            Image(systemName: "water.waves")
                .font(.system(size: 36))
                .foregroundStyle(Color.appAccent.opacity(0.55))
                .padding(.top, Spacing.sm)

            Text("Ready when you are")
                .font(.title3.weight(.semibold))

            Text("Start a trip to begin logging catches. Your data stays private on this device.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, Spacing.lg)

            Button(action: action) {
                Label("Start a Trip", systemImage: "plus.circle.fill")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, Spacing.md)
            }
            .buttonStyle(.borderedProminent)
            .tint(.appAccent)
        }
        .padding(Spacing.xxl)
        .background(.background, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

// MARK: - Active Trip Hero

private struct ActiveTripHero: View {
    let activeTrip: Trip
    let catchCount: Int
    let resume: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            HStack {
                VStack(alignment: .leading, spacing: Spacing.xs) {
                    HStack(spacing: Spacing.sm) {
                        AppBadge(text: "Live")
                        TimelineView(.periodic(from: activeTrip.startAt, by: 60)) { context in
                            Text(HomeDashboardLogic.elapsedText(startAt: activeTrip.startAt, now: context.date))
                                .font(.caption.monospacedDigit())
                                .foregroundStyle(.secondary)
                        }
                    }
                    Text(activeTrip.title)
                        .font(.headline)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: Spacing.xxs) {
                    Text("\(catchCount)")
                        .font(.title2.weight(.bold).monospacedDigit())
                        .foregroundStyle(.appAccent)
                    Text(catchCount == 1 ? "catch" : "catches")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            if let snapshot = activeTrip.conditionSnapshot {
                Text(snapshot.displaySummary)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let spot = activeTrip.spot?.title {
                Label(spot, systemImage: "mappin")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Button(action: resume) {
                Label("Resume Logging", systemImage: "arrow.right.circle.fill")
                    .font(.subheadline.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, Spacing.sm)
            }
            .buttonStyle(.borderedProminent)
            .tint(.appAccent)
        }
        .appCard(prominent: true)
    }
}

// MARK: - Quick Stat Card

private struct QuickStatCard: View {
    let value: String
    let label: String
    let icon: String

    var body: some View {
        VStack(spacing: Spacing.xs) {
            Image(systemName: icon)
                .font(.footnote)
                .foregroundStyle(.appAccent)
            Text(value)
                .font(.title3.weight(.bold).monospacedDigit())
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, Spacing.md)
        .background(.background, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

// MARK: - Last Trip Card

private struct LastTripCard: View {
    let trip: Trip
    let catchCount: Int
    let summary: HomeLastTripSummary?

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack {
                Text(trip.title)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }

            HStack(spacing: Spacing.lg) {
                Label(AppFormatters.tripDate.string(from: trip.startAt), systemImage: "calendar")
                Label(
                    "\(catchCount) \(catchCount == 1 ? "catch" : "catches")",
                    systemImage: "fish"
                )
            }
            .font(.footnote)
            .foregroundStyle(.secondary)

            if let durationText = summary?.durationText {
                Text(durationText)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }

            if let topSpeciesText = summary?.topSpeciesText {
                AppBadge(text: "Top \(topSpeciesText)")
            }

            if trip.outcomeRawValue == TripOutcome.skunked.rawValue {
                AppBadge(text: "Skunked", color: .secondary)
            }
        }
        .padding(Spacing.lg)
        .background(.background, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

private struct SuggestedMemoryCard: View {
    let card: HomeMemoryCard

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            AppBadge(text: "Private Memory")
            Text(card.title)
                .font(.headline)
            Text(card.body)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text(card.footer)
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
        .appCard(prominent: true)
    }
}

private struct LastTimeHereCard: View {
    let card: HomeReplayCard

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack {
                AppBadge(text: "Saved Privately")
                Spacer()
                Image(systemName: "arrow.up.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }

            Text(card.title)
                .font(.headline)

            Text(card.body)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Text(card.footer)
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
        .appCard(prominent: true)
    }
}

private struct EmptyPersonalBestsCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Text("Your best catches will show up here.")
                .font(.subheadline.weight(.semibold))
            Text("Once you log length or weight, the app keeps those records private and easy to find.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(Spacing.lg)
        .background(.background, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

// MARK: - Personal Best Row

private struct PersonalBestCard: View {
    let record: PersonalBest
    @ScaledMetric(relativeTo: .headline) private var minCardWidth: CGFloat = 220

    var body: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack {
                Image(systemName: "trophy.fill")
                    .font(.footnote)
                    .foregroundStyle(.appWarning)
                    .frame(width: 28, height: 28)
                    .background(Color.appWarning.opacity(0.12), in: Circle())
                Spacer()
                if record.heaviestCatchID != nil || record.longestCatchID != nil {
                    Image(systemName: "arrow.up.right")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.tertiary)
                }
            }

            Text(record.species)
                .font(.headline)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)

            Text(summaryText)
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            if let heaviest = record.heaviestWeightKg {
                StatCapsule(value: "\(heaviest.formatted()) kg", label: "Heaviest", icon: "scalemass")
            }

            if let longest = record.longestLengthCm {
                StatCapsule(value: "\(longest.formatted()) cm", label: "Longest", icon: "ruler")
            }
        }
        .frame(minWidth: minCardWidth, maxWidth: 320, alignment: .leading)
        .padding(Spacing.lg)
        .background(.background, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private var summaryText: String {
        HomeDashboardLogic.personalBestSummaryText(
            longestLengthCm: record.longestLengthCm,
            heaviestWeightKg: record.heaviestWeightKg
        )
    }
}

// MARK: - Section Header

private struct HomeSectionHeader: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.footnote.weight(.semibold))
            .foregroundStyle(.secondary)
            .textCase(.uppercase)
    }
}
