# Catchbook: Remaining Steps Before iOS Submission

Audit date: 2026-04-20
Scope: audit only, no submission attempted

## Bottom Line

Catchbook looks close to a **manual App Store submission**.

Most product-facing submission assets already exist:

- App name, subtitle, description, keywords, review notes, and URLs are drafted
- screenshots exist for 6.7" and 6.5" iPhone classes
- app icon exists in the asset catalog
- privacy manifest and permission strings exist
- WeatherKit entitlement and attribution are present
- the iOS test suite is wired and local Xcode tooling is available
- manual QA and App Review prep docs exist

The main remaining work is no longer "invent the release package." It is:

1. finish the last Apple-side setup and archive flow
2. run TestFlight on a real device and complete sign-off
3. clean up stale release-state records that still point at the old `fishing-logbook` identity
4. build the real automation layer if you want future submissions to happen through Codex or Claude instead of manually in Xcode and App Store Connect

## Current Readiness Assessment

### Manual submission readiness

Estimated status: **close**

If we define "ready to submit manually" as "a human can finish the remaining Apple steps without needing more product/engineering discovery," Catchbook appears to be roughly in the **80-90% complete** range.

### Fully agent-driven submission readiness

Estimated status: **not close yet**

If we define "ready for Codex/Claude to submit it for me" as "the system can prepare, upload, validate, and advance App Store state through approval-gated automation," Catchbook appears to be roughly in the **35-50% complete** range.

The app artifacts are mostly there. The missing part is the real release automation.

## Remaining Steps Before Manual iOS Submission

### 1. Configure signing in Xcode

Why it still remains:

- the docs say this is a human Xcode step
- there is no evidence in repo state that signing has been completed for a release archive

What to do:

1. Open `products/catchbook-ios/Catchbook.xcodeproj`
2. Select the Catchbook target
3. Enable automatic signing
4. choose the Apple Developer team
5. confirm bundle identifier `io.aicompanyos.products.fishinglogbook`
6. confirm WeatherKit capability is present in signing/capabilities

Blocking level: **hard blocker**

### 2. Produce and validate a release archive

Why it still remains:

- the repo has build/test wiring, but no committed evidence of a successful release archive
- the current App Store lane does not create real build artifacts

What to do:

1. create an Xcode archive for Catchbook
2. verify the Release configuration succeeds
3. confirm the archive is uploadable to App Store Connect

Blocking level: **hard blocker**

### 3. Upload the build to TestFlight

Why it still remains:

- the docs describe this as a future/manual step
- the App Store worker does not actually upload builds

What to do:

1. create the internal TestFlight group in App Store Connect
2. upload the archive from Xcode
3. wait for processing
4. install the build through TestFlight

Blocking level: **hard blocker**

### 4. Complete the physical-device QA pass and sign-off

Why it still remains:

- `manual-qa-pass.md` exists, but it is still a blank execution sheet
- TestFlight validation is not recorded as complete

What to do:

1. run the scenarios in [manual-qa-pass.md](/Users/simons/ai-company-os/docs/products/catchbook/manual-qa-pass.md)
2. record pass/fail results
3. fix any issues found
4. re-archive if needed

Blocking level: **hard blocker**

### 5. Finish the remaining App Store Connect form work

Why it still remains:

- these are still documented as manual ASC tasks

What to do:

1. complete the age rating questionnaire
2. complete the content rights declaration
3. complete the App Privacy nutrition labels
4. confirm pricing and availability
5. upload screenshots
6. paste in the finalized metadata fields
7. paste in the review notes

Blocking level: **hard blocker**

### 6. Do a final submission review pass

Why it still remains:

- the checklist is comprehensive, but the repo contains conflicting/stale readiness records

What to do:

1. verify the checklist still matches reality
2. verify the latest app version/build number to submit
3. confirm no last-minute regressions after TestFlight
4. only then move to "Add for Review" and "Submit to App Review"

Blocking level: **hard blocker before actual submission**

## Remaining Repo/System Cleanup Before We Should Trust The Submission State

These are not all Apple blockers, but they are important audit findings.

