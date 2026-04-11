# App Store Readiness Audit: Catchbook

Single source of truth for what is ready, what is missing, and what must happen before App Store submission becomes a credible, repeatable workflow.

Audit date: 2026-04-08
Auditor: Claude (session handoff artifact)
Repo state: commit history through v0.1.4 iteration

## Status Key

- DONE — exists and is adequate for submission lane progress
- PARTIAL — exists but incomplete or not yet submission-grade
- MISSING — does not exist and is required before submission
- LATER — not needed for first submission but worth tracking

---

## A. Catchbook iOS App Readiness

### A1. App Structure and Code Quality — DONE

The app under `products/catchbook-ios/` is well-organized:

- 28 Swift source files across App, Features, Models, Services, Insights, Shared layers
- 16 Swift test files with 1:1 mirroring of source structure
- Clean SwiftUI + SwiftData architecture, local-first, no backend dependency
- Feature set covers trip logging, catch recording, spot management, insights, backup export
- Code is modular with separated logic (e.g., `HomeDashboardLogic`, `TripEditingLogic`) from views

Assessment: app structure is solid for an MVP submission.

### A2. Build Configuration — PARTIAL

What exists:
- `project.yml` (XcodeGen) defines targets, deployment target (iOS 17.0), Swift 5.0
- `Catchbook.xcodeproj` generated and functional
- Shared Xcode scheme with test coverage enabled

What is missing or needs attention:
- **Version alignment**: verified that `project.yml` and `Info.plist` both use version 1.0.0
- **Asset Catalog**: `Assets.xcassets` created with proper Contents.json
- **App Icon**: `AppIcon.appiconset` configured, placeholder ready for 1024x1024 icon
- **Launch Screen assets**: using default launch screen storyboard reference
- **Entitlements file**: evaluated and determined not needed for current feature set (documented in ENTITLEMENTS_NOTE.md)
- **exportOptions.plist**: not yet configured, may be needed for automated workflows
- **Signing configuration**: no team ID, no provisioning profile references — human will configure in Xcode

### A3. Test Coverage — PARTIAL

What exists:
- 16 test files covering models, services, features, shared logic
- iOS coverage threshold enforced at 20% via `IOS_COVERAGE_MIN`
- `test_ios.sh` script exists for local execution
- Tests-with-code policy is documented and enforced

What is missing:
- 20% coverage is too low for submission confidence — should target 40-60% before submission
- No UI tests or snapshot tests (documented as intentionally deferred, but some basic smoke tests would help)
- No test for the app entry point or navigation flow

### A4. Privacy and Permissions — DONE

- Location usage description present: "Capture trip locations privately for your own fishing history."
- Photo library read/write descriptions present
- Privacy-first positioning is consistent throughout product docs
- No network calls, no analytics SDKs, no third-party frameworks — clean privacy story

### A5. Product Artifacts — DONE

Complete artifact chain from founder brief through App Store positioning:
- founder-brief.md (imported from RTF)
- product-brief.md
- mvp-spec.md
- backlog.md
- ios-architecture.md
- app-store-positioning.md
- insight-rules.md
- insight-acceptance-cases.md

All tracked in `state/checkpoints/platform/products/catchbook.json` with status "ready".

### A6. App Store Metadata — PARTIAL

What exists:
- `app-store-positioning.md` with category, messaging, name direction, subtitle direction, screenshot story
- Metadata draft checkpoint at `state/checkpoints/platform/releases/metadata_drafts/metadata-catchbook-en-US.json` (status: ready)

What is missing:
- **No field-by-field ASC metadata draft** — After Plans has `APP_STORE_METADATA_DRAFT.md` as a model, Fishing Logbook does not
- **No final app name decided** — only "working directions" (Catchbook, Tidelog, etc.)
- **No App Store description written** — only positioning angles
- **No promotional text drafted**
- **No keywords list**
- **No "What's New" text**
- **No privacy policy URL** (required by Apple)
- **No support URL** (required by Apple)
- **No marketing URL**

### A7. Visual Assets — MISSING

