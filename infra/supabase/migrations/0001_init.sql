-- After Plans v1 schema.
-- Source of truth: docs/products/after-plans/api/CONTRACT.md
--
-- Design notes:
-- * Supabase auth.users supplies the identity primitive. `profiles` is a
--   1:1 extension that holds product-visible identity fields.
-- * RLS is the single enforcement layer for visibility rules. Clients never
--   re-implement them.
-- * Lifecycle and visibility are constrained enums to prevent drift.
-- * Soft writes only — closed plans stay queryable for recap / history.
-- * Aggregates that the contract surfaces as denormalized fields
--   (e.g. interested_count, host_descriptor) are kept in views, not tables.

create extension if not exists "pgcrypto";

-- Enums
create type plan_mode as enum ('default_option', 'open_intent', 'exact');
create type plan_visibility as enum ('same_context_only', 'known_people', 'invite_only', 'friends_of_participants');
create type plan_lifecycle as enum ('open', 'forming', 'confirmed', 'active', 'closed');
create type plan_participation_role as enum ('host', 'joined', 'interested', 'confirmed');
create type context_type as enum ('meetup', 'class_session', 'dinner', 'conference', 'community', 'hangout');
create type report_target as enum ('plan', 'user');
create type invite_share_channel as enum ('same_context', 'known_people', 'nearby_qr');

