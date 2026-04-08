import SwiftUI

struct ProfileView: View {
    @EnvironmentObject private var store: AfterPlansStore

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Spacing.xl) {
                profileHeader
                trustSection
                partnersSection
                safetySection
            }
            .padding(Spacing.lg)
        }
        .background(Color.appBackground.ignoresSafeArea())
        .navigationTitle("Profile")
    }

    // MARK: - Profile header

    private var profileHeader: some View {
        HStack(spacing: Spacing.lg) {
            ZStack {
                Circle()
                    .fill(Color.appAccent.opacity(0.12))
                    .frame(width: 64, height: 64)
                Text(store.currentUser.firstName.prefix(1))
                    .font(.system(size: 26, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.appAccent)
            }

            VStack(alignment: .leading, spacing: Spacing.xs) {
                Text(store.currentUser.firstName)
                    .font(.title2.weight(.bold))
                Text(store.currentUser.descriptor)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                AppBadge(text: store.currentUser.trustHeadline, tone: .appSafe)
            }

            Spacer()
        }
        .appSurface(prominent: true)
    }

    // MARK: - Trust defaults

    private var trustSection: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Trust defaults")

            Label(store.currentUser.visibilityDefault.title, systemImage: "eye")
                .font(.subheadline)

            Text("Your default visibility controls who can see you in plans.")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .appSurface()
    }

    // MARK: - Partners

    private var partnersSection: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Recent plan partners")

            if store.recentPartners.isEmpty {
                Text("Past partners appear here as you join more plans.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(store.recentPartners, id: \.self) { partner in
                    HStack {
                        Text(partner)
                            .font(.subheadline)
                        Spacer()
                        AppBadge(text: "Known")
                    }
                }
            }
        }
        .appSurface()
    }

    // MARK: - Safety

    private var safetySection: some View {
        VStack(alignment: .leading, spacing: Spacing.md) {
            SectionHeader(title: "Safety")

            NavigationLink {
                SafetyCenterView(focusedPlanID: nil)
            } label: {
                HStack {
                    Label("Open safety center", systemImage: "shield.lefthalf.filled")
                        .font(.subheadline.weight(.medium))
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundStyle(.tertiary)
                        .font(.footnote)
                }
            }
            .buttonStyle(.plain)

            if store.blockedUserNames.isEmpty {
                Text("No blocked users.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(store.blockedUserNames, id: \.self) { name in
                    Label(name, systemImage: "hand.raised")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .appSurface()
    }
}
