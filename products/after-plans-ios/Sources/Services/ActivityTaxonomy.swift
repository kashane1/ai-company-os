import Foundation

// MARK: - Static activity taxonomy
// Source of truth for activity slugs/titles/icons in the iOS app. The
// equivalent rows are seeded into `public.activities` via
// `infra/supabase/seed.sql`; the UUIDs match the seed so a fresh local
// Supabase stack and the in-memory shell agree on identity.
//
// New activities: add a row here AND in seed.sql, using a UUID prefixed
// by the parent category (a0…/a1…/a2… etc.) so visual scanning stays
// easy. Slugs must stay lowercase, ASCII, hyphenated.

enum ActivityTaxonomy {
    /// All activities, parents and children, in display order.
    static let all: [Activity] = parents + children

    static let parents: [Activity] = [
        a("A0000000-0000-0000-0000-000000000001", "sports",    "Sports",    "figure.run",                            nil, 10),
        a("A0000000-0000-0000-0000-000000000002", "fitness",   "Fitness",   "figure.strengthtraining.traditional",   nil, 20),
        a("A0000000-0000-0000-0000-000000000003", "creative",  "Creative",  "paintbrush",                            nil, 30),
        a("A0000000-0000-0000-0000-000000000004", "social",    "Social",    "person.2",                              nil, 40),
        a("A0000000-0000-0000-0000-000000000005", "outdoors",  "Outdoors",  "leaf",                                  nil, 50),
        a("A0000000-0000-0000-0000-000000000006", "community", "Community", "person.3",                              nil, 60),
    ]

    static let children: [Activity] = {
        let sportsID = parents[0].id
        let fitnessID = parents[1].id
        let creativeID = parents[2].id
        let socialID = parents[3].id
        let outdoorsID = parents[4].id
        let communityID = parents[5].id
        return [
            a("A1000000-0000-0000-0000-000000000001", "basketball", "Basketball", "basketball",         sportsID, 110),
            a("A1000000-0000-0000-0000-000000000002", "soccer",     "Soccer",     "soccerball",         sportsID, 120),
            a("A1000000-0000-0000-0000-000000000003", "tennis",     "Tennis",     "tennis.racket",      sportsID, 130),
            a("A1000000-0000-0000-0000-000000000004", "volleyball", "Volleyball", "volleyball",         sportsID, 140),
            a("A2000000-0000-0000-0000-000000000001", "run",        "Run",        "figure.run",         fitnessID, 210),
            a("A2000000-0000-0000-0000-000000000002", "walk",       "Walk",       "figure.walk",        fitnessID, 220),
            a("A2000000-0000-0000-0000-000000000003", "bike",       "Bike",       "bicycle",            fitnessID, 230),
            a("A2000000-0000-0000-0000-000000000004", "yoga",       "Yoga",       "figure.yoga",        fitnessID, 240),
            a("A2000000-0000-0000-0000-000000000005", "pilates",    "Pilates",    "figure.pilates",     fitnessID, 250),
            a("A3000000-0000-0000-0000-000000000001", "pottery",    "Pottery",    "cup.and.saucer",     creativeID, 310),
            a("A3000000-0000-0000-0000-000000000002", "art-class",  "Art class",  "paintpalette",       creativeID, 320),
            a("A3000000-0000-0000-0000-000000000003", "music",      "Music",      "music.note",         creativeID, 330),
            a("A4000000-0000-0000-0000-000000000001", "coffee",     "Coffee",     "cup.and.saucer.fill",socialID, 410),
            a("A4000000-0000-0000-0000-000000000002", "dinner",     "Dinner",     "fork.knife",         socialID, 420),
            a("A4000000-0000-0000-0000-000000000003", "drinks",     "Drinks",     "wineglass",          socialID, 430),
            a("A4000000-0000-0000-0000-000000000004", "brunch",     "Brunch",     "sun.and.horizon",    socialID, 440),
            a("A4000000-0000-0000-0000-000000000005", "coworking",  "Coworking",  "laptopcomputer",     socialID, 450),
            a("A5000000-0000-0000-0000-000000000001", "hike",       "Hike",       "mountain.2",         outdoorsID, 510),
            a("A5000000-0000-0000-0000-000000000002", "climb",      "Climb",      "figure.climbing",    outdoorsID, 520),
            a("A5000000-0000-0000-0000-000000000003", "beach",      "Beach",      "beach.umbrella",     outdoorsID, 530),
            a("A5000000-0000-0000-0000-000000000004", "park",       "Park",       "tree",               outdoorsID, 540),
            a("A5000000-0000-0000-0000-000000000005", "dog-walk",   "Dog walk",   "pawprint",           outdoorsID, 550),
            a("A6000000-0000-0000-0000-000000000001", "book-club",  "Book club",  "books.vertical",     communityID, 610),
            a("A6000000-0000-0000-0000-000000000002", "meetup",     "Meetup",     "person.3.sequence",  communityID, 620),
            a("A6000000-0000-0000-0000-000000000003", "board-games","Board games","gamecontroller",     communityID, 630),
            a("A6000000-0000-0000-0000-000000000004", "playdate",   "Kids playdate","figure.2.and.child.holdinghands", communityID, 640),
            a("A6000000-0000-0000-0000-000000000005", "church",     "Church",     "building.columns",   communityID, 650),
        ]
    }()

    static func parent(of activity: Activity) -> Activity? {
        guard let parentID = activity.parentActivityID else { return nil }
        return parents.first { $0.id == parentID }
    }

    static func children(of parent: Activity) -> [Activity] {
        children.filter { $0.parentActivityID == parent.id }
    }

    private static func a(_ id: String, _ slug: String, _ title: String, _ icon: String, _ parent: UUID?, _ rank: Int) -> Activity {
        Activity(
            id: UUID(uuidString: id)!,
            slug: slug,
            title: title,
            iconSystemName: icon,
            parentActivityID: parent,
            sortRank: rank
        )
    }
}
