# Handoff prompt — After Plans C1 finish + remaining submission slices

Paste everything below this line into a fresh Claude Code conversation in the
`/Users/simons/ai-company-os` working directory once Docker Desktop and the
Supabase CLI are installed.

---

You are picking up an in-flight workstream on **After Plans**, an iOS app in
this repo at `products/after-plans-ios/`. Read the orientation files below
before doing anything; the repo has substantial context you do not yet have.

## Mandatory orientation reading (in order)

1. `CLAUDE.md` — repo conventions and skill triggers
2. `docs/products/after-plans/PHASE_STATUS.md` — current state of the product
3. `docs/products/after-plans/remaining-steps-before-ios-submission.md` — the
   submission audit and what still blocks launch
4. `docs/products/after-plans/api/CONTRACT.md` — backend contract (source of
   truth for iOS / Android / Web)
5. `infra/supabase/README.md` — local Supabase setup
6. `infra/supabase/migrations/0001_init.sql` — full schema + RLS policies
7. `products/after-plans-ios/Sources/Services/NetworkProtocols.swift` — async
   protocol shapes the backend must satisfy
8. `products/after-plans-ios/Sources/Services/SupabaseBackend.swift` — the
   real adapter (gated behind `#if canImport(Supabase)`)
9. `products/after-plans-ios/Sources/Services/AfterPlansConfiguration.swift` —
   backend selection via env vars

## What is already done — DO NOT redo

- Asset catalog with placeholder app icon, AccentColor, LaunchBackground
- Privacy posture cleanup (`NSLocationWhenInUseUsageDescription` removed; no
  unused permission strings)
- Platform-neutral backend contract (`docs/products/after-plans/api/CONTRACT.md`)
- Network-shaped async protocols and `AfterPlansBackend` bundle
- `InMemoryBackend` actor with full conformance (used in tests + previews)
- `AfterPlansStore` refactored to consume `AfterPlansBackend`; action methods
  are `async`; views wrap calls in `Task { await ... }`
- 50 unit tests green (`xcodebuild test`)
- `infra/supabase/` with `config.toml`, `migrations/0001_init.sql`,
  `seed.sql`, `README.md`
- `supabase-swift` Swift Package linked in `project.yml`
- `SupabaseBackend.swift` adapter implemented for: identity (anonymous auth
  bootstrap), contexts, plan feed/get/create, join/expressInterest/
  suggestPlace/confirm/markActive/wrap, invite preview/resolve/recordShare,
  reports, blocks. **Untested against a real backend.**

## Verify your environment first

Before doing anything else, run these and report results:

```bash
which supabase && supabase --version
which docker && docker version --format '{{.Server.Version}}'
```

Both must return real values. If either fails:
- Supabase CLI: `brew install supabase/tap/supabase`
- Docker Desktop: install manually from https://www.docker.com/products/docker-desktop/
  and start it before continuing

Then verify the iOS test suite is still green:

```bash
xcodebuild test -project products/after-plans-ios/AfterPlans.xcodeproj \
  -scheme AfterPlans \
  -destination 'platform=iOS Simulator,name=iPhone 17,OS=26.4' \
  2>&1 | grep -E "Executed [0-9]+ tests|TEST SUCCEEDED|TEST FAILED" | tail -5
```

Expect 50 tests, 0 failures. If not, stop and surface the regression — do not
proceed.

## Slice 1 (do this first): C1 finish — local Supabase end-to-end

Goal: prove the `SupabaseBackend` adapter actually works against a real
Postgres + Auth + Realtime stack, fix any wire-shape bugs that surface, and
land an integration test that catches future regressions.

### 1a. Boot local Supabase

```bash
cd infra/supabase
supabase start
```

Capture the printed `API URL` (typically `http://127.0.0.1:54321`) and
`anon key`. Save both to your scratch buffer; you will need them.

Apply the migration + seed:

```bash
supabase db reset
```

Confirm the schema loaded:

```bash
supabase db dump --schema public --data-only=false 2>&1 | head -40
```

