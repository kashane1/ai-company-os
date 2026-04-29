-- Local-dev seed for After Plans.
-- Mirrors the InMemoryServices seed so a developer running `supabase start`
-- and pointing the iOS app at the local instance sees the same starting state
-- as the in-memory backend.
--
-- This file is loaded automatically by `supabase db reset`.

-- Seed contexts ------------------------------------------------------------
-- Kept from the original seed. Inert anonymous data; safe to leave in place
-- alongside the new activity-taxonomy + auto-context-formation model.
insert into public.contexts (id, type, title, venue_name, trust_note) values
    ('11111111-1111-1111-1111-111111111111', 'class_session', 'Pottery Night',           'Clay House Studio', 'People leaving this class should see each other first.'),
    ('22222222-2222-2222-2222-222222222222', 'community',     'Wednesday Run Club',      'Civic Track',       'Same-route regulars outrank broader city discovery.'),
    ('33333333-3333-3333-3333-333333333333', 'meetup',        'Downtown Product Meetup', 'Pier Hall',         'Visible to people who just shared the meetup context.')
on conflict (id) do nothing;

-- Seed activity taxonomy --------------------------------------------------
-- Founder-curated, ~30 entries. Includes both specific activities (basketball,
-- soccer) and broader category buckets (sports, fitness, creative). The
-- broader buckets are linked via parent_activity_id and are used ONLY for
-- recommendation queries — visibility predicates use exact activity match.
--
-- Stable UUIDs are used so the iOS taxonomy in ActivityTaxonomy.swift can
-- pin to specific IDs across dev environments.

-- Parent / category buckets first (so children can FK them).
insert into public.activities (id, slug, title, icon_system_name, parent_activity_id, sort_rank) values
    ('a0000000-0000-0000-0000-000000000001', 'sports',        'Sports',           'figure.run',                       null, 10),
    ('a0000000-0000-0000-0000-000000000002', 'fitness',       'Fitness',          'figure.strengthtraining.traditional', null, 20),
    ('a0000000-0000-0000-0000-000000000003', 'creative',      'Creative',         'paintbrush',                       null, 30),
    ('a0000000-0000-0000-0000-000000000004', 'social',        'Social',           'person.2',                         null, 40),
    ('a0000000-0000-0000-0000-000000000005', 'outdoors',      'Outdoors',         'leaf',                             null, 50),
    ('a0000000-0000-0000-0000-000000000006', 'community',     'Community',        'person.3',                         null, 60)
on conflict (slug) do nothing;

-- Specific activities under sports
insert into public.activities (id, slug, title, icon_system_name, parent_activity_id, sort_rank) values
    ('a1000000-0000-0000-0000-000000000001', 'basketball',    'Basketball',       'basketball',                       'a0000000-0000-0000-0000-000000000001', 110),
    ('a1000000-0000-0000-0000-000000000002', 'soccer',        'Soccer',           'soccerball',                       'a0000000-0000-0000-0000-000000000001', 120),
    ('a1000000-0000-0000-0000-000000000003', 'baseball',      'Baseball',         'baseball',                         'a0000000-0000-0000-0000-000000000001', 130),
    ('a1000000-0000-0000-0000-000000000004', 'tennis',        'Tennis',           'tennis.racket',                    'a0000000-0000-0000-0000-000000000001', 140),
    ('a1000000-0000-0000-0000-000000000005', 'volleyball',    'Volleyball',       'volleyball',                       'a0000000-0000-0000-0000-000000000001', 150),
    ('a1000000-0000-0000-0000-000000000006', 'pickleball',    'Pickleball',       'tennis.racket',                    'a0000000-0000-0000-0000-000000000001', 160)
on conflict (slug) do nothing;

-- Specific activities under fitness
insert into public.activities (id, slug, title, icon_system_name, parent_activity_id, sort_rank) values
    ('a2000000-0000-0000-0000-000000000001', 'run',           'Run',              'figure.run',                       'a0000000-0000-0000-0000-000000000002', 210),
    ('a2000000-0000-0000-0000-000000000002', 'walk',          'Walk',             'figure.walk',                      'a0000000-0000-0000-0000-000000000002', 220),
    ('a2000000-0000-0000-0000-000000000003', 'bike',          'Bike',             'bicycle',                          'a0000000-0000-0000-0000-000000000002', 230),
    ('a2000000-0000-0000-0000-000000000004', 'yoga',          'Yoga',             'figure.yoga',                      'a0000000-0000-0000-0000-000000000002', 240),
    ('a2000000-0000-0000-0000-000000000005', 'pilates',       'Pilates',          'figure.pilates',                   'a0000000-0000-0000-0000-000000000002', 250),
    ('a2000000-0000-0000-0000-000000000006', 'climb',         'Climb',            'figure.climbing',                  'a0000000-0000-0000-0000-000000000002', 260),
    ('a2000000-0000-0000-0000-000000000007', 'gym',           'Gym',              'dumbbell',                         'a0000000-0000-0000-0000-000000000002', 270)