- No app icon (1024x1024 required)
- No screenshot assets (required for submission — 6.7" and 6.5" iPhone at minimum)
- Screenshot checkpoint exists but has empty asset paths array
- No preview video (optional but recommended)
- Screenshot story is documented in positioning doc but no actual images exist

### A8. Release Configuration — MISSING

- No Fastlane setup (Fastfile, Appfile, Matchfile all absent)
- No automated archive/export workflow
- No code signing documentation
- No TestFlight configuration
- infra/fastlane/ directory exists but contains only a README placeholder

---

## B. Repo/System Readiness for App Store Submission

### B1. Worker Implementations — PARTIAL

iOS Worker (`apps/worker-ios/`):
- Real implementation: Codex invocation, worktree isolation, validation, review artifacts
- Handles iOS task packets and test policy enforcement
- Assessment: functional for code changes, but not yet wired for build/archive/export workflows

App Store Worker (`apps/worker-appstore/`):
- Real implementation: release action handler with approval gating
- Supports prepare_testflight, submit_testflight, submit_appstore, release_to_store actions
- Integrates with ApprovalStore and ReleaseStore
- Assessment: structural framework exists but actual ASC interaction is manual/placeholder

### B2. Task Schemas — DONE

- TaskPacket, TaskResult, TaskStatus, WorkerLane, RiskLevel all defined
- TestLane and NoTestReasonCode support iOS-specific validation
- Release-specific schemas (ReleaseRecord) exist
- ApprovalRecord tracks approval state transitions

### B3. Policies — PARTIAL

What exists:
- Approval policy code in `packages/policies/approvals.py`
- App Store submission listed as approval-required
- Release action classification (safe vs. approval-required)

What is missing:
- No submission-specific policy (e.g., checklist validation before submission is allowed)
- No metadata completeness validation policy
- No asset completeness validation policy
- Approval policy is keyword-based, not structured-checklist-based

### B4. Release State Tracking — PARTIAL

What exists:
- 5 release records (v0.1.0 through v0.1.4) in checkpoints
- 5 build candidates
- Metadata and screenshot set checkpoints (scaffolded)

What is missing:
- No actual build artifacts stored
- Screenshot set has empty asset paths
- Release records track state but don't enforce prerequisite completion

### B5. Folder Structure Alignment — DONE

Per AGENTS.md and README, the repo structure is correct:
- Product source in `products/catchbook-ios/`
- Product docs in `docs/products/catchbook/`
- Runtime state in `state/`
- Workers in `apps/worker-ios/` and `apps/worker-appstore/`
- Tools in `packages/tools/ios_tools/` and `packages/tools/appstore_tools/`
- No runtime state leakage into source folders detected

### B6. Documentation Alignment — PARTIAL

What is current and accurate:
- AGENTS.md — accurately describes worker boundaries, approval rules, testing contract
- README.md — accurately describes repo layout and current status
- architecture.md — comprehensive and aligned with code
- ios-lane.md — correctly separates iOS and App Store concerns
- ios-conventions.md — useful but thin
- implementation-phases.md — accurate phase descriptions

What is stale or missing:
- No dedicated App Store worker lane doc (ios-lane.md covers both briefly but App Store worker deserves its own)
- No submission checklist artifact
- No iOS worker operational guide (how to actually run the worker, what it expects, how to debug)
- No App Store worker operational guide
- docs/products/catchbook/ has no submission-readiness tracker

---

## C. Gap List

### Must Have Before Submission Lane Is Credible

1. **App Icon** — 1024x1024 icon required for both Xcode build and App Store submission [needs: human/designer]
2. **Asset Catalog** — Assets.xcassets with app icon set must be added to Xcode project [needs: iOS worker or human]
3. **Version alignment** — project.yml and Info.plist version strings must agree [needs: iOS worker]
4. **Field-by-field ASC metadata draft** — app name, description, keywords, promotional text, what's new [needs: App Store worker]
5. **Privacy policy URL** — required by Apple, must exist at a public URL [needs: human approval]
6. **Support URL** — required by Apple [needs: human approval]
7. **Screenshots** — at least iPhone 6.7" and 6.5" sets [needs: human/designer or automated capture]
8. **App Store submission checklist** — structured checklist artifact the App Store worker validates before submission is allowed [needs: platform]
9. **Signing documentation** — document how the human operator configures signing, what the workers expect to find [needs: docs]
10. **App Store worker lane doc** — dedicated operational doc for the App Store worker [needs: docs]