If migration fails, the most likely causes are:
- Postgres enum mismatches (we already reconciled `context_type` and
  `plan_visibility` to match the Swift enums; check `0001_init.sql` against
  `Sources/Models/AfterPlansModels.swift` if anything errors)
- RLS function definitions referencing tables that don't exist yet (order
  matters; security-definer functions are at the end of the file)

Fix the migration file in place (do NOT add a 0002 migration to patch
0001 — this hasn't shipped to anyone yet) and rerun `supabase db reset`.

### 1b. Run the iOS app against local Supabase

Edit the AfterPlans run scheme in Xcode and add these environment variables:

- `AFTERPLANS_BACKEND` = `supabase`
- `AFTERPLANS_SUPABASE_URL` = the API URL from `supabase start`
- `AFTERPLANS_SUPABASE_KEY` = the anon key from `supabase start`

`AfterPlansConfiguration.swift` already reads these. Run the app on the
iPhone simulator. Walk through:

1. Onboarding completes (anonymous auth bootstrap creates a row in `profiles`)
2. Home shows seeded contexts (the `contexts` rows from `seed.sql`)
3. Feed loads (will be empty at first — no plans seeded; create one)
4. Create a plan in the current context
5. Join the created plan from a second-pass run (or another simulator)
6. Confirm and wrap

Every operation that fails surfaces a wire-shape bug. Common ones to expect:

- **Snake_case mismatches** in upsert/update payloads — I used `[String: String]`
  dictionaries in some places (`expressInterest`, `suggestPlace`); these may
  need explicit `Encodable` types if PostgREST rejects them
- **`closed_at` ISO format** — the format string may need to match Postgres
  `timestamptz` parser
- **Missing `descriptor` columns** — the schema's `plan_participants` has a
  nullable `descriptor`, but the code assumes it exists
- **Empty `contextTitle` / `hostName` / participant `name`** — `hydrate()`
  returns these as empty strings because the basic queries don't join. The
  in-app feed renders fine without them in v1; if anything breaks, fix the
  query to include a `contexts!inner(title)` join

Each fix should be a one- or two-line change in `SupabaseBackend.swift` or
`0001_init.sql`. Resist the urge to redesign anything.

### 1c. Add an integration test

Once the manual walk-through works, add a test that exercises the same path
automatically, gated to skip when the env vars are unset:

- Path: `products/after-plans-ios/Tests/Services/SupabaseBackendIntegrationTests.swift`
- `setUp()` reads `AFTERPLANS_SUPABASE_URL` / `AFTERPLANS_SUPABASE_KEY` from
  `ProcessInfo.processInfo.environment`; if either is empty, call
  `throw XCTSkip(...)` so CI skips it cleanly
- One test method: bootstrap a fresh anonymous user, call `feed`,
  `createPlan`, `join`, `confirm`, `wrap`, assert each transition's
  `lifecycle` matches expectation
- Run it twice in a row — must be idempotent (each run creates a new
  anonymous user, so prior state doesn't matter)

Add the env vars to the test scheme too. Confirm: `xcodebuild test` runs all
51 tests and the new one passes when local Supabase is up.

### 1d. Update `PHASE_STATUS.md` + `remaining-steps-before-ios-submission.md`

Mark "Define a backend contract and ship a thin networked build" as complete
in the audit doc. Bump the manual-submission readiness estimate from 55-65%
to whatever the new state warrants — probably **70-80%** once C1 lands.

## Slice 2: Privacy policy + support URL

Apple requires both before submission. Both can be a single static page each.

What to do:

1. Draft `docs/products/after-plans/legal/PRIVACY_POLICY.md` reflecting the
   *current* data posture: anonymous auth optional, first name + context cues
   only, no location, no contacts, plan/report content user-typed. Reference
   the privacy nutrition labels in `APP_STORE_METADATA_DRAFT.md` and reconcile
   any drift (the privacy cleanup pass made the labels simpler than the early
   draft).
2. Draft `docs/products/after-plans/legal/SUPPORT.md` — a short "how to
   contact us" page with an email and a brief FAQ.
3. Decide hosting: simplest is GitHub Pages or a static page on whatever
   marketing domain you have. **Do not** stand up a custom backend for this.
4. Update `docs/products/after-plans/APP_STORE_METADATA_DRAFT.md` with the
   chosen URLs.

Do NOT commit a domain or set up DNS without the user's go-ahead — flag the
chosen hosting plan and ask for confirmation before publishing anything.

## Slice 3: Manual QA pass document

Catchbook has `manual-qa-pass.md`; After Plans does not. Create one mirroring
the Catchbook structure. Path:
`docs/products/after-plans/manual-qa-pass.md`.

Cover at minimum:

- Onboarding completes and persists across launches
- Context selection
- Create plan in each `PlanMode`
- Join from feed
- Suggest place
- Confirm
- Mark active
- Wrap → appears in history with recap
- Invite share for each `InviteShareChannel` (`sameContext`, `knownPeople`,
  `nearbyQR`)
- QR code displays and scans correctly
- Deep link `afterplans://join/<planID>` from Messages opens the plan
- Block hides plans from feed
- Report plan / report user / safety center reachable from detail
- Closed plans don't show share affordances
- Onboarding age/eligibility gate (whatever the founder approves)
- Privacy posture: no permission prompts (location strings removed)

This is a living checklist — leave checkboxes empty for now; the user fills
them in after the first TestFlight build.

## Slice 4: App icon refinement

The current icon is a placeholder generated by a Python/PIL script. It's
on-brand and submittable but not designer-finished. Two paths:

- **Iterate the script** at `/tmp/afterplans_icon.py` (regenerate from the
  same gradient + typography, refine details). The script is not in the
  repo — it should be moved to `infra/scripts/generate_afterplans_icon.py`
  and committed so it's reproducible.
- **Commission a designer pass** — out of scope for this conversation; surface
  this as a recommendation to the user.

If you iterate the script: do NOT change the brand colors. They are encoded
in `Sources/Shared/UI/DesignTokens.swift` as `Color.appAccent` (deep blue,
rgb 0.122/0.388/0.780) and `Color.appMomentum` (warm orange,
rgb 0.98/0.60/0.18). The icon is a dusk → afterglow gradient between them.

After regenerating: verify the icon at 60pt (smallest user-facing size) by
viewing `AppIcon-60@2x.png`. If text is illegible at that size, simplify the
wordmark (drop "after" line, keep "plans." with the dot, etc.) — but ask the
user first before changing the lockup.

## Slice 5: Founder decisions doc

Four approvals are blocking the App Store lane (per
`LAUNCH_PLAN.md` handoff checklist):

1. Subtitle (recommended: "Keep the moment going")
2. Age rating (recommended: 17+)
3. Initial seeded launch contexts
4. Moderation operating path — who triages reports, response window

Create a single decision-prompt doc at
`docs/products/after-plans/founder-decisions-needed.md` summarizing each
question, the recommendation, and a short list of trade-offs. Designed so
the founder can approve in one sitting.

## Hard rules for this entire workstream

1. **Do not run** `git push`, `gh pr create`, `gh pr merge`, or anything else
   that affects shared state without explicit user confirmation per task.
2. **Do not** install Homebrew packages or system-level software without
   asking. Docker and Supabase CLI are on the user; the prompt above assumes
   they're already present.
3. **Do not** edit `state/` or `.claude/worktrees/`. Those are runtime
   artifacts.
4. **Do not** mark a slice complete unless `xcodebuild test` is green.
5. **Do not** silently skip TODOs that surface during C1. Flag every wire-
   shape mismatch you fix in the chat before continuing.
6. **Do not** widen scope. Each slice has a clear stop condition. Stop at it.
7. **Trust SourceKit warnings about missing types in the same target as
   noise** — they are cross-file LSP false positives. The `xcodebuild`
   compiler resolves them correctly. Only act on errors that appear in
   `xcodebuild` output.

## Stop conditions

After each slice, run the full test suite, summarize what changed (≤ 10
lines), and ask the user whether to continue. Do not auto-chain slices.

End of handoff prompt.