### 1. Release state still points to the old `fishing-logbook` identity

Evidence:

- `state/checkpoints/platform/products/fishing-logbook.json`
- `state/checkpoints/platform/releases/release_records/release-fishing-logbook-v0.1.4.json`
- `state/checkpoints/platform/releases/metadata_drafts/metadata-fishing-logbook-en-US.json`
- `state/checkpoints/platform/releases/screenshot_sets/screenshots-fishing-logbook-iphone.json`

Why this matters:

- the static product registry says the product is `catchbook`
- the persisted release state still tracks the old product id and stale doc paths
- that creates risk for any future automation, approvals, or release-readiness checks

Recommended next step:

- migrate or regenerate the Catchbook product/release checkpoints so the live state matches `infra/products.json` and `docs/products/catchbook/`

Priority: **high**

### 2. Screenshot checkpoint state is stale

Evidence:

- screenshot files exist under `docs/products/catchbook/screenshots/`
- persisted screenshot state still has `"asset_paths": []`

Why this matters:

- the human docs say screenshots are ready
- the machine-readable release state says they are not

Recommended next step:

- update the screenshot-set checkpoint to reference the actual screenshot assets

Priority: **high**

### 3. Older readiness docs are stale or contradictory

Evidence:

- `appstore-readiness-audit.md` still says screenshots, icon, and metadata are missing
- newer docs say those items are complete

Why this matters:

- future workers or agents could follow the wrong source of truth
- audits become noisy and harder to trust

Recommended next step:

- refresh or replace the stale readiness audit so it matches the current state

Priority: **medium**

## Remaining Work Before Codex Or Claude Can Submit Catchbook End-To-End

This is the bigger gap behind your long-term goal.

### 1. Real archive/export automation

Current state:

- iOS scripts and Xcode project exist
- no release-grade archive/export pipeline is wired into the worker flow
- `infra/fastlane/` is still basically a placeholder

Needed:

- deterministic archive command
- export configuration
- artifact capture
- failure handling and logs

### 2. Real App Store Connect integration

Current state:

- `packages/tools/appstore_tools/asc_api.py` is a placeholder
- the App Store worker mostly updates local release records

Needed:

- authenticated ASC API client
- create/select build flows
- metadata upload
- screenshot upload
- status fetch for TestFlight/App Review/release state

### 3. Approval-gated irreversible actions wired to real side effects

Current state:

- approval policy exists
- release-readiness policy exists
- the worker does not yet perform the actual irreversible App Store actions

Needed:

- connect approval records to real submission/release API calls
- keep submit/release actions blocked unless checklist, release state, and approvals all pass

### 4. Machine-readable release artifact completeness

Current state:

- much of the release package exists only in markdown docs
- checkpoint state is incomplete or stale

Needed:

- synced metadata draft state
- synced screenshot set state
- synced release candidate state
- one canonical "ready for submission" machine-readable record

### 5. Review-status monitoring and rejection handling

Current state:

- docs exist for review prep
- no live polling or review-response workflow exists

Needed:

- ASC status polling
- inbox/task creation on rejection or metadata issues
- drafted review responses
- handoff back to the iOS lane when code fixes are required

## Recommended Sequence From Here

If the goal is **submit Catchbook soon**, the best order is:

1. complete Xcode signing and produce a release archive
2. upload to TestFlight and run the physical-device QA pass
3. complete the remaining App Store Connect fields
4. clean up the stale `fishing-logbook` release records
5. do a final checklist review
6. only after that, submit for review

If the goal is **eventually submit through me or Claude**, then after the manual submission path is proven once:

1. fix the stale Catchbook release state
2. implement archive/export automation
3. implement real ASC API integration
4. wire approval-gated submit/release actions to those integrations
5. add end-to-end release verification for the App Store lane

## Practical Answer

Catchbook looks **close to first manual submission**, but **not yet close to hands-off autonomous submission**.

The app and its submission materials are mostly in place. The remaining short-term work is mostly Apple-side execution and real-device validation. The remaining long-term work is release automation, state cleanup, and true App Store Connect integration.
