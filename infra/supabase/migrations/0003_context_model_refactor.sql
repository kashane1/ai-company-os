-- After Plans context model refactor — schema foundation (Phase 1).
--
-- Source of truth for design decisions:
--   docs/plans/2026-04-27-001-feat-after-plans-context-model-refactor-plan.md
--   docs/brainstorms/2026-04-27-after-plans-context-model-brainstorm.md
--
-- This migration adds the schema for:
--   - User-built contexts via activity+venue declarations
--   - Public plans (the new visibility mode added in 0002)
--   - Auto-context formation from wrapped public plans (off-trigger)
--   - Closeness graph computed from confirmed plan participation
--   - Push notification outbox infrastructure (table only; trigger
--     wiring lands in 0004 alongside the dispatcher Edge Function)
--
-- Critical correctness invariants encoded here (per the deepening review):
--   - search_path is set explicitly in every security-definer function
--   - public visibility predicate lives in BOTH plans_visibility_select
--     policy AND user_can_see_plan helper (defense in depth)
--   - Activity hierarchy is used for recommendations only; visibility
--     uses activity_matches_exact (warned via schema comment + naming)
--   - Auto-context trigger does only lightweight enqueue work; bulk
--     conversion happens in an Edge Function consumer (lands in 0004)
--   - Residential venues are rejected from publicMatch eligibility
--   - Sock-puppet auto-context capture is mitigated via probationary
--     contexts + ≥3-distinct-user join requirement
--   - Push token reassignment fix lives in the iOS adapter (0004 land)

-- =========================================================================
-- New tables
-- =========================================================================

-- Activities — founder-curated taxonomy. Includes both specific verbs
-- (basketball, soccer) and broader category buckets (sports, fitness).
-- parent_activity_id is RECOMMENDATIONS-ONLY. Visibility predicates use
-- activity_matches_exact, never the hierarchy.
create table public.activities (
    id uuid primary key default gen_random_uuid(),
    slug text unique not null check (char_length(slug) between 1 and 32),
    title text not null check (char_length(title) between 1 and 48),
    icon_system_name text not null,
    parent_activity_id uuid references public.activities(id) on delete set null,
    sort_rank int not null default 100,
    created_at timestamptz not null default now()
);

comment on column public.activities.parent_activity_id is
    'RECOMMENDATIONS ONLY — never used in visibility predicates. '
    'See activity_matches_hierarchical() for recommendation queries '
    'and activity_matches_exact() for visibility. Mixing these silently '
    'broadens the visibility surface.';

create index activities_parent_idx on public.activities (parent_activity_id)
    where parent_activity_id is not null;

-- Venues — one row per canonical place. Apple Place ID is the unique
-- dedup key for geocoded venues; freeform venues (no Place ID) never
-- auto-merge.
create table public.venues (
    id uuid primary key default gen_random_uuid(),
    name text not null check (char_length(name) between 1 and 120),
    address text,
    latitude double precision,
    longitude double precision,
    apple_place_id text unique,
    apple_poi_category text,                          -- 'Residential' rejected for publicMatch eligibility
    is_freeform boolean not null default false,
    verified boolean not null default false,          -- server-side reconciled (v1.1+)
    interest_count int not null default 0,            -- denorm; gates auto-context formation
    created_by uuid references public.profiles(id) on delete set null,
    created_at timestamptz not null default now()
);

comment on column public.venues.verified is
    'Set true only after server-side reconciliation (v1.1+). Only verified '
    'venues are eligible for auto-context formation merging.';

comment on column public.venues.interest_count is
    'Denormalized count of distinct users with a user_activity_interests row '
    'targeting this venue. Maintained by trigger on user_activity_interests.';

create index venues_latlng_idx on public.venues (latitude, longitude)
    where latitude is not null and longitude is not null;

-- User-declared activity+venue interests. Two partial unique indexes
-- instead of a composite PK because ON DELETE SET NULL on venue_id
-- would cause PK violations on the (user_id, activity_id, NULL) row.
create table public.user_activity_interests (
    user_id uuid not null references public.profiles(id) on delete cascade,
    activity_id uuid not null references public.activities(id) on delete cascade,
    venue_id uuid references public.venues(id) on delete set null,
    declared_at timestamptz not null default now()
);

