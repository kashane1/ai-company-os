# Supabase backend for After Plans

Reference backend implementation of the contract in
[docs/products/after-plans/api/CONTRACT.md](../../docs/products/after-plans/api/CONTRACT.md).

## What's here

| File | Purpose |
| --- | --- |
| `config.toml` | Local-dev project config — ports, auth, realtime, redirect URLs |
| `migrations/0001_init.sql` | Full v1 schema + RLS policies + realtime publications |
| `seed.sql` | Context seed mirroring `InMemoryServices` |

## Local-dev quickstart

Prerequisite: install the Supabase CLI.

```bash
brew install supabase/tap/supabase
```

Bring up local Postgres + Auth + Realtime + Studio:

```bash
cd infra            # NOT infra/supabase — the CLI looks for ./supabase/config.toml
supabase start
```

Studio runs at `http://127.0.0.1:54323`. The Postgres DB is on port `54322`,
the API on `54321`. The first start pulls ~9GB of images and takes several
minutes; subsequent starts are fast.

Local dev keys are written to `infra/supabase/.env.local` (gitignored).
Regenerate them anytime with `supabase status -o env` from `infra/`.

To reset the schema and re-apply the migration + seed:

```bash
supabase db reset
```

## Cloud deployment (manual, until the platform automates it)

After Plans is **not yet wired to a cloud Supabase project**. To go live:

1. Create a new project at https://supabase.com (free tier is fine for v1).
2. In the project dashboard:
   - Authentication → Providers → enable `Anonymous` and any social providers
     you want.
   - Authentication → URL configuration → add `afterplans://join` and
     `afterplans://` to additional redirect URLs.
3. Run the migration against the cloud project:
   ```bash
   supabase link --project-ref <your-ref>
   supabase db push
   ```
4. Capture the project URL and `anon key` and provide them to the iOS app
   via the build-time configuration described in
   [products/after-plans-ios/Sources/Services/AfterPlansConfiguration.swift](../../products/after-plans-ios/Sources/Services/AfterPlansConfiguration.swift).
5. Add the `supabase-swift` Swift Package to the iOS project (currently
   gated by `#if canImport(Supabase)` so the build does not break without
   it). Edit `products/after-plans-ios/project.yml`:

   ```yaml
   packages:
     Supabase:
       url: https://github.com/supabase/supabase-swift
       from: 2.0.0
   targets:
     AfterPlans:
       dependencies:
         - package: Supabase
   ```

   Then run `xcodegen generate` and let Xcode resolve the package.

## RLS policy summary

The policies in `0001_init.sql` enforce the visibility rules from the contract:

- **same_context_only** → caller must be a `context_members` row for the
  plan's context.
- **known_people** → caller is the host, or has shared a plan with the host
  per `shares_history()`.
- **invite_only** → never appears in `feed()`; resolved only by direct
  invite-code lookup, which is performed via a server-side function (not
  raw RLS) in production.
- **blocks** override everything via `has_block()`.
- **closed plans** stay queryable for participants only.

Server-side functions (`shares_context`, `shares_history`, `has_block`) use
`security definer` so the RLS predicates can run without recursive policy
evaluation.

## Versioning

Each migration file is numbered and never edited after merge. New schema
changes go in `0002_*.sql`, etc. The contract version in
`docs/products/after-plans/api/CONTRACT.md` is incremented for breaking
changes only.
