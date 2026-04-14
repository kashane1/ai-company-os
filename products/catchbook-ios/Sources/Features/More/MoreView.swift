import SwiftData
import SwiftUI

struct MoreView: View {
    @Environment(\.modelContext) private var modelContext

    @State private var backupDocument = LogbookBackupDocument(package: .placeholder())
    @State private var showingBackupExporter = false
    @State private var exportPreparationError: String?

    var body: some View {
        NavigationStack {
            List {
                Section("My Inventory") {
                    Label("Saved Lures & Baits", systemImage: "lasso.and.sparkles")
                        .foregroundStyle(.secondary)
                    Label("Species", systemImage: "fish")
                        .foregroundStyle(.secondary)
                }

                Section("Data & Export") {
                    Button {
                        prepareBackupExport()
                    } label: {
                        Label("Export Logbook Backup", systemImage: "square.and.arrow.up")
                    }

                    Label {
                        HStack {
                            Text("CSV Export")
                            Spacer()
                            Text("Coming soon")
                                .font(.caption)
                                .foregroundStyle(.tertiary)
                        }
                    } icon: {
                        Image(systemName: "tablecells")
                    }
                    .foregroundStyle(.secondary)
                }

                Section("Stats & Insights") {
                    Label("Personal Bests", systemImage: "trophy")
                        .foregroundStyle(.secondary)
                    Label {
                        HStack {
                            Text("Fishing Stats")
                            Spacer()
                            Text("Coming soon")
                                .font(.caption)
                                .foregroundStyle(.tertiary)
                        }
                    } icon: {
                        Image(systemName: "chart.bar")
                    }
                    .foregroundStyle(.secondary)
                }

                Section("About") {
                    LabeledContent("Version") {
                        Text(appVersion)
                            .foregroundStyle(.secondary)
                    }
                    Label("Privacy", systemImage: "lock.shield")
                    Label("Send Feedback", systemImage: "envelope")
                }
            }
            .navigationTitle("More")
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

    private var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "—"
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
}
