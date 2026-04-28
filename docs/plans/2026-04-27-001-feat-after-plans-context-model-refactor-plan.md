---
title: "feat: After Plans context model refactor — activity+venue, public plans, closeness graph"
type: feat
status: active
date: 2026-04-27
origin: docs/brainstorms/2026-04-27-after-plans-context-model-brainstorm.md
---

# feat: After Plans context model refactor — activity+venue, public plans, closeness graph

## Enhancement Summary

**Deepened on:** 2026-04-27
**Sections enhanced:** Phase 1, Phase 4, Phase 6, Phase 7, Risks, Acceptance Criteria
**Research agents used:** architecture-strategist, security-sentinel, data-integrity-guardian, performance-oracle, best-practices-researcher

### Key changes from deepening (load-bearing — do not skip)

1. **Migration must split** (data-integrity #1, CRITICAL). `ALTER TYPE plan_visibility ADD VALUE 'public'` cannot share a transaction with statements that *use* the new value. Three migration files now: `0002_add_public_visibility.sql` (just the enum extension, idempotent via `IF NOT EXISTS`), `0003_context_model_refactor.sql` (everything else from original Phase 1), `0004_push_outbox.sql` (was Phase 7's `0003`).

2. **Onboarding bulk auto-join must be a single RPC** (performance #5, BLOCK-RELEASE). 10 round-trips on first launch = 1.5–3s worst-case first impression. Phase 4 now ships a server-side `auto_join_contexts(context_ids[])` RPC; client makes one call.

3. **`maybe_form_auto_context()` moves off the wrap transaction** (data-integrity #4, performance #3). Trigger only enqueues a `context_formation_jobs` row + advisory-locked idempotency write; an Edge Function does the bulk participant + interest conversion + push fan-out. Wrap transaction stays <20ms regardless of context size.

4. **Closeness recursive CTE restructured** (performance #1, architecture #5). Two explicit CTEs with hop-level `LIMIT`, not a single recursive CTE. Specific named indexes added to Phase 1: `(user_id, lifecycle) INCLUDE (plan_id) WHERE lifecycle='confirmed'` and `(plan_id, lifecycle) INCLUDE (user_id) WHERE lifecycle='confirmed'`. The 250ms p95 SLO is achievable only with this restructure.

5. **Public feed: closeness computed in ONE parameterized query**, not N per candidate plan (architecture #5, performance #2). Returns `(host_id, score)` joined into the feed query. Materialized `closeness_scores` table moves up from "v2" to "Phase 6 if integration test shows >200ms p95."

6. **Push token reassignment** (security H3, CRITICAL one-line fix). `on conflict (token) do update set user_id = excluded.user_id, last_seen_at = now()`. Sign-out hook deletes the row. Dispatcher re-checks `user_id` at send time, not enqueue time.

7. **Public-plan visibility predicate goes in the inline `plans_visibility_select` policy AND in `user_can_see_plan` helper** (security H2). Updating only the helper leaves a hole. Integration test must hit PostgREST directly to verify.

8. **Residential venue de-anonymization guardrail** (security H4). Server-side: reject venues whose Apple POI category is `Residential`. Plus: a venue is only `publicMatch`-eligible after ≥3 independent users have declared interest at it (poison-pill defense).

9. **Sock-puppet auto-context capture mitigation** (security M1). Auto-formed contexts are *probationary* until a third independent user (account >24h old, distinct push token) joins. Until then, the context isn't surfaced as a discoverable join target via interest-matching.

10. **Activity hierarchy: explicit SQL helpers** (architecture #4). `activity_matches_exact()` and `activity_matches_hierarchical()` enforce the visibility-vs-recommendation separation at the function-name level. `parent_activity_id` carries a schema comment: "RECOMMENDATIONS ONLY — never used in visibility predicates."

11. **MKLocalSearchCompleter is the typeahead surface** (best-practices), not raw `MKLocalSearch.start()` per keystroke. Apple's `MKMapItem.identifier` is nullable — freeform fallback path triggers when nil. No `NSLocationWhenInUseUsageDescription` needed (confirmed against MapKit privacy manifest).

12. **APNs uses token-based JWT (ES256) with `.p8` AuthKey**, not legacy certs. Push outbox dedupes via `dedupe_key UNIQUE` (insert-time) + `apns-id` header (delivery-time). pgmq queue + Edge Function consumer pattern, not direct `pg_net` from trigger.

### New considerations discovered

- **`user_activity_interests` PK fix.** Plan's `(user_id, activity_id, venue_id)` PK breaks when `ON DELETE SET NULL` nulls two venues for the same activity. Replaced with two partial unique indexes.
- **FK ON DELETE clauses** specified throughout (`venues.created_by ON DELETE SET NULL`, etc.).
- **`push_outbox` retention** via `pg_cron` job (sent: 7d, failed: 30d).
- **`search_path = public`** explicitly set in every security-definer function (security M2).
- **Block check inheritance** on the new `'public'` visibility arm (security M5).
- **Venue name sanitization** for unicode RTL overrides + zero-width chars before display (security M4).
- **Race between interest-declare and auto-context-formation** mitigated via shared advisory lock on both write paths (data-integrity #7).
- **Apple Place ID treated as untrusted client input** (security L2). Venues created from client searches are flagged `verified=false` until server-side reconciliation; only `verified=true` venues are auto-merge eligible.
- **MKLocalSearch SLO must segment by network**: Wi-Fi <500ms, cellular <1000ms (performance #4). Current plan's <500ms is unrealistic on cellular.

These changes are reflected inline in the affected phases below and in the Risks table.

## Overview

After Plans v1 currently has a thin context model: three hand-curated
contexts seeded into the database, plans live inside one selected
context, and visibility is one of `same_context_only` / `invite_only` /
`known_people` / `friends_of_participants`. This refactor replaces
pre-seeding with a user-built context model — every new user picks
activities and venues during onboarding, gets auto-joined to existing
matching contexts, and contexts emerge organically from wrapped public
plans.

The refactor lands as a sequenced 8-phase rollout. The schema migration
(0002) is additive (existing 0001 stays), the iOS data layer fans out
through both `InMemoryBackend` and `SupabaseBackend`, and the UI lands
in three steps (onboarding → plan creation → home/feed). Each phase has
a green-tests stop condition.

The 51 currently green tests must stay green throughout, growing as new
surfaces land. The Supabase integration test (`SupabaseBackendIntegrationTests`)
is extended phase-by-phase to cover the new flows end-to-end.

This plan is the implementation arm of the brainstorm at
`docs/brainstorms/2026-04-27-after-plans-context-model-brainstorm.md`.
All design decisions are locked there; this document does not relitigate
them.

## Problem Statement

The current model has four problems:

1. **Cold-start bottleneck.** New users without shared context see an
   empty feed. Pre-seeding contexts (the current approach) puts the
   founder personally in the loop for every context's bootstrap.
2. **Conflation of activity and context.** Two basketball players at
   different gyms share an interest, not a context. The schema treats
   contexts as the only grouping, which forces either over-broad
   contexts ("basketball") or under-discoverable ones ("Tuesday pickup
   at Westside Court Court 3").
3. **Visibility tangled with social degree.** `known_people` and
   `friends_of_participants` mix a closeness signal into a visibility
   gate, making the privacy story muddier than necessary and blocking
   the cleaner "visibility is bounded; closeness is ranking" model.
4. **No emergent path from one-off plan to recurring context.** Today a
   one-off plan has nowhere to land — there's no mechanism for a wrapped
   plan to crystallize into a context that future plans can ride on.

The locked decisions in the brainstorm address all four.

## Locked Decisions Reference

The complete list of locked decisions and the alternatives considered
lives in the brainstorm:
[docs/brainstorms/2026-04-27-after-plans-context-model-brainstorm.md](../brainstorms/2026-04-27-after-plans-context-model-brainstorm.md).

The most plan-shaping decisions, restated for context:

- New `PlanVisibility` value: **`publicMatch`** (Swift identifier;
  Postgres enum value `'public'`). Removes `known_people` and
  `friends_of_participants` from active use.
- New schema: `activities`, `venues` (with `latitude`, `longitude`,
  `apple_place_id`), `user_activity_interests`, `plan_recommendations`,
  `push_devices`.
- Apple MKLocalSearch is the geocoding provider (free, native, no
  permission required).
- Multi-step onboarding: intro carousel → name → privacy mode → activity+venue
  picker → optional invite code.
- Auto-context formation when a `publicMatch` plan wraps with ≥2 unique
  confirmed participants. Smart merge by Apple Place ID first, lat/lng
  ≤30m fallback (only between geocoded venues; freeform venues never
  auto-merge to avoid chain-merge ambiguity).
- Closeness graph computed on the fly via recursive SQL on
  `plan_participants where lifecycle = confirmed`. 1st and 2nd degree;
  3rd skipped.
- Server-side push notifications for matches, joins, lifecycle
  transitions, and auto-context membership.

## Technical Approach

### Architecture

```
┌────────────────────────────────────────────────────────┐
│                       iOS App                          │
│                                                        │
│  Features/Onboarding (multi-step)                      │
│  Features/CreatePlan (3 visibility modes)              │
│  Features/Home (ranked feed + recommendations)         │
│  Features/PlanDetail (co-invite suggestions)           │
│  Features/Confirmation (post-wrap "did you know")      │
│         │                                              │
│  AfterPlansStore (state machine + actions)             │
│         │                                              │
│  AfterPlansBackend (protocol bundle)                   │
│   ├── PlanService, IdentityService, ContextService     │
│   ├── ActivityService          [NEW]                   │
│   ├── VenueService             [NEW]                   │
│   ├── RecommendationService    [NEW]                   │
│   └── PushRegistration         [NEW]                   │
│         │                                              │
│  ┌──────┴──────────┐    ┌────────────────────────┐     │
│  │ InMemoryBackend │    │ SupabaseBackend        │     │
│  │ (tests/preview) │    │ (live wire path)       │     │
│  └─────────────────┘    └────────────┬───────────┘     │
│                                      │                 │
│  VenueSearchService (MKLocalSearch wrapper)  [NEW]     │
└──────────────────────────────────────┼─────────────────┘
                                       │
                            ┌──────────▼──────────┐
                            │ Supabase (Postgres) │
                            │                     │
                            │  + activities       │
                            │  + venues           │
                            │  + user_activity_   │
                            │      interests      │
                            │  + plan_            │
                            │      recommendations│
                            │  + push_devices     │
                            │  + new RLS policies │
                            │  + closeness fn     │
                            │  + auto-context     │
                            │      trigger        │
                            │  + push outbox fn   │
                            └─────────────────────┘
```

### Implementation Phases

Each phase has: scope, files affected, schema changes (if any), test
plan, and stop condition.

---

#### Phase 1 — Schema foundation (`0002_*.sql` + `0003_*.sql`)

**Scope:** every backend change lands across two migration files so the
iOS work in subsequent phases has a stable target. The split is
mandatory because Postgres requires `ALTER TYPE ... ADD VALUE` to commit
before the new label is usable in subsequent statements.

**Files:**

- `infra/supabase/migrations/0002_add_public_visibility.sql` — new file.
  **Single statement only:** `ALTER TYPE plan_visibility ADD VALUE IF NOT EXISTS 'public';`
  No `BEGIN`. No additional statements. Idempotent across reruns.
- `infra/supabase/migrations/0003_context_model_refactor.sql` — new file.
  Contains everything else originally planned for 0002: new tables, RLS,
  helpers, trigger plumbing.
- `infra/supabase/seed.sql` — extended with seed activities; the three
  existing context inserts are kept (they're inert anonymous data and
  removing them would leave dev DBs in an awkward intermediate state).
- (`infra/supabase/migrations/0004_push_outbox.sql` lands in Phase 7 —
  renumbered from the original Phase 7's `0003`.)

**Schema changes:**

```sql
-- ENUM extension (must be in its own transaction at the top)
alter type plan_visibility add value 'public';

-- New tables
create table public.activities (
    id uuid primary key default gen_random_uuid(),
    slug text unique not null check (char_length(slug) between 1 and 32),
    title text not null check (char_length(title) between 1 and 48),
    icon_system_name text not null,
    parent_activity_id uuid references public.activities(id),
    sort_rank int not null default 100,
    created_at timestamptz not null default now()
);

create table public.venues (
    id uuid primary key default gen_random_uuid(),
    name text not null check (char_length(name) between 1 and 120),
    address text,
    latitude double precision,
    longitude double precision,
    apple_place_id text unique,
    apple_poi_category text, -- 'Residential' rejected for publicMatch eligibility
    is_freeform boolean not null default false,
    verified boolean not null default false, -- server-side reconciled
    interest_count int not null default 0, -- denorm; auto-context eligibility gate
    created_by uuid references public.profiles(id) on delete set null,
    created_at timestamptz not null default now()
);
create index venues_latlng_idx on public.venues (latitude, longitude)
    where latitude is not null and longitude is not null;
create index venues_apple_place_idx on public.venues (apple_place_id)
    where apple_place_id is not null;

create table public.user_activity_interests (
    user_id uuid not null references public.profiles(id) on delete cascade,
    activity_id uuid not null references public.activities(id) on delete cascade,
    venue_id uuid references public.venues(id) on delete set null,
    declared_at timestamptz not null default now()
);
-- PK split into two partial unique indexes because (user_id, activity_id, venue_id)
-- as a real PK breaks when ON DELETE SET NULL nulls two venues for the same activity.
create unique index user_activity_interests_with_venue_pk
    on public.user_activity_interests (user_id, activity_id, venue_id)
    where venue_id is not null;
create unique index user_activity_interests_no_venue_pk
    on public.user_activity_interests (user_id, activity_id)
    where venue_id is null;
create index user_activity_interests_activity_idx
    on public.user_activity_interests (activity_id, venue_id);

create table public.plan_recommendations (
    id uuid primary key default gen_random_uuid(),
    recipient_id uuid not null references public.profiles(id) on delete cascade,
    plan_id uuid references public.plans(id) on delete cascade,
    activity_id uuid references public.activities(id) on delete set null,
    venue_id uuid references public.venues(id) on delete set null,
    kind text not null check (kind in ('did_you_know','co_invite','friends_frequent')),
    reason text,
    created_at timestamptz not null default now(),
    dismissed_at timestamptz
);

create table public.push_devices (
    user_id uuid not null references public.profiles(id) on delete cascade,
    token text primary key,
    platform text not null check (platform in ('ios','android')),
    created_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now()
);

-- Plans table gains optional activity/venue references
alter table public.plans add column activity_id uuid references public.activities(id) on delete set null;
alter table public.plans add column venue_id uuid references public.venues(id) on delete set null;
create index plans_activity_venue_idx on public.plans (activity_id, venue_id, lifecycle);

-- Auto-context formation jobs (off-trigger; processed by Edge Function)
create table public.context_formation_jobs (
    id uuid primary key default gen_random_uuid(),
    plan_id uuid not null references public.plans(id) on delete cascade,
    enqueued_at timestamptz not null default now(),
    processed_at timestamptz,
    failed_at timestamptz,
    last_error text
);
create index context_formation_jobs_unprocessed_idx
    on public.context_formation_jobs (enqueued_at)
    where processed_at is null;

-- Indexes that enable the closeness graph query (per performance review #1)
create index plan_participants_user_lifecycle_idx
    on public.plan_participants (user_id, role)
    include (plan_id);
create index plan_participants_plan_lifecycle_idx
    on public.plan_participants (plan_id, role)
    include (user_id);

-- Profiles gains a privacy_mode column
alter table public.profiles add column privacy_mode text
    not null default 'open'
    check (privacy_mode in ('open','strict'));
```

**New SQL functions** (all with `set search_path = public` explicitly):

- `public.activity_matches_exact(a uuid, b uuid)` returns boolean.
  Used by VISIBILITY predicates only. `select a = b`.
- `public.activity_matches_hierarchical(a uuid, b uuid)` returns boolean.
  Used by RECOMMENDATION queries only. Walks `parent_activity_id` one
  level. Schema comment on `activities.parent_activity_id` explicitly
  warns: "RECOMMENDATIONS ONLY — never used in visibility predicates."
- `public.user_can_see_plan(p_plan_id uuid)` — extended to include the
  `'public'` arm AND the `'known_people'` arm (kept for legacy data
  hydration; never matched by new code). For `'public'` plans:
  - Caller must have a matching `user_activity_interests` row using
    `activity_matches_exact` (NOT hierarchical).
  - Match requires `(activity_id = plan.activity_id AND (venue_id IS NULL OR venue_id = plan.venue_id))`.
  - **Block check inherited:** `not public.has_block(host_id) and not exists (select 1 from plan_participants pp where pp.plan_id = plans.id and pp.role = 'confirmed' and public.has_block(pp.user_id))`.
- **`plans_visibility_select` policy itself** must be rewritten to add
  the `'public'` arm inline (per security H2 — updating only the helper
  leaves a hole). Integration test must verify by hitting PostgREST
  directly as user B against a user-A public plan with no matching
  interest.
- `public.closeness_scores(recipient uuid, candidate_hosts uuid[])`
  returns table `(host_id uuid, score int)` — single parameterized query
  for the public-feed ranking case. Uses the two explicit-CTE pattern,
  not a general recursive CTE:
  ```sql
  with first_degree as (
      select distinct pp2.user_id as friend_id
      from plan_participants pp1
      join plan_participants pp2 using (plan_id)
      where pp1.user_id = recipient and pp1.role = 'confirmed'
        and pp2.role = 'confirmed' and pp2.user_id <> recipient
      limit 200
  ),
  second_degree as (
      select pp.user_id, count(*) as weight
      from first_degree fd
      join plan_participants me on me.user_id = fd.friend_id and me.role = 'confirmed'
      join plan_participants pp on pp.plan_id = me.plan_id and pp.role = 'confirmed'
      where pp.user_id <> recipient and pp.user_id not in (select friend_id from first_degree)
      group by pp.user_id
      limit 500
  )
  select host_id, sum(score)::int from (
      select friend_id as host_id, 100 as score from first_degree where friend_id = any(candidate_hosts)
      union all
      select user_id, weight * 10 as score from second_degree where user_id = any(candidate_hosts)
  ) s group by host_id;
  ```
  - `set local statement_timeout = '250ms'` at start of function body.
  - `LIMIT 200` at first hop, `LIMIT 500` at second.
- `public.closeness(target_user uuid)` (deprecated/removed in favor of
  the bulk variant above; if a single-pair query is needed, wrap the
  bulk function with a one-element array).
- `public.maybe_form_auto_context(p_plan_id uuid)` — security definer,
  `set search_path = public`. **Trigger does only the lightweight gate**:
  1. Check: plan was `publicMatch` AND just transitioned to `closed`
     AND distinct confirmed participants ≥ 2 AND
     `venues.apple_poi_category IS DISTINCT FROM 'Residential'` for
     this plan's venue.
  2. Acquire `pg_try_advisory_xact_lock(hashtextextended(activity_id::text || coalesce(apple_place_id, venue_id::text), 0))`.
     If not acquired, exit (another wrap is processing).
  3. Insert one row into `context_formation_jobs (plan_id)` (idempotent
     via unique partial index on `(plan_id) where processed_at is null`).
  4. Trigger function exits in <20ms regardless of plan size. The
     Edge Function consumer does the bulk work asynchronously.
  - **`EXCEPTION WHEN OTHERS`** at the end: log to `trigger_errors`
     table (also added in 0003), never re-raise. Wrap transaction must
     succeed even if context formation can't be enqueued.
- `public.enqueue_push_event(...)` — inserts to `push_outbox` for
  consumption by an Edge Function (Phase 7). Same `EXCEPTION WHEN OTHERS`
  swallow pattern.

**New RLS policies:**

- `activities`: `select to authenticated using (true)`. No write policy
  (server-managed via migration / admin only).
- `venues`: `select to authenticated using (true)`;
  `insert to authenticated with check (created_by = auth.uid())`. No
  update/delete by clients.
- `user_activity_interests`: `for all to authenticated using
  (user_id = auth.uid()) with check (user_id = auth.uid())`.
- `plan_recommendations`: `select to authenticated using
  (recipient_id = auth.uid())`. Inserts via security-definer trigger
  functions only (no client write policy).
- `push_devices`: `for all to authenticated using
  (user_id = auth.uid()) with check (user_id = auth.uid())`.
- `plans` `plans_visibility_select` policy: rewritten to add the
  `'public'` arm via the updated `user_can_see_plan` helper. Existing
  `'known_people'` arm becomes orphaned (data preserved, never matched
  by new code).

**Realtime publications:** add `plan_recommendations` to
`supabase_realtime`.

**Test plan:**

- `supabase db reset` runs clean.
- `psql` smoke: insert a sample activity, venue, interest; confirm RLS
  blocks cross-user reads; confirm `closeness()` returns 0 for an
  isolated user; confirm `maybe_form_auto_context()` is a no-op when
  conditions aren't met.

**Stop condition:** `supabase db reset` is clean; the existing 51 iOS
tests are still green (none touch the new tables yet); a one-line psql
smoke confirms the new helpers don't crash.

---

#### Phase 2 — iOS data + protocol layer

**Scope:** add new domain types, extend protocols, ship both backend
adapters' implementations of the new protocols. No UI changes yet.

**Files:**

- `products/after-plans-ios/Sources/Models/AfterPlansModels.swift`
  - Add `Activity`, `Venue`, `UserActivityInterest`, `PlanRecommendation`
    structs.
  - Add `case publicMatch` to `PlanVisibility`. Update `launchModes`
    from `[.sameContextOnly, .inviteOnly, .knownPeople]` to
    `[.sameContextOnly, .inviteOnly, .publicMatch]`. Add cases to all
    six exhaustive switches in the file (`title`, `subtitle`,
    `trustBadge`, `visibilityHeadline`, `visibilityDetail`,
    `visibilityFootnote`, `shareAudienceHeadline`, `shareAudienceDetail`,
    `inviteChannels`).
  - `knownPeople` and `friendsOfParticipants` cases stay in the enum
    (Swift can keep them; they're just absent from `launchModes`) so
    legacy data can still hydrate without crashing. Mark with a
    `// TODO: remove in v2` comment.
  - Extend `UserProfile` with `privacyMode: PrivacyMode` (new enum).
  - Extend `AfterPlan` with `activityID: UUID?`, `venueID: UUID?`.
- `products/after-plans-ios/Sources/Services/NetworkProtocols.swift`
  - Add `ActivityServiceProtocol`, `VenueServiceProtocol`,
    `RecommendationServiceProtocol`, `PushRegistrationProtocol`.
  - Extend `AfterPlansBackend` struct with the four new fields.
- `products/after-plans-ios/Sources/Services/InMemoryBackend.swift` and
  `InMemoryServices.swift` — full implementations of the new protocols
  against in-memory state. Seed activities + venues so previews and
  unit tests work without a real backend.
- `products/after-plans-ios/Sources/Services/SupabaseBackend.swift` —
  full implementations against the live wire path from Phase 1.
  - New `SupabaseActivityService`, `SupabaseVenueService`,
    `SupabaseRecommendationService`, `SupabasePushService` structs.
  - Wire DTOs for the new tables (snake_case ↔ camelCase mapping
    following the existing `ProfileRow` / `PlanRow` pattern).
  - Update existing `PlanRow` / `PlanInsert` to include
    `activity_id`, `venue_id`.

**Test plan:**

- `Tests/Services/InMemoryBackendTests.swift` — add tests for each new
  protocol (declare interest, search venues stub, list recommendations).
- `Tests/Services/SupabaseBackendIntegrationTests.swift` — extend
  `testFullLifecycleAgainstLocalSupabase` to also exercise:
  declare interest, search venues, list activities. Wrap-time
  auto-context behavior is tested in Phase 4 (when public-plan creation
  exists).
- `Tests/Models/PlanVisibilityTests.swift` — new file. Switch
  exhaustiveness smoke test asserting every case has non-empty `title`,
  `subtitle`, etc., and that `launchModes` covers exactly the three
  active values.

**Stop condition:** 51 + N tests green (where N ≥ 5 new tests). The
in-memory adapter satisfies every new protocol method; the Supabase
adapter satisfies every method against the live local stack.

---

#### Phase 3 — Apple MKLocalSearch wrapper + activity taxonomy

**Scope:** ship the iOS-side `VenueSearchService` that wraps
`MKLocalSearch`, plus the static activity taxonomy that loads at app
startup.

**Files:**

- `products/after-plans-ios/Sources/Services/VenueSearchService.swift`
  — new file. Protocol + concrete implementation backed by
  **`MKLocalSearchCompleter`** (the typeahead surface — not raw
  `MKLocalSearch.start()` per keystroke; per Apple WWDC23 guidance and
  the best-practices research). Returns canonical address, lat/lng, and
  Apple Place ID via `MKMapItem.identifier?.rawValue` (note the
  optionality — for freeform addresses Apple cannot resolve to a
  canonical POI, identifier is nil and the venue is created with
  `is_freeform = true`, `verified = false`). Debounce **300ms** in a
  `Task` with cancellation; in-memory cache of last 20 queries.
  Handles `MKError.loadingThrottled` (.code 3) by backing off + showing
  cached completions. Confirmed: **does NOT need
  `NSLocationWhenInUseUsageDescription`** because we don't set a
  `region` bias parameter and never instantiate `CLLocationManager`.
- `products/after-plans-ios/Sources/Services/ActivityTaxonomy.swift` —
  new file. Static array of ~30 founder-curated activities. Each has
  `slug`, `title`, `iconSystemName`, optional `parentSlug`. Synced into
  the `activities` table on first app launch by a one-time backend call
  (server-side: an idempotent upsert).
  - Suggested initial taxonomy (tunable by founder): basketball, soccer,
    baseball, tennis, volleyball, **sports** (parent), run, walk, bike,
    hike, climb, yoga, pilates, **fitness** (parent), study, coffee,
    dinner, drinks, brunch, coworking, church, art class, pottery,
    music, **creative** (parent), book club, board games, kids
    playdate, dog walk, beach, park, meetup, conference.
- `products/after-plans-ios/Info.plist` — confirm `NSLocationWhenInUseUsageDescription`
  stays absent (MKLocalSearch does not require it for venue search; it
  only needs the user's location if you bias results to a region —
  which we explicitly don't do in v1, to keep the privacy posture
  clean).
- `products/after-plans-ios/Sources/App/AfterPlansStore.swift` — add
  `availableActivities`, `searchVenues(query:) async`, and a per-search
  cancellation token.

**Test plan:**

- `Tests/Services/VenueSearchServiceTests.swift` — new file.
  Tests debounce + cancellation semantics. Real `MKLocalSearch` calls
  are mocked behind a protocol seam so unit tests don't hit the network.
- `Tests/Services/ActivityTaxonomyTests.swift` — new file. Asserts
  the taxonomy parses, no duplicate slugs, every parent reference is
  resolvable, sort_rank is stable.
- Existing 51 + N from Phase 2 stay green.

**Stop condition:** searching "Westside" in a sample integration test
returns at least one structured result with a Place ID; activity
taxonomy upserts cleanly into the database on first launch.

---

#### Phase 4 — Onboarding refactor (multi-step flow)

**Scope:** replace `OnboardingView` (single carousel) with a multi-step
coordinator. The original 5-card carousel is preserved as the first
step.

**Files:**

- `products/after-plans-ios/Sources/Features/Onboarding/OnboardingView.swift`
  — refactor into a coordinator that switches between sub-views based
  on `OnboardingStep`.
- `products/after-plans-ios/Sources/Features/Onboarding/OnboardingState.swift`
  — new file. `OnboardingStep` enum (`.intro`, `.name`, `.privacy`,
  `.activityVenue`, `.inviteCode`, `.complete`); resumable state
  serialized to UserDefaults so an abandoned onboarding can be picked
  up next launch.
- `products/after-plans-ios/Sources/Features/Onboarding/Steps/IntroCarouselStepView.swift`
  — extracted from current `OnboardingView`'s body. Visual unchanged.
- `products/after-plans-ios/Sources/Features/Onboarding/Steps/NameStepView.swift`
  — new. Required first-name field (≥1 char, ≤24).
- `products/after-plans-ios/Sources/Features/Onboarding/Steps/PrivacyStepView.swift`
  — new. Two-option selector with explanatory copy.
- `products/after-plans-ios/Sources/Features/Onboarding/Steps/ActivityVenueStepView.swift`
  — new. Activity picker (taxonomy-backed) + venue typeahead via
  `VenueSearchService`. Multi-row entry: user can declare multiple
  activity+venue combos before proceeding.
- `products/after-plans-ios/Sources/Features/Onboarding/Steps/InviteCodeStepView.swift`
  — new. Optional. Validates against backend on entry; resolves to a
  plan and seeds the closeness graph from the host outward.
- `products/after-plans-ios/Sources/App/AfterPlansStore.swift` — replace
  `finishOnboarding()` with stepwise transitions. New action methods:
  `updateOnboardingProfile(firstName:, privacyMode:)`,
  `declareActivityInterest(activityID:, venueID:)`,
  `redeemInviteCode(_:)`. Auto-join logic: when interest is declared,
  the backend returns either a `joined_context: ContextID` (matched an
  existing context) or `interest_recorded: true` (no match yet). UI
  shows a small confirmation banner per joined context.
- Bulk auto-join cap: max 10 contexts auto-joined silently. If more
  match, surface "You also matched N more — review and join individually
  in Profile" — defers the rest to a separate review screen.
- Strict privacy mode suppresses auto-join: declared interests are
  recorded but not converted to `context_members` until the user
  manually opts into each context.
- **Bulk auto-join is a single RPC** (per performance review #5 — block-
  release item). Server-side function `public.auto_join_contexts(context_ids uuid[])`
  inserts all `context_members` rows in one transaction, enqueues a
  single push_outbox row per context. iOS calls this once per onboarding
  completion, not N times. Reduces first-impression latency from 1.5–3s
  to ~300ms.

**Test plan:**

- `Tests/Features/Onboarding/OnboardingStateTests.swift` — new. Step
  transitions, resumability, abandoned-then-resumed scenarios.
- `Tests/Services/AfterPlansStoreTests.swift` — extend with onboarding
  action tests against the in-memory backend.
- Manual UI smoke (computer-use): walk a fresh user through onboarding
  end to end against local Supabase. Confirm declared interests land in
  the database and matching contexts are auto-joined.

**Stop condition:** full suite green; manual UI smoke confirms a fresh
anonymous user can complete onboarding and land on Home with declared
activities.

---

#### Phase 5 — Plan creation refactor

**Scope:** plan-creation UI exposes the three new visibility modes.
Conditional required-field UI: each mode shows only the fields it
needs.

**Files:**

- `products/after-plans-ios/Sources/Features/CreatePlan/CreatePlanDraft.swift`
  — add `activityID: UUID?`, `venueID: UUID?`. Update
  `validationMessage(hasContext:)` to check
  `activityID != nil && venueID != nil` when
  `visibility == .publicMatch`.
- `products/after-plans-ios/Sources/Features/CreatePlan/CreatePlanView.swift`
  — visibility section iterates `PlanVisibility.launchModes` (already
  picks up `.publicMatch` from Phase 2). New conditional sub-section:
  when `.publicMatch`, show activity+venue picker (reuses the
  `ActivityVenuePickerView` extracted from Phase 4). Hide the
  context-selector subsection. When `.sameContextOnly`, show only the
  context selector. When `.inviteOnly`, hide both.
- `products/after-plans-ios/Sources/Features/CreatePlan/ActivityVenuePickerView.swift`
  — new shared sub-view (also used in onboarding from Phase 4 if not
  already extracted there).

**Test plan:**

- `Tests/Features/CreatePlan/CreatePlanDraftTests.swift` — add
  validation tests: missing activity for `.publicMatch`, missing venue
  for `.publicMatch`, exact mode required-place rule unchanged, etc.
- `Tests/Services/AfterPlansStoreTests.swift` — extend `createPlan`
  tests across all three visibility modes. Assert the wire round-trip
  via `InMemoryBackend`.
- `Tests/Services/SupabaseBackendIntegrationTests.swift` — extend the
  full-lifecycle test to create a `publicMatch` plan in addition to the
  existing default-visibility one.
- Manual UI smoke: create one of each visibility-type plan against
  local Supabase.

**Stop condition:** full suite green; all three plan types createable
through the UI; database rows show the correct visibility + activity +
venue fields.

---

#### Phase 6 — Home/feed + closeness ranking + recommendation surfaces

**Scope:** the Home feed query applies the new visibility predicates.
Plans are ranked by closeness score. Recommendation surfaces show up in
PlanDetail (co-invite suggestion) and Confirmation (post-wrap "did you
know" card).

**Files:**

- `products/after-plans-ios/Sources/Features/Home/HomeView.swift` —
  current `currentContextPlans` and `secondaryFeedPlans` sections stay.
  Add a third section: "From your activities" — shows `publicMatch`
  plans that match the user's declared interests, ranked by closeness
  to the host.
- `products/after-plans-ios/Sources/App/AfterPlansStore.swift` — add
  `publicFeedPlans: [AfterPlan]` published property and
  `loadPublicFeed()` action. **Closeness scores fetched in ONE call**,
  not per-plan: `loadPublicFeed` first issues the candidate-plan query
  (visibility = public + matching interests), collects unique
  `host_id`s, then a single `closeness_scores(recipient, host_ids[])`
  RPC returns a `(host_id, score)` map. Ranking blends scores into the
  existing `PlanAffinity` helper. Integration test asserts the feed-
  load path makes O(1) backend calls regardless of feed size (per
  performance review #2 and architecture review #5).
- **If integration test shows feed-load p95 > 200ms**, add
  `closeness_scores` materialized table in this phase (don't defer to
  v2): `(user_a, user_b, score, computed_at)` refreshed nightly via
  `pg_cron` and on confirmed-participant changes. The plan's original
  "compute on the fly v1" is fine for ≤10k `plan_participants` rows but
  not for the per-feed-render hot path. Make the call from the
  measurement, not in advance.
- `products/after-plans-ios/Sources/Features/PlanDetail/PlanDetailView.swift`
  — add `CoInviteSuggestionsCard` between the People section and the
  Suggestions section. Loads via `store.coInviteSuggestions(for:
  planID)` (calls backend `RecommendationServiceProtocol`).
- `products/after-plans-ios/Sources/Features/Confirmation/ConfirmationRoomView.swift`
  — add `PostWrapRecommendationsCard` shown when
  `plan.lifecycle == .closed && plan.visibility == .publicMatch`.
  Surfaces 2nd-degree activity+venue suggestions for one-tap join.
- `products/after-plans-ios/Sources/Shared/PlanAffinity.swift` — extend
  with a `closenessScore: Int?` factor; ranking blends existing factors
  with closeness when present.

**Test plan:**

- `Tests/Shared/PlanAffinityTests.swift` — extend with closeness-score
  ranking tests.
- `Tests/Services/AfterPlansStoreTests.swift` — extend with public-feed
  load tests and recommendation-load tests.
- Integration test: extend `SupabaseBackendIntegrationTests` to insert
  multiple plans across visibility types and assert the feed query
  returns only the visible subset, ranked by closeness.

**Stop condition:** full suite green; manual UI smoke shows the three
feed sections rendering correctly; recommendation cards appear in the
documented places.

---

#### Phase 7 — Auto-context formation worker + push notifications

**Scope:** server-side. Two Edge Functions and one migration. The
trigger from Phase 1 only enqueues `context_formation_jobs`; the actual
participant + interest conversion + push fan-out happens
asynchronously in the worker so the wrap transaction stays fast.
Push notifications dispatch via a separate Edge Function consuming
`push_outbox`.

**Files:**

- `infra/supabase/migrations/0004_push_outbox.sql` — new file (renumbered
  from original `0003` per the migration split in Phase 1). Adds:
  - `push_outbox` table:
    ```sql
    create table public.push_outbox (
        id uuid primary key default gen_random_uuid(),
        recipient_id uuid not null references public.profiles(id) on delete cascade,
        dedupe_key text unique not null, -- e.g. "plan:{plan_id}:event:{event_type}:user:{user_id}"
        apns_id uuid not null default gen_random_uuid(), -- passed as apns-id header
        event_type text not null,
        payload jsonb not null,
        status text not null default 'pending' check (status in ('pending','sent','failed','expired')),
        attempts int not null default 0,
        last_error text,
        next_attempt_at timestamptz not null default now(),
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now()
    );
    create index push_outbox_pending_idx on public.push_outbox (next_attempt_at)
        where status = 'pending';
    ```
  - Trigger functions on `plans`, `plan_participants`, `plan_recommendations`,
    and `context_members` insert/update that call `enqueue_push_event`
    for the four notification events.
  - `pg_cron` job: nightly delete `where status='sent' and updated_at < now() - interval '7 days'`
    and `where status='failed' and updated_at < now() - interval '30 days'`.
  - `trigger_errors(id, source_function, error_message, occurred_at)`
    table referenced by the swallow-pattern in `maybe_form_auto_context`
    (see Phase 1).
- `infra/supabase/functions/context_formation_worker/` — new Edge
  Function. Polls `context_formation_jobs where processed_at is null`,
  for each:
  1. Re-acquire the activity+venue advisory lock.
  2. Look up existing context by `(activity_id, venue_id)` — Place ID
     dedup is enforced by the unique constraint on `venues.apple_place_id`,
     so geocoded venues at the same Place ID are the same row.
  3. **Enforce probationary trust gate** (security M1): if creating a
     new context, mark it `is_probationary = true` until a third
     independent user (account >24h old, distinct push token) joins.
     Probationary contexts don't surface as discoverable join targets
     via interest-matching, only as direct invite.
  4. Bulk insert `context_members` rows (`on conflict do nothing`).
  5. Convert matching `user_activity_interests` rows to
     `context_members` — but only for plans whose interest was declared
     before the wrap completed (race-condition guard via `declared_at < jobs.enqueued_at`).
  6. Enqueue per-recipient `push_outbox` rows.
  7. Mark `processed_at = now()`.
  Runs on a 30s `pg_cron` schedule plus immediate trigger via `pg_net`
  on insert.
- `infra/supabase/functions/push_dispatcher/` — new Edge Function. Uses
  **token-based JWT (ES256)** with a `.p8` AuthKey stored as Edge
  Function secret (`APNS_AUTH_KEY_P8`, `APNS_KEY_ID`, `APNS_TEAM_ID`).
  Cert-based auth is legacy; not used. Signs JWT with `jose`, caches
  for ~50 minutes. Endpoint:
  `https://api.push.apple.com/3/device/{token}` with `apns-topic: io.aicompanyos.products.afterplans`
  and `apns-id: {push_outbox.apns_id}` header. **`apns-id` is APNs's
  built-in idempotency key within ~24h** — combined with the
  `dedupe_key UNIQUE` at insert time, this prevents both duplicate
  enqueues and duplicate deliveries. **Re-checks `push_devices.user_id`
  at send time** (per security H3): outbox snapshot is enqueue-time;
  device may have been re-bound to a different user since.
  Retries with exponential backoff, max 5 attempts.
- `infra/supabase/migrations/0004_push_outbox.sql` also adds:
  - `auto_join_contexts(context_ids uuid[])` security-definer function
    (per Phase 4 performance fix). Inserts all `context_members` rows
    in one transaction; enqueues one push per context.
  - `pgmq` extension if not already present, OR direct
    `pg_net.http_post` from trigger if pgmq adds operational complexity
    we don't want yet. Decision deferred to implementation; both are
    documented patterns per the Supabase 2026 best-practices research.
- `products/after-plans-ios/Sources/App/AfterPlansApp.swift` — register
  for push notifications on first launch. Send token to backend via
  new `PushRegistrationProtocol.register(deviceToken:)`. **On sign-out
  (or anonymous-session reset)**, call `PushRegistrationProtocol.unregister(deviceToken:)`
  which deletes the row in `push_devices`.
- `products/after-plans-ios/Sources/Services/SupabaseBackend.swift` —
  `SupabasePushService.register` does
  `insert ... on conflict (token) do update set user_id = excluded.user_id, last_seen_at = now()`
  (security H3 one-line fix). Never naive `do nothing`.
- Notification receive: SwiftUI `onContinueUserActivity` /
  scene-delegate plumbing for tapping a notification to deep-link to
  the right plan or context.

**Test plan:**

- `Tests/Services/PushRegistrationTests.swift` — register/unregister
  flow with the in-memory backend, including the token-reassignment
  case (user A registers, user B registers same token, dispatcher
  must use B's user_id at send time).
- Integration test: trigger a wrap of a `publicMatch` plan with ≥2
  confirmed participants; assert a `context_formation_jobs` row is
  enqueued; manually invoke the worker; assert a new `contexts` row is
  created (or an existing one is matched and joined) AND that the
  context is `is_probationary=true` until a third user joins. Assert
  `push_outbox` rows are enqueued for each new context member with
  unique `dedupe_key`s.
- Concurrent-wrap test (per integration scenario #2): wrap two
  `publicMatch` plans at the same activity+Place ID within ms; assert
  both jobs serialize via the advisory lock and only one new context
  row exists at the end.
- Manual smoke on a physical device (TestFlight): notifications arrive
  for the four event types within 30s of the trigger event.

**Stop condition:** full suite green; the auto-context worker
processes jobs correctly on wrap (sync trigger time <20ms verified via
`pg_stat_statements`); probationary-context gate works; push
notifications arrive on a physical test device.

---

#### Phase 8 — Privacy posture + comprehensive integration test

**Scope:** legal docs + nutrition labels updated; one comprehensive
integration test exercises the full new flow end to end.

**Files:**

- `docs/products/after-plans/legal/PRIVACY_POLICY.md` — add "Venue
  addresses associated with plans you create or join" under "User
  content." Re-confirm "we do not request or use your location."
  Republish to the GitHub Pages mirror at
  https://kashane1.github.io/afterplans-privacy/.
- `docs/products/after-plans/APP_STORE_METADATA_DRAFT.md` — extend
  Privacy Nutrition Labels with the venue-address row under "User
  content."
- `docs/products/after-plans/PHASE_STATUS.md` — add Phase 8 entries.
- `docs/products/after-plans/remaining-steps-before-ios-submission.md`
  — refresh status counts after refactor lands.
- `products/after-plans-ios/Tests/Services/SupabaseBackendIntegrationTests.swift`
  — add `testUserBuiltContextFlow_endToEnd`:
  1. Two anonymous users sign in.
  2. User A goes through onboarding declaring "basketball" + "Westside
     Court" (Apple Place ID seeded for the test).
  3. User B goes through onboarding declaring the same.
  4. User A creates a `publicMatch` plan at basketball+Westside.
  5. User B's public feed surfaces the plan.
  6. User B joins; lifecycle promotes to `forming`. Both users confirm;
     lifecycle promotes to `confirmed`.
  7. User A wraps; assert a new `contexts` row formed with both users
     pre-joined; assert their declared interests have been converted
     into `context_members` rows; assert recommendation rows were
     created.
  8. Verify the integration test is idempotent across reruns.

**Test plan:** full suite green at 51 + N where N includes one
comprehensive end-to-end integration test plus the smaller tests added
in Phases 2–7.

**Stop condition:** full suite green; legal docs republished; metadata
draft updated; phase-status / remaining-steps audit doc reflects the
new state.

---

## Alternative Approaches Considered

The brainstorm captures the full alternatives table; key technical
alternatives that are *not* in this plan:

- **Mapbox / Google Maps for geocoding** — rejected: paid, third-party
  SDK, data-sharing concerns. Apple MKLocalSearch is free, native,
  no permission required.
- **Two-key wrap** — rejected: friction, confusing UX. Single-key wrap
  with the two-person guardrail moved to context-spawn.
- **Time/day pattern as context dimension** — deferred to v2: most
  users won't reliably enter it; complexity explodes.
- **Denormalized `closeness_scores` table** — deferred to v2: compute
  on-the-fly first, optimize when latency demands it.
- **3rd-degree closeness signals** — rejected: signal-to-noise drops
  rapidly past 2nd-degree, and 3rd-degree implications make the
  bounded-visibility promise hard to defend.
- **Phone contacts / social-graph linking as Factor 2 inputs** —
  deferred to v1.1 as opt-in: would flip the privacy posture and require
  new App Review prep. v1 closeness derives from plan-history +
  invite-chain only.

## System-Wide Impact

### Interaction Graph

Wrap → `maybe_form_auto_context()` trigger → advisory lock acquired →
context lookup by Place ID → either insert new context + bulk-insert
context_members + bulk-insert recommendations, OR merge into existing
context + insert new context_members → release lock → insert push_outbox
rows → Edge Function picks up outbox → APNs dispatch → device shows
notification → tap deep-links to the new context's discovery screen
(NEW screen needed in Phase 6 or noted as v1.1 follow-up).

### Error & Failure Propagation

- Trigger function failure on wrap: wrap completes (lifecycle update is
  the load-bearing transaction), context formation is best-effort. Log
  to a `trigger_errors` table for review. Document the
  eventually-consistent nature in the schema comment.
- Push outbox row stuck: Edge Function retries with exponential backoff
  up to 5 attempts; after that, marked failed, surfaced in a small admin
  query.
- MKLocalSearch returns no results: UI offers freeform entry as
  fallback (per locked decision). Freeform venues never auto-merge.
- supabase-swift cached-session race: hardened earlier this session via
  `currentUser()` retry. Pattern carries forward to any new identity-
  dependent calls.

### State Lifecycle Risks

- A user declares interest before any matching context exists. The
  interest row is orphaned until/unless a `publicMatch` plan wraps and
  forms the context. Document this as expected.
- A user changes privacy mode from `open` to `strict` after auto-joining
  contexts: their existing `context_members` rows stay (per least-
  surprise). Document this. v1 accepts; v2 may add a "leave all
  auto-joined contexts" affordance.
- Auto-context formation race: two wraps at the same activity+Place ID
  within ms — advisory lock serializes; second wrap merges into the
  context the first wrap created. Test scenario covers this.

### API Surface Parity

Both `InMemoryBackend` and `SupabaseBackend` implement every protocol
method. Test parity: any new protocol method must have a matching test
in `InMemoryBackendTests` AND a corresponding case in the integration
test. The factory pattern at `SupabaseBackendFactory.make(...)` is the
single seam — new services wire in via that factory.

### Integration Test Scenarios

These five scenarios are not covered by unit tests against
`InMemoryBackend` and must be in the integration test:

1. Two-user public-plan flow → context auto-forms.
2. Concurrent wrap of two `publicMatch` plans at the same activity+Place
   ID → both merge into one context, no duplicate.
3. Strict-privacy user matches a context but is NOT auto-joined; their
   declared interest persists.
4. Closeness graph correctness: user A confirms plans with B, C, D; user
   E is 2nd-degree via B; closeness query returns A→E with the right
   score and excludes any 3rd-degree neighbors.
5. Push-notification delivery on auto-context-membership event:
   `push_outbox` rows created, Edge Function dispatches, no duplicates
   on re-run.

## Acceptance Criteria

### Functional

- [ ] Schema migration `0002` and `0003` apply cleanly; `db reset`
      green.
- [ ] All four new iOS protocols (`ActivityServiceProtocol`,
      `VenueServiceProtocol`, `RecommendationServiceProtocol`,
      `PushRegistrationProtocol`) have InMemory + Supabase
      implementations.
- [ ] PlanVisibility enum exposes exactly three active modes via
      `launchModes`: `.sameContextOnly`, `.inviteOnly`, `.publicMatch`.
      Legacy `.knownPeople` and `.friendsOfParticipants` remain in the
      enum to hydrate stored data without crashing.
- [ ] Multi-step onboarding flow: intro → name → privacy → activity+venue
      → optional invite code → land on Home. Resumable across kills.
- [ ] Plan creation supports all three visibility modes with conditional
      required-field UI.
- [ ] Home feed renders three sections: current context, secondary
      contexts, "from your activities."
- [ ] Wrapping a `publicMatch` plan with ≥2 unique confirmed participants
      auto-forms or merges a context. Smart-merge prefers Apple Place
      ID; lat/lng fallback only between geocoded venues.
- [ ] Push notifications fire for the four documented events on a
      physical TestFlight device.
- [ ] Privacy policy + nutrition labels updated and republished.

### Non-Functional

- [ ] Closeness query p95 latency under 250ms on a 100-confirmed-plan
      history.
- [ ] No new permission prompts at first launch (location, contacts,
      photos, mic, camera all remain absent).
- [ ] Apple MKLocalSearch typeahead (via `MKLocalSearchCompleter`)
      delivers first-results under **500ms p95 on Wi-Fi, 1000ms p95 on
      cellular**. SLO segments by network because the cellular tail is
      not under our control (per performance review #4).

### Quality Gates

- [ ] All 51 existing tests green throughout (no regression at any phase
      stop).
- [ ] Net new test count ≥ 20 (rough estimate: 5 in Phase 2, 3 in Phase
      3, 4 in Phase 4, 3 in Phase 5, 3 in Phase 6, 1 in Phase 7, 1
      end-to-end in Phase 8).
- [ ] Integration test idempotent across reruns (proven by running 3×
      in succession).
- [ ] No orphan `auth.users` rows from the new flows (existing test
      pattern in `SupabaseBackendIntegrationTests` for currentUser
      flake-fix carries forward).

## Success Metrics

These are observable post-launch (require cloud Supabase + telemetry,
which are out of scope here but should be wired in v1.0.1):

- **Activation rate**: % of new users who declare ≥1 activity+venue in
  onboarding (target: ≥80%)
- **Auto-join hit rate**: % of declared interests that find an existing
  context within 7 days (early proxy for whether the model achieves
  emergent context density)
- **Auto-context formation rate**: # of contexts auto-formed per week
  from wrapped public plans (validates the emergent-formation
  mechanism works)
- **Cold-start feed density**: average # of plans visible to a brand-new
  user 24h after onboarding (target: ≥3)
- **Closeness signal density**: average # of 1st-degree neighbors per
  user 30d after install

## Dependencies & Prerequisites

- **Local Supabase running** (for development + integration tests).
  Already set up.
- **supabase-swift package linked** in project.yml. Already done.
- **Xcode 15+ with iOS 17+ deployment target** for the SwiftUI patterns
  used in the new onboarding flow. Already met.
- **Apple Developer account** for APNs key (Phase 7 push notifications
  on physical device). Same as required for TestFlight.
- **Cloud Supabase project** is NOT required for this refactor; it's a
  prerequisite for TestFlight (separate plan).

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Auto-context race condition (two wraps at same venue → duplicate context) | Medium | High | Postgres advisory lock in `maybe_form_auto_context()`; unique constraint on `venues.apple_place_id` so geocoded venues at the same Place ID are the same row already |
| Smart-merge chain on freeform venues (A↔B↔C within 30m chain) | Low | Medium | Solved structurally: only Apple Place ID matches auto-merge; freeform venues never auto-merge |
| Closeness query timeout on dense graphs | Medium | Medium | `LIMIT 50` on neighbor fan, `statement_timeout` SET LOCAL 250ms, 2nd-degree cap, denormalize to a table in v2 if needed |
| Bulk auto-join overwhelm during onboarding | Medium | Low | Cap silent auto-joins at 10; defer the rest to a Profile review screen |
| Strict-privacy interaction unclear | Low | Medium | Strict mode suppresses auto-join entirely; interests recorded for opt-in later. Documented in privacy mode help copy |
| Residential venue privacy leak ("Maya's house, 123 Oak St") | Medium | Medium | Soft warning UI when MKLocalSearch returns no results: "This looks like a private location — anyone joining will see the address. Continue?" |
| Push token edge cases (anonymous user with no device token, blocked-pair, opted-out) | Low | Low | Outbox dispatcher checks `push_devices` for a token before sending; blocked-pair check inline; opted-out is a v1.0.1 concern |
| Onboarding abandonment → orphan `auth.users` row | Medium | Low | Already handled in dev (the `currentUser` retry fix from this session). Production cleanup is a separate concern (no production DB yet) |
| supabase-swift session drift across multi-step onboarding | Low | Medium | Same retry pattern that hardened `currentUser()` carries forward to any new identity-dependent backend calls |
| MKLocalSearch returns inconsistent Place IDs across locales | Low | Low | Document as known v1 limitation; if same physical venue gets two Place IDs in two locales, two contexts auto-form. v2 reconciliation tooling if it surfaces |
| 0001 + 0002 enum-add transaction boundary | Was Low → confirmed by data-integrity review as CRITICAL | High (deploy break) | **Resolved:** split into 0002 (just enum extension, idempotent via `IF NOT EXISTS`) and 0003 (everything else). Phase 1 updated to reflect. `0004_push_outbox.sql` is what was originally Phase 7's `0003`. |
| Push token reassignment on shared device → wrong user gets pushes (security H3) | Medium | Catastrophic (cross-user privacy) | One-line fix in `register`: `on conflict (token) do update set user_id = excluded.user_id, last_seen_at = now()`. Sign-out hook deletes the row. Dispatcher re-checks `user_id` at send time, not enqueue time. Integration test required. |
| Sock-puppet auto-context capture (security M1) | Medium | High | Probationary contexts: auto-formed contexts don't surface as discoverable join targets via interest-matching until a third independent user (account >24h old, distinct push token) joins. |
| Residential venue de-anonymization (security H4) | Medium | High | Server-side reject venues with Apple POI category `Residential`. Plus: `interest_count` denorm + `verified` flag; venue is `publicMatch`-eligible only after ≥3 independent users have declared interest. |
| Public-plan visibility predicate update misses inline policy (security H2) | Low | Catastrophic if missed (visibility hole) | Phase 1 explicitly updates BOTH `plans_visibility_select` policy AND `user_can_see_plan` helper. Integration test hits PostgREST directly to verify gate. |
| `maybe_form_auto_context()` blocks wrap transaction (data-integrity #4, performance #3) | High at scale | High (UX block) | Trigger only enqueues `context_formation_jobs` row (<20ms); Edge Function does the bulk work. `EXCEPTION WHEN OTHERS` swallows + logs to `trigger_errors` so wrap always completes. |
| Onboarding 10× round-trips on first launch (performance #5) | High | High (1.5–3s first impression) | `auto_join_contexts(context_ids[])` RPC: single backend call. Drops to ~300ms. Block-release item per perf review. |
| Closeness recursive CTE doesn't push down LIMIT (performance #1) | High at modest scale | High (latency landmine) | Two explicit CTEs with hop-level `LIMIT 200` + `LIMIT 500`, not generic recursive CTE. Specific named indexes added in Phase 1. `set local statement_timeout = '250ms'` inside function body. |
| Public feed = N closeness queries per render (performance #2, architecture #5) | High | High | `closeness_scores(recipient, candidate_hosts[])` returns full ranking in one call. Integration test asserts O(1) backend calls per feed render. Materialized table escalation if measured p95 >200ms. |
| `user_activity_interests` PK breaks under `ON DELETE SET NULL` (data-integrity #2) | Low | High (silent FK violation) | Phase 1 schema updated: PK split into two partial unique indexes (one for `venue_id IS NOT NULL`, one for `venue_id IS NULL`). |
| `search_path` not set in security-definer functions (security M2) | Low | Medium (privilege escalation surface) | Phase 1 explicitly sets `set search_path = public` in every security-definer function. Same pattern as 0001's existing helpers. |
| `apple_place_id` is client-supplied untrusted input (security L2) | Low | Medium | New venues created from client searches are flagged `verified=false`. Only `verified=true` venues are auto-merge eligible. Server-side reconciliation is a v1.1 backlog item. |
| Activity hierarchy used in visibility predicates by accident (architecture #4) | Low | Medium (silently broadens visibility) | Two explicit SQL helpers: `activity_matches_exact()` for visibility, `activity_matches_hierarchical()` for recommendations. Schema comment on `parent_activity_id` is a warning. |
| Test parity drift (InMemory vs Supabase implementations diverging) | Medium | High | Each protocol has a matching test in both backend test files; CI gate is full-suite green |
| Catchbook layered-location-model lessons (`docs/solutions/integration-issues/catchbook-layered-location-model-rollout.md`) | — | — | Adopted: explicit semantic contract for what each coordinate means before coding. Venue lat/lng = canonical place; user device location = never collected. |
| Multi-phase shipping anti-patterns (`docs/solutions/architecture/multi-phase-plan-shipping-primitives-skills.md`) | — | — | Adopted: each phase commits independently; CI gate is green tests; convention compliance verified before moving forward |
| Old onboarding entry point left active after refactor (`docs/solutions/integration-issues/waterbody-optional-refactor.md`) | Low | Medium | Onboarding refactor in Phase 4 deletes the old single-carousel `OnboardingView` body; the new coordinator is the only entry point |

## Resource Requirements

- **Time**: 8 phases, roughly 1–2 days of focused work each. Total
  estimate: 10–14 days for a single engineer with no other interruptions.
  Phases are independently shippable; can pause between any two.
- **Infrastructure**: existing local Supabase (Docker), Xcode, simulator.
  No new spend.
- **Tooling**: existing test harness, no new dependencies. Apple
  MKLocalSearch is part of `MapKit` (already in iOS).

## Future Considerations

Items deferred to v1.0.1 / v1.1 / v2:

- **Phone contacts as a Factor 2 closeness input** (opt-in)
- **Social-graph linking** (Facebook, Instagram via OAuth)
- **3rd-degree closeness signals**
- **Sub-context splitting by time/day pattern**
- **Denormalized `closeness_scores` table** for feed-load latency
- **Recommendation surface for "people who frequent the same venue"**
  (separate from "friends of friends")
- **Activity taxonomy expansion via user-suggested entries** with
  founder moderation
- **Venue merging tooling** for freeform venues that turn out to be the
  same physical place
- **Telemetry** to instrument the success metrics above
- **Reconciliation tooling** for cross-locale Apple Place ID drift

## Documentation Plan

- This plan + the brainstorm document (already written).
- `docs/products/after-plans/PHASE_STATUS.md` — phase entries added per
  phase landed.
- `docs/products/after-plans/remaining-steps-before-ios-submission.md`
  — readiness counts refreshed once all phases land.
- `docs/products/after-plans/api/CONTRACT.md` — extended to cover the
  new operations (activities, venues, interests, recommendations,
  push registration).
- `infra/supabase/README.md` — note about the new tables and helpers
  added in 0002 / 0003.
- `docs/products/after-plans/legal/PRIVACY_POLICY.md` and
  `APP_STORE_METADATA_DRAFT.md` — venue-address disclosure (Phase 8).
- A new `docs/products/after-plans/manual-qa-pass.md` section covering
  the new onboarding + public-plan + auto-context flows (extends the
  existing QA pass doc).

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-04-27-after-plans-context-model-brainstorm.md](../brainstorms/2026-04-27-after-plans-context-model-brainstorm.md)
  — captures all 13 locked decisions, the alternatives considered and
  rejected, and the open questions deferred to v2.

### Internal references

- Current schema: [infra/supabase/migrations/0001_init.sql](../../infra/supabase/migrations/0001_init.sql)
- iOS adapter: [products/after-plans-ios/Sources/Services/SupabaseBackend.swift](../../products/after-plans-ios/Sources/Services/SupabaseBackend.swift)
- In-memory adapter: [products/after-plans-ios/Sources/Services/InMemoryBackend.swift](../../products/after-plans-ios/Sources/Services/InMemoryBackend.swift)
- Network protocols: [products/after-plans-ios/Sources/Services/NetworkProtocols.swift](../../products/after-plans-ios/Sources/Services/NetworkProtocols.swift)
- Domain models: [products/after-plans-ios/Sources/Models/AfterPlansModels.swift](../../products/after-plans-ios/Sources/Models/AfterPlansModels.swift)
- Current onboarding view: [products/after-plans-ios/Sources/Features/Onboarding/OnboardingView.swift](../../products/after-plans-ios/Sources/Features/Onboarding/OnboardingView.swift)
- Backend contract: [docs/products/after-plans/api/CONTRACT.md](../products/after-plans/api/CONTRACT.md)
- Founder decisions: [docs/products/after-plans/founder-decisions-needed.md](../products/after-plans/founder-decisions-needed.md)
  — section 3 (launch contexts) deferred pending this brainstorm.

### Institutional learnings carried forward

- [docs/solutions/integration-issues/catchbook-layered-location-model-rollout.md](../solutions/integration-issues/catchbook-layered-location-model-rollout.md)
  — semantic contract for layered location models. Adopted: clear
  separation between venue-canonical-location (what we collect) and
  user-device-location (which we don't).
- [docs/solutions/architecture/multi-phase-plan-shipping-primitives-skills.md](../solutions/architecture/multi-phase-plan-shipping-primitives-skills.md)
  — multi-phase shipping discipline. Adopted: each phase ships
  independently with CI-green stop conditions.
- [docs/solutions/integration-issues/plan-deepening-apply-verify-loop-2026-04-15.md](../solutions/integration-issues/plan-deepening-apply-verify-loop-2026-04-15.md)
  — deepening loop. Recommend running `/deepen-plan` against this plan
  before Phase 1 execution to surface anything else.
- [docs/solutions/integration-issues/waterbody-optional-refactor.md](../solutions/integration-issues/waterbody-optional-refactor.md)
  — gate-removal anti-pattern. Adopted: Phase 4 deletes the old
  single-carousel onboarding entry point in the same commit it lands the
  multi-step coordinator.
- [docs/brainstorms/2026-04-11-catchbook-location-model-brainstorm.md](../brainstorms/2026-04-11-catchbook-location-model-brainstorm.md)
  — prior thinking on layered location models from Catchbook.
  Cross-product reference; not directly load-bearing but useful background.

### External references

- Apple MKLocalSearch:
  https://developer.apple.com/documentation/mapkit/mklocalsearch
- Supabase RLS:
  https://supabase.com/docs/guides/auth/row-level-security
- Supabase Edge Functions:
  https://supabase.com/docs/guides/functions
- Postgres advisory locks:
  https://www.postgresql.org/docs/15/explicit-locking.html#ADVISORY-LOCKS
- supabase-swift:
  https://github.com/supabase/supabase-swift

### Related work in this repo

- The C1 backend slice that proved the SupabaseBackend wire path
  (commit `a81e114`).
- The hardened `currentUser()` race-fix (commit `90d2348`) — pattern
  reused for any new identity-dependent calls.
- The legal docs published to GitHub Pages mirrors (commit `653b964`)
  — Phase 8 syncs the privacy posture update there.
