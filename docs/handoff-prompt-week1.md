# Handoff Prompt — Catchbook Go-to-Market Build Plan (Week 1)

Copy everything below this line into a fresh Claude Cowork chat with the ai-company-os folder selected.

---

## Context

You are picking up execution of the Catchbook go-to-market build plan. Catchbook is a privacy-first iOS fishing logbook app — SwiftUI + SwiftData, local-only, no accounts, no cloud, no third-party SDKs in v1.0. The repo is `ai-company-os`.

**Read these files first (in this order) before doing anything else:**

1. `docs/go-to-market-build-plan-v3.md` — the master execution plan. Read the ENTIRE file. It contains all decisions, all lanes, all open items, all risks. This is your single source of truth.
2. `docs/products/catchbook/brand-guidelines.md` — color palette, typography, visual direction
3. `docs/products/catchbook/appstore-metadata-draft.md` — current App Store metadata state
4. `docs/products/catchbook/submission-checklist.md` — 35-item structured submission checklist
5. `products/catchbook-ios/project.yml` — XcodeGen build config (recently renamed from FishingLogbook → Catchbook)
6. `products/catchbook-ios/Sources/Shared/UI/DesignTokens.swift` — current color tokens (still `.teal`, needs brand palette)
7. `AGENTS.md` — worker architecture and boundaries

**Do NOT read the full codebase.** The plan tells you everything you need to know about the current state.

## What has already been done (do not repeat)

- App name decided: **Catchbook**
- Full project rename: fishing-logbook → catchbook across all directories, files, targets, imports, configs. Bundle identifiers (`io.aicompanyos.products.fishinglogbook`) intentionally preserved (permanent Apple ID).
- `.env` file created with Gemini API key
- `.env.example` + `.gitignore` updated for secrets pattern
- `packages/config/settings.py` — `load_dotenv()` and `get_api_key()` helper functions added
- `packages/tools/content_tools/gemini_images.py` — Gemini image generation client (complete)
- `packages/tools/social_tools/postiz_client.py` — Postiz scheduling client (complete)
- `docs/products/catchbook/brand-guidelines.md` — brand palette extracted from icon (complete)
- TikTok account created and warming
- Gemini API key obtained (free tier)

## What needs to happen now — Week 1 tasks

Execute these in priority order. Items marked 🔴 are critical-path blockers.

### 🔴 1. Create PrivacyInfo.xcprivacy

**This is the #1 priority. Without it, Apple will reject the binary immediately.**

Create a `PrivacyInfo.xcprivacy` file at `products/catchbook-ios/PrivacyInfo.xcprivacy`. The app uses:
- Core Location (`NSLocationWhenInUseUsageDescription`) — for tagging fishing spots. Reason: user-initiated location capture for personal use, no tracking.
- PhotosUI (`NSPhotoLibraryUsageDescription`, `NSPhotoLibraryAddUsageDescription`) — for attaching catch photos. Reason: user-initiated media selection, local storage only.

After creating the file, add it to `project.yml` so Xcode includes it in the build.

### 2. Apply Catchbook brand palette to DesignTokens.swift

