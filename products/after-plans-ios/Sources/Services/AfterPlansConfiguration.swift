import Foundation

// MARK: - Backend selection
//
// The store is constructed against an `AfterPlansBackend`. The configuration
// below decides which backend to instantiate. Default is `.inMemory` so the
// app and tests work offline.
//
// To run against a real Supabase project, set the build-time environment
// variables and switch the default to `.supabase`.

enum AfterPlansBackendKind {
    case inMemory
    case supabase(url: URL, anonKey: String)
}

enum AfterPlansConfiguration {
    /// Reads the backend selection from Info.plist or environment, falling
    /// back to `.inMemory`. Override at build time by setting:
    ///   AFTERPLANS_BACKEND       = "supabase" | "inMemory"
    ///   AFTERPLANS_SUPABASE_URL  = "https://<project>.supabase.co"
    ///   AFTERPLANS_SUPABASE_KEY  = "<anon key>"
    static var defaultBackend: AfterPlansBackendKind {
        let env = ProcessInfo.processInfo.environment
        guard env["AFTERPLANS_BACKEND"] == "supabase",
              let urlString = env["AFTERPLANS_SUPABASE_URL"],
              let url = URL(string: urlString),
              let key = env["AFTERPLANS_SUPABASE_KEY"], !key.isEmpty
        else {
            return .inMemory
        }
        return .supabase(url: url, anonKey: key)
    }

    static func makeBackend(_ kind: AfterPlansBackendKind = defaultBackend) -> AfterPlansBackend {
        switch kind {
        case .inMemory:
            return InMemoryBackendFactory.make()
        case let .supabase(url, anonKey):
            if let supabase = SupabaseBackendFactory.make(url: url, anonKey: anonKey) {
                return supabase
            }
            // Fall back when the supabase-swift package is not yet linked into
            // the project. Keeps the app runnable while infra is being wired.
            return InMemoryBackendFactory.make()
        }
    }
}