-- Profiles ------------------------------------------------------------------
create table public.profiles (
    id              uuid primary key references auth.users(id) on delete cascade,
    first_name      text not null check (char_length(first_name) between 1 and 24),
    visibility_default plan_visibility not null default 'same_context_only',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create index profiles_first_name_idx on public.profiles using btree (first_name);

-- Contexts ------------------------------------------------------------------
create table public.contexts (
    id              uuid primary key default gen_random_uuid(),
    type            context_type not null,
    title           text not null,
    venue_name      text,
    trust_note      text,
    created_at      timestamptz not null default now()
);

-- Per-user context membership — drives same-context visibility.
create table public.context_members (
    context_id      uuid not null references public.contexts(id) on delete cascade,
    user_id         uuid not null references public.profiles(id) on delete cascade,
    joined_at       timestamptz not null default now(),
    last_seen_at    timestamptz not null default now(),
    primary key (context_id, user_id)
);

create index context_members_user_idx on public.context_members(user_id, last_seen_at desc);

-- Plans ---------------------------------------------------------------------
create table public.plans (
    id              uuid primary key default gen_random_uuid(),
    context_id      uuid not null references public.contexts(id) on delete cascade,
    host_id         uuid not null references public.profiles(id) on delete cascade,
    title           text not null check (char_length(title) between 1 and 80),
    summary         text,
    mode            plan_mode not null,
    visibility      plan_visibility not null,
    lifecycle       plan_lifecycle not null default 'open',
    time_label      text,
    venue_label     text,
    distance_label  text,
    invite_code     text not null unique default encode(gen_random_bytes(9), 'base64'),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    closed_at       timestamptz
);

create index plans_context_idx on public.plans(context_id, lifecycle);
create index plans_host_idx on public.plans(host_id, created_at desc);
create index plans_invite_code_idx on public.plans(invite_code);

-- Plan participants ---------------------------------------------------------
create table public.plan_participants (
    plan_id         uuid not null references public.plans(id) on delete cascade,
    user_id         uuid not null references public.profiles(id) on delete cascade,
    role            plan_participation_role not null default 'joined',
    descriptor      text,
    joined_at       timestamptz not null default now(),
    primary key (plan_id, user_id)
);

create index plan_participants_user_idx on public.plan_participants(user_id);

-- Plan place suggestions ----------------------------------------------------
create table public.plan_place_suggestions (
    plan_id         uuid not null references public.plans(id) on delete cascade,
    place           text not null,
    suggested_by    uuid not null references public.profiles(id) on delete cascade,
    suggested_at    timestamptz not null default now(),
    primary key (plan_id, place)
);

-- Interest signals ----------------------------------------------------------
create table public.plan_interest (
    plan_id         uuid not null references public.plans(id) on delete cascade,
    user_id         uuid not null references public.profiles(id) on delete cascade,
    expressed_at    timestamptz not null default now(),
    primary key (plan_id, user_id)
);

-- Blocks --------------------------------------------------------------------
create table public.user_blocks (
    blocker_id      uuid not null references public.profiles(id) on delete cascade,
    blocked_id      uuid not null references public.profiles(id) on delete cascade,
    blocked_at      timestamptz not null default now(),
    primary key (blocker_id, blocked_id),
    check (blocker_id <> blocked_id)
);

-- Reports -------------------------------------------------------------------
create table public.reports (
    id              uuid primary key default gen_random_uuid(),
    reporter_id     uuid not null references public.profiles(id) on delete cascade,
    target          report_target not null,
    plan_id         uuid references public.plans(id) on delete set null,
    user_id         uuid references public.profiles(id) on delete set null,
    reason_id       text not null,
    note            text,
    created_at      timestamptz not null default now(),
    check (
        (target = 'plan' and plan_id is not null and user_id is null) or
        (target = 'user' and user_id is not null and plan_id is null)
    )
);

create index reports_target_idx on public.reports(target, created_at desc);

-- Invite share log (instrumentation only) -----------------------------------
create table public.invite_shares (
    id              uuid primary key default gen_random_uuid(),
    plan_id         uuid not null references public.plans(id) on delete cascade,
    user_id         uuid not null references public.profiles(id) on delete cascade,
    channel         invite_share_channel not null,
    shared_at       timestamptz not null default now()
);

-- updated_at triggers --------------------------------------------------------
create or replace function public.touch_updated_at() returns trigger as $$
begin
    new.updated_at := now();
    return new;
end;
$$ language plpgsql;

create trigger profiles_touch before update on public.profiles
    for each row execute function public.touch_updated_at();
create trigger plans_touch before update on public.plans
    for each row execute function public.touch_updated_at();

-- Helper: did caller share a context with target? ---------------------------
create or replace function public.shares_context(target_user uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.context_members me
        join public.context_members them
            on me.context_id = them.context_id
        where me.user_id = auth.uid()
            and them.user_id = target_user
    );
$$;

-- Helper: known-people heuristic — have caller and target ever shared a plan?
create or replace function public.shares_history(target_user uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.plan_participants me
        join public.plan_participants them
            on me.plan_id = them.plan_id
        where me.user_id = auth.uid()
            and them.user_id = target_user
            and me.user_id <> them.user_id
    );
$$;

-- Helper: is target blocked by caller, or has target blocked caller?
create or replace function public.has_block(target_user uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.user_blocks
        where (blocker_id = auth.uid() and blocked_id = target_user)
           or (blocker_id = target_user and blocked_id = auth.uid())
    );
$$;

-- Helper: is the caller a member of this context?
-- security definer so policies can call it without re-triggering RLS.
create or replace function public.user_in_context(p_context_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.context_members
        where context_id = p_context_id and user_id = auth.uid()
    );
$$;

-- Helper: is the caller a participant on this plan?
-- security definer so the plans-visibility policy can check participation
-- without triggering plan_participants RLS (which itself references plans).
create or replace function public.user_on_plan(p_plan_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.plan_participants
        where plan_id = p_plan_id and user_id = auth.uid()
    );
$$;

-- Helper: does the caller satisfy the plan's visibility rule?
-- Mirrors plans_visibility_select, but as a security-definer function so
-- dependent tables (plan_participants, plan_place_suggestions) can ask
-- "can the caller see this plan?" without re-entering RLS on plans and
-- causing 42P17 infinite recursion.
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
                (p.visibility = 'same_context_only' and public.user_in_context(p.context_id))
                or (p.visibility = 'known_people' and (p.host_id = auth.uid() or public.shares_history(p.host_id)))
                or public.user_on_plan(p.id)
            )
    );
$$;

-- =========================================================================
-- Row Level Security
-- =========================================================================

