import SwiftData
import SwiftUI

struct MoreView: View {
    @Environment(\.modelContext) private var modelContext

    @State private var backupDocument = LogbookBackupDocument(package: .placeholder())
    @State private var showingBackupExporter = false
    @State private var csvDocument = LogbookCSVDocument(csv: "")
    @State private var showingCSVExporter = false
    @State private var exportPreparationError: String?

    var body: some View {
        NavigationStack {
            List {
                Section("My Inventory") {
                    NavigationLink {
                        SavedLuresView()
                    } label: {
                        Label("Saved Lures & Baits", systemImage: "lasso.and.sparkles")
                    }
                    NavigationLink {
                        SpeciesListView()
                    } label: {
                        Label("Species", systemImage: "fish")
                    }
                }

                Section {
                    Button {
                        prepareBackupExport()
                    } label: {
                        Label("Export Catchbook Data", systemImage: "square.and.arrow.up")
                    }
                    Button {
                        prepareCSVExport()
                    } label: {
                        Label("Export Catches as CSV", systemImage: "tablecells")
                    }
                } header: {
                    Text("Data & Export")
                } footer: {
                    Text("Full backup saves every trip, catch, and photo in Catchbook's package format. CSV export flattens all catches with trip and condition context for spreadsheets.")
                }

                Section("Stats & Insights") {
                    NavigationLink {
                        FishingStatsView()
                    } label: {
                        Label("Fishing Stats", systemImage: "chart.bar")
                    }
                    NavigationLink {
                        PersonalBestsListView()
                    } label: {
                        Label("Personal Bests", systemImage: "trophy")
                    }
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
        .fileExporter(
            isPresented: $showingCSVExporter,
            document: csvDocument,
            contentType: .commaSeparatedText,
            defaultFilename: LogbookCSVExporter.defaultFilename
        ) { _ in }
        .alert("Export unavailable", isPresented: exportPreparationAlertIsPresented) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(exportPreparationError ?? "We couldn't prepare your export right now.")
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

    private func prepareCSVExport() {
        do {
            csvDocument = try LogbookCSVExporter.makeDocument(context: modelContext)
            showingCSVExporter = true
        } catch {
            exportPreparationError = "We couldn't prepare your CSV right now."
        }
    }
}