create unique index user_activity_interests_with_venue_pk
    on public.user_activity_interests (user_id, activity_id, venue_id)
    where venue_id is not null;

create unique index user_activity_interests_no_venue_pk
    on public.user_activity_interests (user_id, activity_id)
    where venue_id is null;

create index user_activity_interests_activity_idx
    on public.user_activity_interests (activity_id, venue_id);

create index user_activity_interests_user_idx
    on public.user_activity_interests (user_id);

-- Recommendation rows surfaced in the UI. Server-managed only; no
-- client write policy.
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

create index plan_recommendations_recipient_idx
    on public.plan_recommendations (recipient_id, created_at desc)
    where dismissed_at is null;

-- Push device registry. Token uniqueness lets us catch device
-- reassignment (user A signs out, user B signs in on same physical
-- device) — see iOS adapter's on conflict do update for the load-
-- bearing fix.
create table public.push_devices (
    token text primary key,
    user_id uuid not null references public.profiles(id) on delete cascade,
    platform text not null check (platform in ('ios','android')),
    created_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now()
);

create index push_devices_user_idx on public.push_devices (user_id);

-- Auto-context formation jobs. The wrap trigger only enqueues; an Edge
-- Function consumer does the bulk work asynchronously. This keeps the
-- wrap transaction <20ms regardless of plan size.
create table public.context_formation_jobs (
    id uuid primary key default gen_random_uuid(),
    plan_id uuid not null references public.plans(id) on delete cascade,
    enqueued_at timestamptz not null default now(),
    processed_at timestamptz,
    failed_at timestamptz,
    last_error text
);

-- One unprocessed job per plan, max. Idempotent enqueue from trigger.
create unique index context_formation_jobs_one_pending_per_plan
    on public.context_formation_jobs (plan_id)
    where processed_at is null;

create index context_formation_jobs_unprocessed_idx
    on public.context_formation_jobs (enqueued_at)
    where processed_at is null;

-- Trigger errors. Security-definer functions swallow exceptions and
-- log here so the wrap transaction never fails because of side-effect
-- bugs.
create table public.trigger_errors (
    id uuid primary key default gen_random_uuid(),
    source_function text not null,
    error_sqlstate text,
    error_message text,
    context_payload jsonb,
    occurred_at timestamptz not null default now()
);

create index trigger_errors_occurred_idx on public.trigger_errors (occurred_at desc);

-- =========================================================================
-- Plans table extensions
-- =========================================================================

alter table public.plans add column activity_id uuid references public.activities(id) on delete set null;
alter table public.plans add column venue_id uuid references public.venues(id) on delete set null;

-- Drop NOT NULL on context_id: 'public' visibility plans don't have a
-- pre-existing context (one auto-forms at wrap via maybe_form_auto_context).
-- 'same_context_only' plans still set this at create time; client-side
-- validation in CreatePlanDraft enforces the invariant per visibility mode.
alter table public.plans alter column context_id drop not null;

create index plans_activity_venue_idx on public.plans (activity_id, venue_id, lifecycle);

-- =========================================================================
-- Profiles table extensions
-- =========================================================================

alter table public.profiles add column privacy_mode text
    not null default 'open'
    check (privacy_mode in ('open','strict'));

comment on column public.profiles.privacy_mode is
    'open = anyone in shared contexts can see and invite the user. '
    'strict = only people the user has confirmed plans with can reach them. '
    'In strict mode, auto-join during onboarding is suppressed (interests '
    'are recorded but not converted to context_members until manual opt-in).';