alter table public.profiles            enable row level security;
alter table public.contexts            enable row level security;
alter table public.context_members     enable row level security;
alter table public.plans               enable row level security;
alter table public.plan_participants   enable row level security;
alter table public.plan_place_suggestions enable row level security;
alter table public.plan_interest       enable row level security;
alter table public.user_blocks         enable row level security;
alter table public.reports             enable row level security;
alter table public.invite_shares       enable row level security;

-- profiles: anyone authenticated may read; users may write only their own.
create policy profiles_read_all on public.profiles
    for select to authenticated using (true);
create policy profiles_self_write on public.profiles
    for update to authenticated using (id = auth.uid()) with check (id = auth.uid());
create policy profiles_self_insert on public.profiles
    for insert to authenticated with check (id = auth.uid());

-- contexts: read for any authenticated user. Server-managed creation.
create policy contexts_read_all on public.contexts
    for select to authenticated using (true);

-- context_members: read your own membership; insert only yourself.
create policy context_members_read_self on public.context_members
    for select to authenticated using (user_id = auth.uid());
create policy context_members_join_self on public.context_members
    for insert to authenticated with check (user_id = auth.uid());

-- plans: visibility is the load-bearing rule.
-- A plan is visible to caller if all of the following:
--   * caller has not blocked host and host has not blocked caller
--   * AND visibility allows it:
--       - same_context_only → caller is a member of plan.context
--       - known_people      → caller shares a plan-history with host
--       - invite_only       → only via direct id lookup using the invite code
-- Closed plans remain visible to participants for history.
create policy plans_visibility_select on public.plans
    for select to authenticated using (
        not public.has_block(host_id)
        and (
            (visibility = 'same_context_only' and public.user_in_context(context_id))
            or (visibility = 'known_people' and (host_id = auth.uid() or public.shares_history(host_id)))
            or public.user_on_plan(id)
        )
    );

-- Hosts may insert plans.
create policy plans_host_insert on public.plans
    for insert to authenticated with check (host_id = auth.uid());

-- Hosts and confirmed participants may update lifecycle/title-side fields.
create policy plans_host_update on public.plans
    for update to authenticated using (
        host_id = auth.uid()
        or exists (
            select 1 from public.plan_participants pp
            where pp.plan_id = plans.id and pp.user_id = auth.uid() and pp.role = 'confirmed'
        )
    );

-- plan_participants: visible to anyone who can see the plan.
-- Uses user_can_see_plan (security definer) to avoid recursive RLS evaluation
-- against plans, which itself references plan_participants.
create policy plan_participants_select on public.plan_participants
    for select to authenticated using (
        public.user_can_see_plan(plan_id)
    );
create policy plan_participants_join_self on public.plan_participants
    for insert to authenticated with check (user_id = auth.uid());
create policy plan_participants_update_self on public.plan_participants
    for update to authenticated using (user_id = auth.uid());

-- plan_place_suggestions: same visibility as plan; any participant or
-- visible viewer may suggest.
create policy plan_place_suggestions_select on public.plan_place_suggestions
    for select to authenticated using (
        public.user_can_see_plan(plan_id)
    );
create policy plan_place_suggestions_insert on public.plan_place_suggestions
    for insert to authenticated with check (suggested_by = auth.uid());

-- plan_interest: viewer-only.
create policy plan_interest_self on public.plan_interest
    for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

-- user_blocks: only the blocker sees their block list.
create policy user_blocks_self on public.user_blocks
    for all to authenticated using (blocker_id = auth.uid()) with check (blocker_id = auth.uid());

-- reports: only the reporter can read their own.
create policy reports_self_read on public.reports
    for select to authenticated using (reporter_id = auth.uid());
create policy reports_self_insert on public.reports
    for insert to authenticated with check (reporter_id = auth.uid());

-- invite_shares: instrumentation only — only the user that recorded the share.
create policy invite_shares_self on public.invite_shares
    for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

-- =========================================================================
-- Realtime publications
-- =========================================================================

alter publication supabase_realtime add table public.plans;
alter publication supabase_realtime add table public.plan_participants;
alter publication supabase_realtime add table public.plan_place_suggestions;