### Should Have Soon

11. **Fastlane configuration** — Fastfile for automated build, test, archive, TestFlight upload [needs: iOS worker lane]
12. **exportOptions.plist** — for headless archive/export [needs: iOS worker]
13. **Submission prerequisite validation policy** — code-level check that metadata, assets, build, and signing are complete before submission action is allowed [needs: packages/policies]
14. **Raise iOS test coverage** — from 20% to 40%+ before submission [needs: iOS worker]
15. **iOS worker operational guide** — how to run, configure, debug the worker [needs: docs]
16. **App review preparation doc** — what to expect, how to handle rejections, demo account notes [needs: docs]
17. **TestFlight workflow documentation** — internal testing setup, beta group management [needs: docs]

### Later / Nice to Have

18. **Automated screenshot capture** — using Xcode UI tests or Fastlane snapshot
19. **Localization support** — additional locales beyond en-US
20. **Preview video** — optional but helps conversion
21. **App Store Connect API integration** — currently manual, could be automated via ASC API
22. **Submission state machine formalization** — release records enforce ordered prerequisite completion
23. **CI integration for archive builds** — automated IPA generation in CI
24. **Watch/Widget support** — documented as later in backlog

---

## D. Proposed Implementation Plan

### Phase 1: Documentation and Checklist Foundation (do now)

Owner: current agent session
No code risk, highest leverage for making the lane credible and resumable.

1. Create `docs/appstore-lane.md` — dedicated App Store worker lane doc
2. Create `docs/products/catchbook/submission-checklist.md` — structured checklist
3. Create `docs/products/catchbook/appstore-metadata-draft.md` — field-by-field ASC draft (modeled on After Plans)
4. Update `docs/ios-lane.md` to cross-reference the new App Store lane doc
5. Create `docs/products/catchbook/HANDOFF.md` — next-agent-start-here note

### Phase 2: App Build Fixes (next Codex/iOS worker session)

Owner: iOS worker / Codex
Low risk, required for any build to be submission-grade.

1. Align version strings between project.yml and Info.plist
2. Add Assets.xcassets with placeholder app icon
3. Add entitlements file if needed
4. Verify clean archive build succeeds

### Phase 3: Metadata and Asset Production (next App Store worker session)

Owner: App Store worker / human
Requires human decisions on app name, icon design, screenshot capture.

1. Finalize app name
2. Write full App Store description
3. Capture or create screenshots
4. Set up privacy policy and support URLs
5. Fill in all ASC metadata fields

### Phase 4: Automation and Policy (later)

Owner: platform / engineering worker
Higher effort, needed for repeatability but not for first submission.

1. Set up Fastlane
2. Add submission prerequisite validation to policy code
3. Wire App Store worker to validate checklist before allowing submission actions
4. Add CI archive build step

---

## E. Current Assessment Summary

The fishing logbook app is in good shape as an MVP product. The code is well-structured, the product artifacts are comprehensive, and the platform architecture correctly separates iOS and App Store concerns. The main gaps are in the "last mile" of submission readiness: visual assets, metadata specifics, build configuration details, and the operational documentation that would let an agent or human walk through submission without guessing.

The repo's platform infrastructure (workers, schemas, policies, state tracking) is more mature than typical for this stage. The App Store worker has real approval-gated logic. What it lacks is the concrete checklist and metadata artifacts that turn "structurally ready" into "actually submittable."

The highest-leverage work right now is documentation: creating the missing checklist, metadata draft, and lane docs so that future sessions (Claude or Codex) can pick up exactly where this audit leaves off.