The app currently uses `.teal` everywhere. Update to match `brand-guidelines.md`:
- `appAccent` → Ocean Blue `#3BA3D9` (primary brand color)
- `appCardBackground` → Ocean Blue at 0.06 opacity
- `appCardBackgroundProminent` → Ocean Blue at 0.10 opacity
- Add `AccentColor.colorset` in the Asset Catalog with Ocean Blue (#3BA3D9) for light mode and a slightly lighter variant for dark mode
- Update `Sources/App/CatchbookApp.swift` — change `.tint(.teal)` to use the new brand color
- Verify dark mode looks good with the new palette

### 3. Place app icon in Asset Catalog

The icon PNG was provided but `Sources/Assets.xcassets/AppIcon.appiconset/` is empty. The 1024x1024 PNG needs to be placed there and `Contents.json` updated. For modern Xcode (iOS 17+), a single 1024x1024 universal icon in the asset catalog is sufficient — Xcode auto-generates all required sizes.

Check if the icon file exists somewhere in the repo or uploads directory. If not, note it as blocked on Kashane providing the file path.

### 4. Regenerate .xcodeproj

The `project.yml` was renamed from FishingLogbook to Catchbook but the `.xcodeproj/project.pbxproj` hasn't been regenerated yet. Run:
```bash
cd products/catchbook-ios && xcodegen generate
```
If xcodegen isn't installed, install it first: `brew install xcodegen`

### 5. Create GitHub Pages repo (catchbook-legal)

Create a GitHub repository called `catchbook-legal` with GitHub Pages enabled. It needs three pages:
- **Privacy Policy** — All data stored locally on device. No analytics, no tracking, no third-party SDKs. Location used only for personal spot tagging. Photos stored locally only. GDPR/CCPA compliant by design (no data collection). User can delete all data by uninstalling.
- **Terms of Service** — Personal use only. Not responsible for fishing decisions. Data is user's own.
- **Support** — Contact email for Kashane (ksakhakorn@gmail.com).

After deployment, update `docs/products/catchbook/appstore-metadata-draft.md` with the live URLs.

### 6. Competitive analysis

Research competing fishing logbook apps and create `docs/products/catchbook/competitive-analysis.md`:
- Fishbrain, FishAngler, BassMaster, Plusinno — what they charge, key features, user complaints (read 1-star App Store reviews)
- Feature parity table: what Catchbook has vs competitors
- Key differentiators to emphasize: privacy, offline-first, no account required, simplicity
- Use findings to sharpen App Store metadata

### 7. Keyword research + ASO metadata finalization

Current keyword list in `appstore-metadata-draft.md` is unresearched. Research via web search:
- What keywords do Fishbrain and FishAngler rank for?
- What are users searching for in the fishing logbook category?
- Identify 3-5 niche keywords with lower competition (e.g., "kayak fishing log", "saltwater catch journal")
- Finalize the 100-character keyword string
- Finalize the subtitle (current working directions: "Private Catch & Spot Log", "Remember What Worked", "Fishing Journal & Insights")
- Consider testing Reference (primary) + Sports (secondary) category placement vs current Sports + Reference
- Update `appstore-metadata-draft.md` with final decisions: pricing = Free, subtitle = finalized, keywords = researched

### 8. Start fishing lifestyle content generation

TikTok account is warming. Start generating fishing lifestyle content (angle 1 — serene scenery, golden hour, "this is the life" vibes). No app screenshots needed for these — they're pure fishing atmosphere content.

Use the Gemini client at `packages/tools/content_tools/gemini_images.py`. The `.env` file has the API key. Generate 3-5 test images first to evaluate quality before doing a full batch. Save outputs to `state/artifacts/content/`.

### 9. Write monetization strategy doc

Create `docs/products/catchbook/monetization-strategy.md`:
- Current v1.0 ships almost everything free (trip logging, catch recording, spot history, insights, share cards, backup export)
- Define what Pro features could be that DON'T already exist in v1.0
- Recommend pricing based on competitor research
- Define activation trigger (when to turn on paywall)
- Model 3 revenue scenarios (conservative, realistic, optimistic)

## Human actions Kashane still needs to do

These are flagged in the plan but require Kashane's manual action. Don't block on them — work around them:

- 🔴 **Xcode code signing** — Apple dev portal → create App ID for `io.aicompanyos.products.fishinglogbook` → distribution provisioning profile. This is a hard blocker for Week 2 submission.
- **Instagram account** — not a v1.0 blocker, TikTok launches first
- **Postiz signup** — deferred, manual posting for now
- **Choose release type** — recommend manual release for v1.0

## Important constraints

- **Bundle identifiers are permanent:** `io.aicompanyos.products.fishinglogbook` — do NOT change these anywhere
- **No RevenueCat in v1.0:** Deferred to v1.1 to keep the binary clean for first App Store review
- **XcodeGen, not raw Xcode:** All build config changes go through `project.yml`, then regenerate with `xcodegen generate`
- **The repo's skill system:** If you build a new skill, follow `skills/canonical/` → `skills/adapters/` → `.claude/skills/` wiring convention per `skills/WIRING.md`
- **State goes in `state/`:** Content outputs, campaign tracker, and runtime data belong in `state/`, never in source directories
