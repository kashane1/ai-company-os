-- 0004_push_outbox.sql
-- Phase 7: push notifications outbox + dispatch plumbing.
--
-- The outbox pattern: triggers enqueue rows; an Edge Function
-- (push_dispatcher) drains them and signs APNs tokens. Critical
-- properties:
--
--   1. Idempotency at enqueue time via UNIQUE(dedupe_key). A trigger
--      that fires twice for the "same" event collapses to a single
--      row. The dedupe_key encodes the event (e.g. plan/event/user).
--   2. Idempotency at deliver time via apns-id header reuse. APNs
--      treats apns-id as the per-notification dedupe key within ~24h.
--   3. Token re-binding (security H3): push_devices is upserted on
--      register so a device that switches users updates user_id.
--      The dispatcher re-reads push_devices.user_id at send time
--      rather than trusting the outbox snapshot.

create table if not exists public.push_outbox (
    id uuid primary key default gen_random_uuid(),
    recipient_id uuid not null references public.profiles(id) on delete cascade,
    dedupe_key text unique not null,
    apns_id uuid not null default gen_random_uuid(),
    event_type text not null,
    payload jsonb not null,
    status text not null default 'pending'
        check (status in ('pending','sent','failed','expired')),
    attempts int not null default 0,
    last_error text,
    next_attempt_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists push_outbox_pending_idx
    on public.push_outbox (next_attempt_at)
    where status = 'pending';

alter table public.push_outbox enable row level security;

-- Server-only writes; users can only read their own queue (used by the
-- in-app "delivery diagnostics" view).
create policy push_outbox_self_read on public.push_outbox
    for select to authenticated using (recipient_id = auth.uid());

-- Helper: enqueue a push event, swallowing dedupe collisions. Trigger
-- functions call this rather than inserting directly so the dedupe_key
-- contract stays in one place.
create or replace function public.enqueue_push_event(
    p_recipient_id uuid,
    p_dedupe_key text,
    p_event_type text,
    p_payload jsonb
) returns void
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
begin
    insert into public.push_outbox (recipient_id, dedupe_key, event_type, payload)
    values (p_recipient_id, p_dedupe_key, p_event_type, p_payload)
    on conflict (dedupe_key) do nothing;
exception
    when others then
        insert into public.trigger_errors (source_function, error_message)
        values ('enqueue_push_event', sqlerrm);
end;
$$;

-- Trigger: on plan_participants insert, notify the host.
create or replace function public.notify_host_of_join() returns trigger
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
declare
    v_host_id uuid;
    v_title text;
begin
    select host_id, title into v_host_id, v_title
    from public.plans where id = new.plan_id;
    if v_host_id is null or v_host_id = new.user_id then
        return new;
    end if;
    perform public.enqueue_push_event(
        v_host_id,
        format('plan:%s:event:join:user:%s', new.plan_id, new.user_id),
        'plan_join',
        jsonb_build_object('plan_id', new.plan_id, 'joiner_id', new.user_id, 'plan_title', v_title)
    );
    return new;
end;
$$;

drop trigger if exists trg_notify_host_of_join on public.plan_participants;
create trigger trg_notify_host_of_join
    after insert on public.plan_participants
    for each row
    when (new.role <> 'host')
    execute function public.notify_host_of_join();

-- Trigger: on plans lifecycle promotion to confirmed, notify all
-- joined participants.
create or replace function public.notify_confirmed() returns trigger
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
begin
    if new.lifecycle = 'confirmed' and old.lifecycle is distinct from 'confirmed' then
        insert into public.push_outbox (recipient_id, dedupe_key, event_type, payload)
        select pp.user_id,
               format('plan:%s:event:confirmed:user:%s', new.id, pp.user_id),
               'plan_confirmed',
               jsonb_build_object('plan_id', new.id, 'plan_title', new.title)
        from public.plan_participants pp
        where pp.plan_id = new.id and pp.user_id <> new.host_id
        on conflict (dedupe_key) do nothing;
    end if;
    return new;
end;
$$;

drop trigger if exists trg_notify_confirmed on public.plans;
create trigger trg_notify_confirmed
    after update of lifecycle on public.plans
    for each row execute function public.notify_confirmed();

-- auto_join_contexts: bulk insert context_members for a set of context
-- ids (per Phase 4 performance fix). Used by the iOS app at the end of
-- onboarding to avoid N round-trips. Returns the count of new rows.
create or replace function public.auto_join_contexts(p_context_ids uuid[])
returns int
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
declare
    v_count int;
begin
    with inserted as (
        insert into public.context_members (context_id, user_id)
        select unnest(p_context_ids), auth.uid()
        on conflict (context_id, user_id) do nothing
        returning *
    )
    select count(*) into v_count from inserted;
    return v_count;
end;
$$;

-- Daily prune: keep the outbox bounded.
-- Requires pg_cron; safe to drop if pg_cron isn't installed (the
-- migration still succeeds because the call is wrapped in a do-block).
do $$
begin
    if exists (select 1 from pg_extension where extname = 'pg_cron') then
        perform cron.schedule(
            'push_outbox_prune',
            '0 4 * * *',
            $$delete from public.push_outbox
              where (status = 'sent' and updated_at < now() - interval '7 days')
                 or (status = 'failed' and updated_at < now() - interval '30 days')$$
        );
    end if;
end$$;

comment on table public.push_outbox is
    'Push notification queue. Triggers enqueue rows; an Edge Function (push_dispatcher) drains them. dedupe_key prevents duplicate enqueues within an event; apns-id prevents duplicate APNs deliveries within ~24h.';