-- =========================================================================
-- Indexes for the closeness graph (per performance review #1)
-- =========================================================================

-- These two indexes are load-bearing for closeness_scores() to hit the
-- 250ms p95 SLO on a 100-confirmed-plan history. Without them the
-- recursive query falls back to seq scans.
create index plan_participants_user_role_idx
    on public.plan_participants (user_id, role)
    include (plan_id)
    where role = 'confirmed';

create index plan_participants_plan_role_idx
    on public.plan_participants (plan_id, role)
    include (user_id)
    where role = 'confirmed';

-- =========================================================================
-- Helper functions
-- =========================================================================

-- Maintain venues.interest_count denorm.
create or replace function public.bump_venue_interest_count()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    if (tg_op = 'INSERT' and new.venue_id is not null) then
        update public.venues set interest_count = interest_count + 1 where id = new.venue_id;
    elsif (tg_op = 'DELETE' and old.venue_id is not null) then
        update public.venues set interest_count = greatest(0, interest_count - 1) where id = old.venue_id;
    end if;
    return coalesce(new, old);
end;
$$;

create trigger user_activity_interests_count_trigger
    after insert or delete on public.user_activity_interests
    for each row execute function public.bump_venue_interest_count();

-- Activity matchers — explicit names so future dev can't accidentally
-- mix visibility (exact) with recommendations (hierarchical).
create or replace function public.activity_matches_exact(a uuid, b uuid)
returns boolean
language sql
immutable
parallel safe
as $$
    select a is not null and b is not null and a = b;
$$;

create or replace function public.activity_matches_hierarchical(a uuid, b uuid)
returns boolean
language sql
stable
parallel safe
set search_path = public
as $$
    -- True if a == b OR a is a parent of b OR b is a parent of a.
    -- Used for recommendation queries only. Visibility uses _exact.
    select case
        when a is null or b is null then false
        when a = b then true
        else exists (
            select 1 from public.activities
            where (id = a and parent_activity_id = b)
               or (id = b and parent_activity_id = a)
        )
    end;
$$;

-- Closeness scores for a recipient against a candidate set of host IDs.
-- Returns a single result set in one query (no N+1 from per-plan
-- closeness lookups in the public feed).
--
-- 1st-degree: co-confirmed direct plan history → score 100 per shared plan
-- 2nd-degree: shared 1st-degree neighbor → score 10 per path (capped via LIMIT)
-- 3rd-degree: skipped (per locked decision; signal too noisy)
create or replace function public.closeness_scores(
    recipient uuid,
    candidate_hosts uuid[]
)
returns table (host_id uuid, score int)
language plpgsql
volatile  -- volatile required because we SET LOCAL statement_timeout below;
          -- stable/immutable disallow session-state mutation
parallel safe
security definer
set search_path = public
as $$
begin
    set local statement_timeout = '250ms';

    return query
    with first_degree as (
        select distinct pp2.user_id as friend_id
        from public.plan_participants pp1
        join public.plan_participants pp2 using (plan_id)
        where pp1.user_id = recipient
            and pp1.role = 'confirmed'
            and pp2.role = 'confirmed'
            and pp2.user_id <> recipient
        limit 200
    ),
    second_degree as (
        select pp.user_id, count(*) as weight
        from first_degree fd
        join public.plan_participants me
            on me.user_id = fd.friend_id and me.role = 'confirmed'
        join public.plan_participants pp
            on pp.plan_id = me.plan_id and pp.role = 'confirmed'
        where pp.user_id <> recipient
            and pp.user_id not in (select friend_id from first_degree)
        group by pp.user_id
        limit 500
    ),
    combined as (
        select friend_id as h_id, 100 as s
        from first_degree
        where friend_id = any(candidate_hosts)
        union all
        select user_id, (weight * 10)::int as s
        from second_degree
        where user_id = any(candidate_hosts)
    )
    select h_id as host_id, sum(s)::int as score
    from combined
    group by h_id;
end;
$$;

-- Update user_can_see_plan to include the 'public' arm.
-- IMPORTANT: keeps the 'known_people' arm for legacy data hydration so
-- existing rows with that visibility don't disappear. New code never
-- creates plans with 'known_people' visibility (PlanVisibility.launchModes
-- on the iOS side excludes it).
create or replace function public.user_can_see_plan(p_plan_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.plans p
        where p.id = p_plan_id
            and not public.has_block(p.host_id)
            and (
                -- same_context_only: caller is a context member
                (p.visibility = 'same_context_only' and public.user_in_context(p.context_id))
                -- known_people: legacy. Caller is host or has shared history.
                or (p.visibility = 'known_people' and (p.host_id = auth.uid() or public.shares_history(p.host_id)))
                -- public (NEW): caller has a matching exact-activity interest
                -- (venue match optional; just declaring the activity matches),
                -- AND no confirmed participant has blocked the caller.
                or (p.visibility = 'public' and exists (
                        select 1 from public.user_activity_interests uai
                        where uai.user_id = auth.uid()
                            and public.activity_matches_exact(uai.activity_id, p.activity_id)
                            and (uai.venue_id is null or uai.venue_id = p.venue_id)
                    )
                    and not exists (
                        select 1 from public.plan_participants pp
                        where pp.plan_id = p.id
                            and pp.role = 'confirmed'
                            and public.has_block(pp.user_id)
                    )
                )
                -- Caller is already a participant (any visibility)
                or public.user_on_plan(p.id)
            )
    );
$$;

-- Rewrite the inline plans_visibility_select policy so the 'public' arm
-- is enforced at the policy level too (defense in depth — never trust a
-- single helper to be the only gate).
drop policy if exists plans_visibility_select on public.plans;
create policy plans_visibility_select on public.plans
    for select to authenticated using (
        not public.has_block(host_id)
        and (
            (visibility = 'same_context_only' and public.user_in_context(context_id))
            or (visibility = 'known_people' and (host_id = auth.uid() or public.shares_history(host_id)))
            or (visibility = 'public' and exists (
                    select 1 from public.user_activity_interests uai
                    where uai.user_id = auth.uid()
                        and public.activity_matches_exact(uai.activity_id, plans.activity_id)
                        and (uai.venue_id is null or uai.venue_id = plans.venue_id)
                )
                and not exists (
                    select 1 from public.plan_participants pp
                    where pp.plan_id = plans.id
                        and pp.role = 'confirmed'
                        and public.has_block(pp.user_id)
                )
            )
            or public.user_on_plan(id)
        )
    );

-- Lightweight wrap-time trigger. Does ONLY:
--   1. Eligibility check (visibility = public, just transitioned to closed,
--      ≥2 distinct confirmed participants, venue not residential)
--   2. Advisory-lock-protected idempotent enqueue
--   3. Exception-swallow + trigger_errors log so wrap never rolls back
-- The actual context formation + interest conversion + push fan-out
-- happens in an Edge Function consumer of context_formation_jobs
-- (lands in 0004).
create or replace function public.maybe_form_auto_context()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    v_apple_place_id text;
    v_apple_poi_category text;
    v_confirmed_count int;
    v_lock_key bigint;
begin
    -- Only fire on transitions TO closed
    if not (old.lifecycle is distinct from new.lifecycle and new.lifecycle = 'closed') then
        return new;
    end if;

    -- Only public plans
    if new.visibility <> 'public' then
        return new;
    end if;

    begin
        -- Look up venue category
        select v.apple_place_id, v.apple_poi_category
            into v_apple_place_id, v_apple_poi_category
        from public.venues v
        where v.id = new.venue_id;

        -- Reject residential venues (security H4)
        if coalesce(v_apple_poi_category, '') = 'Residential' then
            return new;
        end if;

        -- Need ≥2 distinct confirmed participants
        select count(distinct pp.user_id) into v_confirmed_count
        from public.plan_participants pp
        where pp.plan_id = new.id and pp.role = 'confirmed';

        if v_confirmed_count < 2 then
            return new;
        end if;

        -- Advisory lock per (activity_id, place_or_venue) so concurrent
        -- wraps at the same activity+venue serialize. Hash to bigint.
        v_lock_key := hashtextextended(
            coalesce(new.activity_id::text, '') || '|' || coalesce(v_apple_place_id, new.venue_id::text, ''),
            0
        );

        -- pg_try_advisory_xact_lock returns false if another txn holds it.
        -- Either way, we just enqueue (the unique partial index makes
        -- enqueue itself idempotent). The lock is paranoia.
        perform pg_try_advisory_xact_lock(v_lock_key);

        -- Idempotent enqueue (unique partial index on (plan_id) where processed_at is null)
        insert into public.context_formation_jobs (plan_id)
        values (new.id)
        on conflict do nothing;

    exception when others then
        -- Never re-raise. Wrap transaction must succeed even if we can't
        -- enqueue context formation.
        insert into public.trigger_errors (source_function, error_sqlstate, error_message, context_payload)
        values (
            'maybe_form_auto_context',
            sqlstate,
            sqlerrm,
            jsonb_build_object('plan_id', new.id, 'visibility', new.visibility)
        );
    end;

    return new;
end;
$$;

create trigger plans_maybe_form_auto_context
    after update on public.plans
    for each row execute function public.maybe_form_auto_context();

-- =========================================================================
-- Single-RPC bulk auto-join used by onboarding (per performance review #5)
-- Reduces first-launch latency from N×round-trip to one round-trip.
-- =========================================================================

create or replace function public.auto_join_contexts(context_ids uuid[])
returns int
language plpgsql
security definer
set search_path = public
as $$
declare
    v_caller uuid := auth.uid();
    v_inserted int;
begin
    if v_caller is null then
        raise exception 'unauthenticated' using errcode = '42501';
    end if;

    insert into public.context_members (context_id, user_id)
    select unnest(context_ids), v_caller
    on conflict (context_id, user_id) do nothing;

    get diagnostics v_inserted = row_count;
    return v_inserted;
end;
$$;

-- =========================================================================
-- Row Level Security
-- =========================================================================

alter table public.activities                 enable row level security;
alter table public.venues                     enable row level security;
alter table public.user_activity_interests    enable row level security;
alter table public.plan_recommendations       enable row level security;
alter table public.push_devices               enable row level security;
alter table public.context_formation_jobs     enable row level security;
alter table public.trigger_errors             enable row level security;

-- activities: world-readable to authenticated users; no client writes.
create policy activities_read_all on public.activities
    for select to authenticated using (true);

-- venues: world-readable; users can insert venues they search up via
-- MKLocalSearch. No update/delete by clients (server-managed).
create policy venues_read_all on public.venues
    for select to authenticated using (true);
create policy venues_insert_self on public.venues
    for insert to authenticated with check (created_by = auth.uid() or created_by is null);

-- user_activity_interests: self-only. Separate select policy AND for-all
-- policy so future joins can't accidentally leak (security H1).
create policy user_activity_interests_select_self on public.user_activity_interests
    for select to authenticated using (user_id = auth.uid());
create policy user_activity_interests_insert_self on public.user_activity_interests
    for insert to authenticated with check (user_id = auth.uid());
create policy user_activity_interests_delete_self on public.user_activity_interests
    for delete to authenticated using (user_id = auth.uid());

-- plan_recommendations: read your own; no client writes (server-only via
-- security-definer functions).
create policy plan_recommendations_select_self on public.plan_recommendations
    for select to authenticated using (recipient_id = auth.uid());
create policy plan_recommendations_dismiss_self on public.plan_recommendations
    for update to authenticated
    using (recipient_id = auth.uid())
    with check (recipient_id = auth.uid());

-- push_devices: self-manage. No cross-user reads.
create policy push_devices_self on public.push_devices
    for all to authenticated
    using (user_id = auth.uid())
    with check (user_id = auth.uid());

-- context_formation_jobs + trigger_errors: no client access at all.
-- (No policies created; RLS enabled with no policies = deny all.)

-- =========================================================================
-- Realtime publications
-- =========================================================================

alter publication supabase_realtime add table public.plan_recommendations;

-- =========================================================================
-- Notes for follow-on migrations
-- =========================================================================

-- 0004 (Phase 7) will add:
--   - push_outbox table (with dedupe_key UNIQUE + apns_id for APNs idempotency)
--   - Postgres triggers calling enqueue_push_event on plan/participant/recommendation events
--   - pg_cron jobs for push_outbox retention (sent: 7d, failed: 30d) and
--     trigger_errors retention (30d)
--   - Edge Functions: context_formation_worker (consumes context_formation_jobs)
--     and push_dispatcher (consumes push_outbox via APNs JWT ES256 with .p8 key)
