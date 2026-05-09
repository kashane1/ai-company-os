import Foundation

/// In-memory store of pre-authored quests. Loaded once at app start from
/// JSON in the resource bundle; immutable thereafter.
///
/// Phase 2 of the quest-pool affinity engine
/// (docs/plans/2026-05-08-feat-quest-pool-affinity-engine-plan.md).
///
/// Backed by a `Dictionary<String, PoolQuest>` keyed by slug for O(1) tone
/// resolution per render. The JSON files at
/// `Resources/QuestPool/{activity,diet,sleep}.json` ship empty in this
/// phase; Phase 4 authors the 90-quest production pool. The fixture pool
/// (`Resources/QuestPool/fixture.json`) is test-only and is loaded by tests
/// against an explicit `Bundle` — it is never used as a release fallback.
///
/// Failure mode (per architecture + framework reviews on the deepened plan):
/// a malformed or missing pool JSON is a build defect, not a runtime
/// fallback condition. `loadFromBundle(_:)` throws; `Bundle.main`-driven
/// app startup converts the error to a `fatalError` so the next TestFlight
/// build catches the problem before App Store rollout.
struct QuestPool: Sendable {
let quests: [String: PoolQuest]

init(quests: [PoolQuest]) {
        var dict: [String: PoolQuest] = [:]
        for quest in quests {
            dict[quest.slug] = quest
        }
        self.quests = dict
    }

    /// All slugs in the pool, in deterministic sort order.
var slugs: [String] {
        quests.keys.sorted()
    }

    /// All quests for a given genre, in deterministic sort order by slug.
func quests(in genre: Genre) -> [PoolQuest] {
        quests.values
            .filter { $0.genre == genre }
            .sorted { $0.slug < $1.slug }
    }

    /// O(1) tone resolution: the rendered copy for a slug at the user's
    /// current tone. Returns nil if the slug is unknown to the pool.
    /// Tone presence is enforced at load time (custom Codable on
    /// `PoolQuest`), so a known slug always has all three tones.
func copy(for slug: String, tone: ToneMode) -> ToneCopy? {
        quests[slug]?.copy[tone]
    }

    /// True when the pool has no entries. Called by app startup to
    /// distinguish "empty production pool, expected during Phase 2/3" from
    /// "load failure, programmer error".
var isEmpty: Bool {
        quests.isEmpty
    }
}

// MARK: - Loading

extension QuestPool {
    /// Filenames (without extension) that the production pool loader reads.
    /// Tests can use `loadFromBundle(_:basenames:)` with `["fixture"]` to
    /// target the test-only fixture pool.
    static let productionBasenames: [String] = ["activity", "diet", "sleep"]

    enum LoadError: Error, CustomStringConvertible {
        case missingResource(String)
        case decodeFailed(String, underlying: Error)
        case duplicateSlug(String, in: String)

    var description: String {
            switch self {
            case .missingResource(let name):
                return "QuestPool: missing resource \(name).json in bundle"
            case .decodeFailed(let name, let underlying):
                return "QuestPool: failed to decode \(name).json: \(underlying)"
            case .duplicateSlug(let slug, let file):
                return "QuestPool: duplicate slug \"\(slug)\" found in \(file).json"
            }
        }
    }

    /// Load the production pool from a bundle. Throws on missing or
    /// malformed JSON, or on a duplicate slug across files. Caller
    /// (typically the app's launch code) decides whether to convert the
    /// throw into a fatalError or a graceful empty-pool startup.
    static func loadFromBundle(
        _ bundle: Bundle,
        basenames: [String] = QuestPool.productionBasenames
    ) throws -> QuestPool {
        var seen: [String: String] = [:]   // slug -> first-seen filename
        var collected: [PoolQuest] = []
        let decoder = JSONDecoder()

        for name in basenames {
            // The QuestPool/ subdirectory is preserved in the .app bundle via
            // project.yml's folder-reference (`type: folder`). If a future
            // refactor flattens the resources, this lookup fails loudly at
            // load time — which is correct: the build is the wrong shape.
            // No silent flat-bundle fallback.
            guard let url = bundle.url(
                forResource: name,
                withExtension: "json",
                subdirectory: "QuestPool"
            ) else {
                throw LoadError.missingResource(name)
            }
            let data: Data
            do {
                data = try Data(contentsOf: url)
            } catch {
                throw LoadError.decodeFailed(name, underlying: error)
            }
            let entries: [PoolQuest]
            do {
                entries = try decoder.decode([PoolQuest].self, from: data)
            } catch {
                throw LoadError.decodeFailed(name, underlying: error)
            }
            for quest in entries {
                if let firstFile = seen[quest.slug] {
                    throw LoadError.duplicateSlug(quest.slug, in: "\(firstFile) and \(name)")
                }
                seen[quest.slug] = name
                collected.append(quest)
            }
        }

        return QuestPool(quests: collected)
    }
}