on conflict (slug) do nothing;

-- Specific activities under creative
insert into public.activities (id, slug, title, icon_system_name, parent_activity_id, sort_rank) values
    ('a3000000-0000-0000-0000-000000000001', 'pottery',       'Pottery',          'cup.and.saucer',                   'a0000000-0000-0000-0000-000000000003', 310),
    ('a3000000-0000-0000-0000-000000000002', 'art_class',     'Art Class',        'paintbrush.pointed',               'a0000000-0000-0000-0000-000000000003', 320),
    ('a3000000-0000-0000-0000-000000000003', 'music',         'Music',            'music.note',                       'a0000000-0000-0000-0000-000000000003', 330),
    ('a3000000-0000-0000-0000-000000000004', 'writing',       'Writing',          'pencil.and.outline',               'a0000000-0000-0000-0000-000000000003', 340),
    ('a3000000-0000-0000-0000-000000000005', 'photography',   'Photography',      'camera',                           'a0000000-0000-0000-0000-000000000003', 350)
on conflict (slug) do nothing;

-- Specific activities under social
insert into public.activities (id, slug, title, icon_system_name, parent_activity_id, sort_rank) values
    ('a4000000-0000-0000-0000-000000000001', 'coffee',        'Coffee',           'cup.and.saucer.fill',              'a0000000-0000-0000-0000-000000000004', 410),
    ('a4000000-0000-0000-0000-000000000002', 'dinner',        'Dinner',           'fork.knife',                       'a0000000-0000-0000-0000-000000000004', 420),
    ('a4000000-0000-0000-0000-000000000003', 'drinks',        'Drinks',           'wineglass',                        'a0000000-0000-0000-0000-000000000004', 430),
    ('a4000000-0000-0000-0000-000000000004', 'brunch',        'Brunch',           'sun.and.horizon',                  'a0000000-0000-0000-0000-000000000004', 440),
    ('a4000000-0000-0000-0000-000000000005', 'board_games',   'Board Games',      'die.face.5',                       'a0000000-0000-0000-0000-000000000004', 450),
    ('a4000000-0000-0000-0000-000000000006', 'book_club',     'Book Club',        'book',                             'a0000000-0000-0000-0000-000000000004', 460)
on conflict (slug) do nothing;

-- Specific activities under outdoors
insert into public.activities (id, slug, title, icon_system_name, parent_activity_id, sort_rank) values
    ('a5000000-0000-0000-0000-000000000001', 'hike',          'Hike',             'mountain.2',                       'a0000000-0000-0000-0000-000000000005', 510),
    ('a5000000-0000-0000-0000-000000000002', 'beach',         'Beach',            'beach.umbrella',                   'a0000000-0000-0000-0000-000000000005', 520),
    ('a5000000-0000-0000-0000-000000000003', 'park',          'Park',             'tree',                             'a0000000-0000-0000-0000-000000000005', 530),
    ('a5000000-0000-0000-0000-000000000004', 'dog_walk',      'Dog Walk',         'dog',                              'a0000000-0000-0000-0000-000000000005', 540)
on conflict (slug) do nothing;

-- Specific activities under community
insert into public.activities (id, slug, title, icon_system_name, parent_activity_id, sort_rank) values
    ('a6000000-0000-0000-0000-000000000001', 'church',        'Church',           'building.columns',                 'a0000000-0000-0000-0000-000000000006', 610),
    ('a6000000-0000-0000-0000-000000000002', 'meetup',        'Meetup',           'person.3.sequence',                'a0000000-0000-0000-0000-000000000006', 620),
    ('a6000000-0000-0000-0000-000000000003', 'study',         'Study',            'graduationcap',                    'a0000000-0000-0000-0000-000000000006', 630),
    ('a6000000-0000-0000-0000-000000000004', 'coworking',     'Coworking',        'laptopcomputer',                   'a0000000-0000-0000-0000-000000000006', 640),
    ('a6000000-0000-0000-0000-000000000005', 'kids_playdate', 'Kids Playdate',    'figure.and.child.holdinghands',    'a0000000-0000-0000-0000-000000000006', 650)
on conflict (slug) do nothing;

-- Note: profiles, plans, participants, venues, and user_activity_interests
-- are not seeded here because they depend on real auth.users rows and the
-- live MKLocalSearch venue picker. Use the iOS dev build with anonymous
-- sign-ins to populate them organically.
