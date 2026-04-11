# Handoff: Catchbook App Store Readiness

Start here if you are a new agent (Claude or Codex) picking up work on the Catchbook App Store submission lane.

Last updated: 2026-04-08 (two-pass session: audit then implementation)

## What Was Done (2026-04-08 session)

### Pass 1: Audit

A full audit was performed covering the iOS app, repo platform, worker implementations, schemas, policies, docs, and state tracking. The single source-of-truth assessment is:

- `docs/products/catchbook/appstore-readiness-audit.md`

### Pass 1: New documentation artifacts

1. **appstore-readiness-audit.md** — comprehensive gap analysis with prioritized findings
2. **submission-checklist.md** — structured 35-item checklist for App Store submission, with status markers
3. **appstore-metadata-draft.md** — field-by-field App Store Connect metadata draft (modeled on After Plans)
4. **docs/appstore-lane.md** — dedicated App Store worker lane operational doc
5. **Updated docs/ios-lane.md** — added cross-references to new docs

### Pass 2: Technical implementation (iOS worker tasks)

Four tasks were planned, dispatched to agents, executed, and reviewed against repo standards:

1. **Version string fix** — APPROVED
   - `project.yml` MARKETING_VERSION changed from 0.1.0 to 1.0.0
   - `Info.plist` CFBundleShortVersionString changed from 1.0 to 1.0.0
   - Both now agree on 1.0.0 for first App Store release

2. **Asset catalog creation** — APPROVED
   - Created `Sources/Assets.xcassets/` with Contents.json
   - Created `AppIcon.appiconset/Contents.json` (modern single-size 1024x1024 format)
   - Created `AccentColor.colorset/Contents.json`
   - Added `ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon` to project.yml
   - Note: actual icon PNG still needed from designer

3. **Entitlements evaluation** — APPROVED
   - Determined no .entitlements file needed for current feature set
   - Created `ENTITLEMENTS_NOTE.md` documenting the evaluation and future triggers

4. **Test coverage expansion** — APPROVED
   - Created `Tests/Insights/DeterministicInsightCardTests.swift` (11 tests)
   - Created `Tests/App/AppTabTests.swift` (11 tests)
   - Created `Tests/Services/LocationRecorderTests.swift` (7 tests)
   - 29 new test methods total across 3 files
   - All follow repo conventions: `@testable import Fishing_Logbook`, XCTestCase, descriptive names

### Review process

All agent outputs were reviewed by reading every modified/created file, validating JSON/YAML/XML parsing, checking Swift import conventions, and verifying no files outside the task scope were touched. No lane boundary violations, no policy violations, no state leakage into source folders.

### Key findings

The app code is solid for MVP. The platform infrastructure (workers, schemas, policies, state tracking) is more mature than expected. The remaining gaps are concentrated in:

- Visual assets (app icon PNG needed, no screenshots yet)
- Metadata specifics (no final app name, no description, no URLs)
- Human decisions needed (app name, pricing, URLs, signing setup)

## What Remains

### Needs human decisions (blocked until human input)

- Final app name
- Pricing (free vs. paid)
- Privacy policy URL (must exist at public URL)
- Support URL (must exist at public URL)
- Code signing setup in Xcode
- Release type (manual vs. automatic after Apple approval)

### Needs iOS worker / Codex (unblocked, can proceed)

1. ~~Fix version string mismatch~~ — DONE (2026-04-08, aligned to 1.0.0)
2. ~~Add Assets.xcassets with placeholder app icon set~~ — DONE (2026-04-08, structure created)
3. Verify clean archive build — still needed
4. ~~Add tests for uncovered logic files~~ — DONE (2026-04-08, 29 new tests)
5. ~~Evaluate entitlements~~ — DONE (2026-04-08, not needed, documented)
6. Measure actual test coverage after new tests (run `test_ios.sh` on Mac with Xcode)
7. Add more tests if coverage still below 40% after measurement

### Needs App Store worker (partially blocked on human decisions)

1. Finalize metadata draft once app name is chosen
2. Write final App Store description
3. Optimize keywords
4. Draft review notes
5. Validate checklist completeness before any submission action

### Needs designer / human (blocked)

1. App icon design (1024x1024)
2. Screenshot capture (at least iPhone 6.7" and 6.5")

### Needs platform work (lower priority, for repeatability)

1. Fastlane setup for automated builds
2. Submission prerequisite validation in policy code
3. CI archive build step

## Reading Order for New Agent

1. `AGENTS.md` — understand worker boundaries
2. `docs/ios-lane.md` — understand iOS vs App Store separation
3. `docs/appstore-lane.md` — understand App Store worker scope
4. `docs/products/catchbook/appstore-readiness-audit.md` — current state assessment
5. `docs/products/catchbook/submission-checklist.md` — what specifically needs to happen
6. `docs/products/catchbook/appstore-metadata-draft.md` — current metadata state

## Conventions

- Product source: `products/catchbook-ios/`
- Product docs: `docs/products/catchbook/`
- Runtime state: `state/checkpoints/platform/`
- iOS worker: `apps/worker-ios/`
- App Store worker: `apps/worker-appstore/`
- Policies: `packages/policies/`
- Schemas: `packages/schemas/`

## Next Best Action

If you are a **Claude session**: the highest-value unblocked work is (a) verifying an archive build succeeds on the host Mac, (b) measuring test coverage after the new tests, (c) refining metadata once the human decides on an app name.

If you are a **Codex session**: the highest-value unblocked work is (a) adding more test coverage if measurement shows it's still below 40%, (b) any app polish tasks from the backlog.

If you are the **human operator**: the most impactful thing you can do right now is:
1. Decide on an app name (working directions: Catchbook, Tidelog, Angler Journal, Spotbook Fishing)
2. Set up a privacy policy page and support URL
3. Provide or commission a 1024x1024 app icon PNG
4. Open the project in Xcode, verify it builds cleanly, and run the test suite to measure coverage
