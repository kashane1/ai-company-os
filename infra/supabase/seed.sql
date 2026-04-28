-- Local-dev seed for After Plans.
-- Mirrors the InMemoryServices seed so a developer running `supabase start`
-- and pointing the iOS app at the local instance sees the same starting state
-- as the in-memory backend.
--
-- This file is loaded automatically by `supabase db reset`.

-- Seed contexts ------------------------------------------------------------
insert into public.contexts (id, type, title, venue_name, trust_note) values
    ('11111111-1111-1111-1111-111111111111', 'class_session', 'Pottery Night',           'Clay House Studio', 'People leaving this class should see each other first.'),
    ('22222222-2222-2222-2222-222222222222', 'community',     'Wednesday Run Club',      'Civic Track',       'Same-route regulars outrank broader city discovery.'),
    ('33333333-3333-3333-3333-333333333333', 'meetup',        'Downtown Product Meetup', 'Pier Hall',         'Visible to people who just shared the meetup context.')
on conflict (id) do nothing;

-- Seed reports reasons table is omitted because reasons are returned from a
-- server-side constant in v1; see contract `report_reasons()`.

-- Note: profiles, plans, and participants are not seeded here because they
-- depend on real auth.users rows and the local auth flow. Use the iOS dev
-- build with `enable_anonymous_sign_ins = true` to populate them organically.
