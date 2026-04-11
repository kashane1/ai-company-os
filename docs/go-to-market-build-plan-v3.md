# AI Company OS — Go-to-Market Build Plan v3

**Date:** April 8, 2026 (last revised April 9, 2026)
**Product:** Catchbook — Private Fishing Logbook (first app)
**Budget:** Near-zero ($0-50/mo operational, $99/yr Apple Developer Program already active)
**Status:** All decisions resolved. Execution started 2026-04-09.

---

## Decisions Made

These are locked in from our planning sessions:

1. **Monetization:** Launch fully free with zero third-party SDKs in v1.0. Add RevenueCat in v1.1 (first update post-approval) with paywall wired but inactive. Activate pro tier later once user behavior data shows what features people value. No ads ever — it kills the private/elegant positioning.
2. **Content marketing style:** Test all three angles (fishing lifestyle, fishing tips + data, catch log highlights), then double down on the winner.
3. **Posting cadence:** Start at 1x/day on TikTok and 1x/day on Instagram. Scale frequency later.
4. **Image generation:** Google Gemini API direct (`gemini-2.0-flash-exp`, image generation) for images. OpenRouter stays for text/reasoning.
5. **Content types:** Slideshows (primary volume) + Xcode simulator screen recordings (credibility/demo content).
6. **Scheduling:** Postiz hosted at $29/mo to start. Self-hosting on the always-on MacBook Air is a future optimization.
7. **Posting method:** Manual posting from personal phone first. Android + ADB automation deferred until content is validated.
8. **Campaign intelligence:** AI agents make format decisions autonomously. Daily/weekly summaries surfaced to Kashane. TikTok and IG tracked separately.
9. **Attribution:** Deferred. RevenueCat analytics + App Store Connect only until product-market fit is validated.
10. **Always-on host:** MacBook Air serves as the local server for all ai-company-os automation.

---

## Current State of Catchbook

Based on the repo audit (2026-04-08), here's where the app stands:

**Done:** App structure solid (28 Swift source files, 16 test files), SwiftUI + SwiftData local-first architecture, feature set covers trip logging / catch recording / spot management / insights / backup export, product artifact chain complete (founder brief through app store positioning), version strings aligned, asset catalog structure created, entitlements evaluated, 29 new tests added.

**Blocked on human decisions:** ~~Final app name~~ (decided: **Catchbook**), ~~privacy policy URL~~ (GitHub Pages), ~~support URL~~ (GitHub Pages), code signing setup in Xcode, release type.

**Needs work:** ~~App icon PNG (1024x1024)~~ (icon provided, needs Asset Catalog placement), brand palette application to SwiftUI codebase, screenshots (iPhone 6.7" and 6.5"), archive build verification, test coverage improvement (currently ~20%, target 40%+), Fastlane setup.

**Critical submission blockers found (iOS dev review):**
- **PrivacyInfo.xcprivacy MISSING** — iOS 17+ requires a Privacy Manifest declaring reasons for using Location and Photo Library APIs. Without this file, Apple WILL reject the binary. Must be created in Week 1.
- **TestFlight validation not planned** — Must test on a physical iPhone via TestFlight before submission. Simulator doesn't catch signing, permission, and performance issues that real devices surface.
- **Test coverage at ~20%** — Too low for submission confidence. No tests for app launch, permission denial edge cases, or integration flows. Target 40%+ before archive.

**Metadata ready to finalize:** App Store description drafted (Catchbook name inserted), keywords drafted (needs real research — current list is guesswork), promotional text drafted, review notes drafted — all in `docs/products/catchbook/appstore-metadata-draft.md`. Still needs: subtitle finalized, pricing confirmed as free, release type chosen (manual vs auto).

**Build system note:** App uses XcodeGen (`project.yml`) — not SPM root Package.swift. Any new dependencies (RevenueCat, etc.) must be added via `project.yml` packages section. `CFBundleDisplayName` updated to "Catchbook". Project renamed from FishingLogbook to Catchbook across all targets (2026-04-09). pbxproj must be regenerated via `xcodegen generate`.

---

## The Seven Lanes

Each lane below maps to a gap in the go-to-market pipeline. Lanes are ordered by dependency — build top to bottom.

---

### LANE 1: Monetization Infrastructure (Gap 4)

**Job:** Pre-wire RevenueCat so the paywall can be activated later without a code change or app update.

**Decided:** Launch completely free. No paywall active at launch. No ads ever.

**Revised approach (v3.1):** Do NOT include RevenueCat SDK in the v1.0 binary. Ship the leanest possible binary for first App Store review — fewer dependencies = fewer rejection vectors. Add RevenueCat in v1.1 (first post-approval update) once the app is live and you have baseline download data.

**Why defer SDK from v1.0:** Apple reviewers occasionally flag inactive IAP frameworks or SDKs that configure products but never present a purchase flow. A clean v1.0 with zero third-party SDKs matches Catchbook's "no accounts, no cloud, no tracking" privacy story. RevenueCat can be added in a single update without disrupting users since the free feature set doesn't change.

**Tools:**
- [RevenueCat/purchases-ios](https://swiftpackageindex.com/RevenueCat/purchases-ios) — Swift SDK via SPM, free until $2.5k/mo revenue
- [RevenueCatUI](https://www.revenuecat.com/docs/tools/paywalls) — pre-built paywall templates for when you activate
- [70-line SwiftUI example](https://gist.github.com/joshdholtz/48aa8be3d139381b5eee1c370f407fd8) — reference implementation

**Build steps:**
1. v1.0 launch: Ship with NO monetization SDK. Pure free app.
2. Post-launch (v1.1 prep): Create RevenueCat account, connect to App Store Connect
3. Configure products (placeholder pricing — e.g., $4.99/mo, $29.99/yr) and entitlements ("pro")
4. Write a RevenueCat integration skill for the iOS worker — install SDK via `project.yml` packages section (XcodeGen, not Package.swift), configure API key on app launch, check entitlement status, but do NOT present paywall yet
5. Ship v1.1 with RevenueCat wired but paywall hidden. This gives you the ability to flip it on server-side later without another binary update.
6. When ready to activate: define pro features based on user data, configure offerings in RevenueCat dashboard, enable paywall presentation via remote config flag

**Pro tier direction (for later):** Free = core logging loop (start trip, log catches, view history, basic personal bests). Pro = intelligence layer (spot-detail recall, filters, weather data, catch share card export, seasonal nudges, pattern replay). Drawing the line at "logging is free, memory/recall is pro."

**Effort:** v1.0 = zero work (ship without SDK). v1.1 RevenueCat integration = RevenueCat account setup ~1 hour, integration skill ~1 session, per-app wiring ~30 minutes.

---

### LANE 2: App Store Optimization (Gap 5)

**Job:** Make the App Store listing convert browsers into downloaders.

**Decided:** Build a generalized ASO skill, first applied to the fishing logbook. The app already has extensive positioning docs, a metadata draft, and a submission checklist — the ASO skill refines and completes what exists rather than starting from scratch.

**Existing repo artifacts to build on:**
- `docs/products/catchbook/app-store-positioning.md` — category, messaging, name direction, subtitle direction, screenshot story
- `docs/products/catchbook/appstore-metadata-draft.md` — full field-by-field ASC draft with description, keywords, promotional text, review notes
- `docs/products/catchbook/submission-checklist.md` — 35-item checklist, ~15 of 35 complete
- `docs/products/catchbook/appstore-readiness-audit.md` — comprehensive gap analysis

**Tools:**
- [AppDrift](https://appdrift.co/) — free AI metadata generation, screenshot generator, keyword tracking
- Apple Search Ads keyword tool (free) — keyword suggestions with search popularity scores
- [AwesomeASO](https://www.awesomeaso.com/) — free ASO tools for indie devs

**Build steps:**
1. Create a generalized ASO skill that: takes app name + niche + existing positioning docs → runs keyword research via AppDrift/Apple Search Ads → generates optimized subtitle, description, keywords → generates screenshot text overlay copy
2. Apply to fishing logbook: refine the existing metadata draft with keyword-optimized copy. **Finalize subtitle** — current working directions are "Private Catch & Spot Log" (22 chars), "Remember What Worked" (20 chars), "Fishing Journal & Insights" (26 chars). ASO skill should test keywords and pick.
3. **App Store screenshots (CRITICAL PATH):** Capture Xcode simulator screenshots (not screen recordings — those are Lane 3 marketing content). Required: 6.7" (iPhone 15 Pro Max, 1290×2796) and 6.5" (iPhone 11 Pro Max, 1242×2688). Need 4-8 screenshots showing: trip logging, catch entry, spot history, insights dashboard, share card, and the privacy empty-state. Composite with text overlays using brand palette. This is a self-contained Lane 2 task — does NOT depend on Lane 3.
4. Complete the remaining submission checklist items that don't require human decisions
5. **Update `project.yml`:** Verified `CFBundleDisplayName` is set to "Catchbook". Verified `PRODUCT_NAME` is set to "Catchbook".

**Privacy Manifest (PrivacyInfo.xcprivacy) — CRITICAL:**
iOS 17+ requires a Privacy Manifest file declaring reasons for using specific APIs. Catchbook uses Core Location and PhotosUI — both require explicit reason declarations. Without this file Apple will reject the binary immediately.

Create `PrivacyInfo.xcprivacy` at the project root with:
- Location: `NSPrivacyAccessedAPICategoryLocationServices` → reason: tagging fishing spots (personal use, no tracking)
- Photos: `NSPrivacyAccessedAPICategoryPhotoLibrary` → reason: attaching catch photos (user-initiated, local only)
- Add to `project.yml` target settings: reference the privacy manifest file
- Regenerate Xcode project after adding

**Privacy Policy, Terms of Service & Support URL Setup:**
Create a single GitHub Pages repo (e.g., `catchbook-legal`) with three pages: privacy policy, terms of service, and support. GitHub Pages is free, publicly accessible, and satisfies Apple's URL requirements. The privacy story is simple — all data local, no analytics, no third-party SDKs — so the privacy policy is straightforward. Terms of service covers liability ("personal use only") and data handling. Support page needs an email contact. All URLs go into App Store Connect metadata and `appstore-metadata-draft.md`.

The legal pages should address GDPR (EU) and CCPA (California) compliance: "All data stored locally on your device. No data is sent to servers. You can delete all data by uninstalling the app."

**Blocked on:** ~~Final app name decision~~ (decided: **Catchbook**), ~~privacy policy URL~~, ~~support URL~~ → resolved via GitHub Pages repo above. Remaining: **subtitle finalization** (ASO skill will handle), **release type** (manual recommended for first submission — lets you verify everything before going live).

**Effort:** ASO skill creation ~1 session. Per-app application ~1-2 hours. Screenshot capture + compositing ~2-3 hours (first time). GitHub Pages repo ~30 minutes. project.yml rename ~15 minutes.

---

### LANE 3: Content Factory (Gap 6)

**Job:** Take the fishing logbook app + niche and produce a stockpile of marketing content — slideshow images, screen recordings, captions, and hashtags — entirely AI-generated, ready to schedule.

**Decided:** Test three content angles simultaneously: fishing lifestyle (golden hour, peaceful nature, "this is the life"), fishing tips + data (educational, seasonal guides, best lures), and catch log highlights (app demos, stats screens, organized data). Identify winner after week 1, then 80% winner / 20% experimental going forward.

**Tools:**
- Google Gemini API (`gemini-2.0-flash-exp`) — free tier at 15 req/min. Generates legible text on images, supports vertical aspect ratios. Set up at [ai.google.dev](https://ai.google.dev/gemini-api/docs/image-generation). **Rate limit note:** generating a weekly stockpile (21 images) = 21 API calls. At 15 req/min the batch completes in ~2 minutes, but add 2-second delays between calls to stay safely under limits. The free tier also has daily quotas — check current limits at setup.
- Xcode simulator + `xcrun simctl io booted recordVideo` — screen recording for app demo content (marketing videos, not App Store screenshots)
- [ReelFarm](https://reel.farm/) — AI UGC video generation (future upgrade, paid)

**Content structure per post (3 slides):**
- Slide 1: Hook — introduce concept, why should they care
- Slide 2: Main value — core information or benefit
- Slide 3: Resolution + CTA — emotional pull + "link in bio" / app name

**Fishing-specific marketing angles:**
- Lifestyle: serene fishing scenery, golden hour shots, "the private fishing journal for anglers who care about their craft"
- Tips + data: "5 lures that crush bass in April", seasonal patterns, weather correlations — with the app as the tool that tracks all of it
- Catch highlights: actual app screenshots, logging demo, spot recall in action, "here's what I logged vs. here's what the app remembered for me next time"

**Build steps:**
1. ~~Set up Gemini API key at ai.google.dev~~ — done (2026-04-09), key needs to go in `.env`
2. Build the Content Factory skill: inputs = app name, niche, marketing angle, number of posts. Outputs = organized folder of slideshow image sets (3 per post) + captions + hashtags. Should generate a full week (7 posts = 21 images) in one batch. Must include inter-request delays (2s minimum) to respect Gemini rate limits.
3. Build screen recording workflow: launch Catchbook in Xcode simulator → navigate through key flows (start trip, log catch, view spot recall) → record → trim to 15-30 second clips → add text overlay
4. Create slide templates for each of the 3 angles with consistent brand elements (color palette from `brand-guidelines.md`, font style, tone of voice)
5. **Content quality gate:** Every generated batch goes through a review pass BEFORE scheduling. Check for: AI artifacts (extra fingers, warped text, uncanny faces), unreadable or misspelled text overlays, off-brand tone, images that look obviously AI-generated. Rejected images get regenerated. First few batches Kashane reviews manually; once the prompt templates are dialed in, the agent can self-review by checking legibility and brand alignment.

**Content can start before app launch.** TikTok account is warming now. Pre-launch content builds hype and signals to the algorithm that the account is active. Start posting fishing lifestyle content (angle 1) immediately — no app screenshots needed for these. App demo content (angle 3) waits until the brand palette is applied and the app looks polished.

**Effort:** Content Factory skill ~2 sessions. Screen recording workflow ~1 session. Per-week stockpile generation ~1-2 hours once skills exist. First batch will take longer due to prompt iteration.

---

### LANE 4: Social Media Scheduling (Gap 8)

**Job:** Take content stockpiles from Lane 3 and schedule them across TikTok and Instagram, sending everything to drafts for review.

**Decided:** Start with Postiz hosted ($29/mo), 1x/day on both TikTok and IG. Self-hosting on MacBook Air is a future cost optimization.

**Tools:**
- [Postiz](https://postiz.com/) — $29/mo hosted, 30+ platforms, agent-friendly API
- [gitroomhq/postiz-agent](https://github.com/gitroomhq/postiz-agent) — CLI built specifically for AI agents (Claude, OpenClaw). Outputs structured JSON. Has a [Claude Cowork integration page](https://postiz.com/claude-cowork).
- `@postiz/node` — Node SDK for programmatic access

**Posting rules (encoded from reference posts):**
- Send to DRAFTS only (not direct publish)
- No audio set (pick manually or skip for slideshows)
- Maximum 5 hashtags per post, trending and relevant to fishing/angling
- Caption under 1,000 characters, natural tone
- Schedule: 1 post/day at optimal time (test different times in week 1)
- Media must be uploaded to Postiz first (TikTok/IG reject external URLs)

**Build steps:**
1. Create Postiz account at postiz.com, get $29/mo plan, generate API key
2. Install Postiz Agent CLI: `npm install -g @postiz/cli`
3. Connect TikTok and Instagram accounts to Postiz
4. Build the Scheduler skill: takes a content folder (from Lane 3) → uploads all media to Postiz → creates posts with 3-slide structure → schedules at specified times → sends to drafts → outputs a manifest for review
5. Cross-platform adaptation rules: same images for both platforms (9:16 works on both), slightly different caption style and hashtag sets for IG vs TikTok

**Self-hosting later (for reference):** Postiz is open source ([gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app)). Self-hosting requires Docker Desktop on your Mac, then `docker-compose up` with their config (Node.js app + PostgreSQL + Redis). Your MacBook Air can handle it. Switch when the pipeline is proven and you want to cut the $29/mo.

**Effort:** Postiz setup ~30 minutes. CLI installation + testing ~1 hour. Scheduler skill ~1-2 sessions. Per-week scheduling ~30 minutes once skill exists.

---

### LANE 5: Anti-Shadowban Posting (Gap 9)

**Job:** Post content from a physical Android device instead of via API to avoid TikTok's reach-limiting algorithm.

**Decided:** Manual posting from personal phone first. Android + ADB automation is a Phase 2 upgrade after content is validated and the pipeline is working.

**Phase 1 (now): Manual posting**
- Content generated by Lane 3, scheduled to drafts by Lane 4
- Kashane reviews drafts on Postiz, then manually posts from phone
- This validates the content quality before investing in automation
- Also serves as account warming (human behavior on the account)

**Phase 2 (later): Android automation**

**GitHub repos to fork/adapt:**

| Repo | Purpose | Why it matters |
|------|---------|---------------|
| [Hormold/tiktok-warmup](https://github.com/Hormold/tiktok-warmup) | Account warming via ADB + Gemini Vision | TypeScript, staged architecture (initiating → learning → working), multi-device support, uses Gemini API you'll already have |
| [edde746/tiktok-uploader](https://github.com/edde746/tiktok-uploader) | Slideshow upload via ADB | Python, includes `greentext_slideshow.py` example, lightweight starting point |
| [haziq-exe/TikTokAutoUploader](https://github.com/haziq-exe/TikTokAutoUploader) | Upload with sound + hashtags | Python, updated Feb 2026, browser-based alternative |
| [oh-ashen-one/reddit-growth-skill](https://github.com/oh-ashen-one/reddit-growth-skill) | Reddit growth OpenClaw skill | Reference for how to structure agent skills for social platform automation |

**Phase 2 build steps (when ready):**
1. Buy a cheap Android phone (~$50 Samsung, Android 5.0+, no root needed)
2. Install Android SDK platform tools, enable USB debugging, pair via USB
3. Fork Hormold/tiktok-warmup → configure for fishing niche keywords
4. Fork edde746/tiktok-uploader → adapt to pull drafts from Postiz, open TikTok, post slideshow, add audio
5. Set up CRON job on MacBook Air: triggers 5 min after each posting time to check for and publish drafts from phone
6. Monitoring: simple notification on post success/failure

**Effort:** Phase 1 is zero build work (just manual posting). Phase 2: Android setup ~2 hours, warming ~3 days (hands-off), uploader adaptation ~2-3 sessions, CRON setup ~1 session. Total Phase 2: ~1 week elapsed, ~6-8 hours active work.

---

### LANE 6: Campaign Intelligence (Gap 10)

**Job:** Track what content performs, identify winning formats, and generate the next batch weighted toward what's working. The feedback loop that turns random posting into a growth machine.

**Decided:** AI agents make decisions autonomously. Daily/weekly summaries surfaced to Kashane. TikTok and Instagram tracked separately.

**Tools:**
- Postiz analytics (built-in, pull via Agent CLI)
- TikTok Creator Analytics (native in-app)
- Instagram Insights (native in-app)

**The methodology (from the reference posts):**
1. Week 1: post all three content styles (lifestyle, tips, catch highlights)
2. End of week 1: agent pulls analytics, ranks by engagement
3. Identify winner (3x+ views vs. others)
4. Week 2+: generate 80% content in winning format, 20% experimental
5. If a new experimental format beats the current winner, pivot
6. Repeat weekly

**Build steps:**
1. Campaign tracker: JSON file in `state/` that logs every post — date, platform, format type, content angle, caption summary, image references, and later: views, likes, comments, shares. Agent updates after each posting cycle.
2. Performance analysis skill: reads campaign tracker → ranks formats by engagement → identifies current winner → generates a content brief for the next batch (80/20 split) → outputs daily/weekly summary for Kashane
3. Brand consistency guidelines doc: per-app document defining color palette, font style, visual tone, caption voice, hashtag set. Prevents the "random Pinterest feed" problem.
4. Competitor monitoring (semi-automated): weekly TikTok search for fishing niche keywords, screenshot top-performing posts, extract patterns. Manual in Phase 1, automatable via Android phone in Phase 2.

**Effort:** Campaign tracker setup ~1 session. Performance analysis skill ~1 session. Brand guidelines ~1 hour per app. Weekly runs ~15 minutes each (mostly automated).

---

### LANE 7: Analytics & Attribution (Gap 11)

**Job:** Connect "someone saw my TikTok" to "someone downloaded my app."

**Decided:** Deferred until product-market fit is validated. Use free built-in tools only for now.

**Phase 1 (now): Free built-in analytics**
- RevenueCat dashboard (free with Lane 1 integration): MRR, trial conversion, churn, LTV — available when paywall activates
- App Store Connect analytics (free): impressions, product page views, downloads, sources — available immediately after launch
- Manual correlation: log "posted TikTok about X at 9AM, got Y downloads between 9AM-12PM" in campaign tracker

**Phase 2 (later): Full attribution**
- [Singular](https://www.singular.net/) — free plan, SKAdNetwork support, handles TikTok + Meta attribution in one SDK
- Alternative: [Tenjin](https://www.tenjin.io/) — built for indie developers, lower-cost entry point
- Deep linking via [Branch](https://www.branch.io/) — track which platform (TikTok bio vs IG bio) drove the click

**Effort:** Phase 1: ~30 minutes setup (comes free with other lanes). Phase 2: ~2-3 hours when the time comes.

---

## Execution Order

Revised 2026-04-09. Timeline is realistic — accounts for App Store review time (~24-48 hours typical), dependency chains, and the fact that content marketing can start before app approval.

```
WEEK 1: Polish & Prep (no submission yet)
├── 🔴 iOS worker: Create PrivacyInfo.xcprivacy (Location + Photos reason declarations)
├── iOS worker: Apply Catchbook brand palette to DesignTokens.swift + AccentColor.colorset
├── iOS worker: Place app icon PNG into Asset Catalog (all required sizes)
├── ✅ iOS worker: Rename project from FishingLogbook → Catchbook (done 2026-04-09)
├── iOS worker: Regenerate .xcodeproj via `xcodegen generate`
├── Lane 2: Create GitHub Pages repo (catchbook-legal) with privacy policy + ToS + support
├── Lane 2: Finalize ASO metadata — keyword research, subtitle, optimized description
├── Lane 2: Research competitors (Fishbrain, FishAngler) — pricing, features, user complaints
├── ✅ Human: Gemini API key created, .env file created (2026-04-09)
├── ✅ Human: TikTok account created, warming in progress
├── Human: Create Instagram account
├── 🔴 Human: Set up Xcode code signing (Apple dev portal → App ID → profiles)
└── Lane 3: Start generating fishing lifestyle content (angle 1) — no app screenshots needed

WEEK 2: Test, Screenshots & Submit
├── iOS worker: Raise test coverage from ~20% → 40%+ (app launch, permissions, integration)
├── iOS worker: Test edge cases (location denied, photo denied, large datasets, empty states)
├── Lane 2: Capture Xcode simulator screenshots (6.7" + 6.5") with brand palette applied
├── Lane 2: Composite screenshots with text overlays for App Store listing
├── iOS worker: Archive build → upload to TestFlight
├── 🔴 Human: Install TestFlight build on physical iPhone, run through full flow
├── iOS worker: Fix any issues found in TestFlight testing
├── Complete submission checklist (remaining items)
├── Submit to App Store (manual release recommended for v1.0)
└── Lane 3: Continue lifestyle content generation, start building Content Factory skill

WEEK 2-3: Content Pipeline (while waiting for App Store review)
├── Lane 3: Build Content Factory skill, generate first week's stockpile (7 posts × 3 slides)
├── Lane 3: Record 2-3 Xcode simulator screen recordings for marketing
├── Human: Manual review of first content batch (quality gate — score images 1-10 for realism)
├── Lane 4: Sign up for Postiz ($29/mo), build Scheduler skill, schedule first week to drafts
├── Lane 6: Create campaign tracker JSON in state/
└── Lane 6: Brand guidelines doc already created → verify slide templates match

WEEK 3-4: Launch Marketing (app approved, go live)
├── Release app on App Store (manual release → flip the switch)
├── Manual posting from phone (1x/day TikTok, 1x/day IG)
├── Lane 6: Pull analytics after day 3, identify early signals
├── Lane 6: Pull analytics after day 7, identify winning format
├── Lane 3: Generate week 2 stockpile weighted toward winner (80/20)
├── Lane 3: Add app demo content (angle 3) now that live app exists
└── If organic < 50 downloads/week by Day 14: evaluate paid TikTok ads ($10/day test)

MONTH 2+: Automate & Scale
├── Lane 1: Ship v1.1 with RevenueCat SDK (wired but paywall hidden)
├── v1.1: Add onboarding flow (3-4 screens showing app value)
├── v1.1: Add in-app review prompt (triggers after 3rd successful trip log)
├── v1.1: Plan push notification strategy (opt-in, weekly, high-value only)
├── Lane 5: Buy Android, set up ADB, fork warming + uploader repos
├── Lane 4: Consider self-hosting Postiz on MacBook Air
├── Lane 6: Weekly autonomous campaign optimization
├── Lane 1: Activate pro tier based on user behavior data (trigger: 100+ active users)
├── Increase posting frequency (2-3x/day) once format is proven
└── Lane 7: Add Singular when traffic justifies it
```

🔴 = items most likely to cause delays if not started immediately

**What if Apple rejects v1.0?** Common rejection reasons for new apps: missing PrivacyInfo.xcprivacy (guaranteed rejection without it), privacy policy URL returns 404, missing screenshot for required device size, crash on reviewer's device. Mitigation: create privacy manifest Week 1, test GitHub Pages URLs after deployment, submit all required screenshot sizes, and verify the archive build on a physical iPhone via TestFlight before submission. Most rejections include specific feedback and turnaround on resubmission is 24-48 hours.

**What if TikTok organic doesn't convert?** Realistic Month 1 estimate: 50-150 downloads from all organic channels combined (TikTok, IG, App Store search). If you're below 50 downloads/week by Day 14, trigger a $10/day TikTok ad test to validate whether the content resonates at scale or needs rework. Alternative channels to explore: Reddit fishing subreddits (r/fishing, r/bassfishing), YouTube fishing creator partnerships, fishing forum sponsorships, Apple Search Ads (free $100 credit for new advertisers).

---

## New Worker Lanes for AGENTS.md

These lanes need to be formally added to the ai-company-os worker architecture:

| Worker | Scope | Lane Doc Location |
|--------|-------|-------------------|
| worker-content | Content generation, image creation, screen recordings, stockpile management | `apps/worker-content/` |
| worker-social | Social media scheduling, posting rules, platform-specific adaptation | `apps/worker-social/` |
| worker-growth | Campaign intelligence, analytics, format testing, competitor monitoring | `apps/worker-growth/` |

These follow the repo conventions in AGENTS.md: single lane of responsibility, structured I/O, policy-bound, observable execution.

---

## Business Strategy Gaps (identified by business review)

These are not engineering tasks — they're strategic planning items that directly affect revenue, positioning, and growth. Each needs a short doc in `docs/products/catchbook/`.

### Competitive Analysis (do Week 1)
No research exists on competing fishing logbook apps. Create `docs/products/catchbook/competitive-analysis.md`:
- Download and test: Fishbrain, FishAngler, BassMaster, Plusinno
- Feature parity table (what they have vs Catchbook)
- Pricing comparison (what they charge, free vs paid tiers)
- Read their 1-star App Store reviews — extract user pain points to exploit
- Key differentiators for Catchbook: privacy (no accounts, no cloud), offline-first, simplicity
- Use findings to sharpen App Store metadata (description, keywords, screenshots)

### Revenue Model (do Week 1-2)
No path from $0 to revenue is documented. Create `docs/products/catchbook/monetization-strategy.md`:
- Define explicit Pro features that DON'T already ship in v1.0 free (current issue: spot recall, filters, share cards are all in the free MVP — what remains for Pro?)
- Set initial Pro pricing (recommendation: $4.99/mo or $29.99/yr based on fishing app category norms)
- Define paywall activation trigger: "Activate when X active users reached" or "Activate on specific date"
- Model revenue scenarios: Conservative (500 downloads/mo, 5% conversion = $125/mo), Realistic (2k/mo = $500/mo), Optimistic (10k/mo = $2,500/mo)
- Decide: lifestyle business ($1-5k/mo) or scale-up ($50k+/mo)? This drives everything.

### Retention Strategy (do for v1.1)
No re-engagement mechanics exist. Plan for `v1.1`:
- **Onboarding:** 3-4 screen walkthrough showing app value (create waterbody → start trip → log catch → view insights)
- **In-app review prompt:** Trigger after 3rd successful trip log. "Enjoying Catchbook?" → Yes → App Store review sheet. No → feedback form.
- **Re-engagement nudges:** Home screen card: "You haven't logged a trip in 7 days — ready to fish?" (contextual, not pushy)
- **Push notifications (opt-in):** Weekly max. Seasonal reminders ("Bass are biting this week"), personal bests ("New PB opportunity: you caught 5lb at Lake X last April")
- **Data safety:** Backup/restore workflow must be prominent. Users who lose data on phone switch will leave 1-star reviews. Plan: either iCloud CloudKit sync or prominent export/import in Settings.

### Keyword Research (do Week 1)
Current keyword list is unresearched guesswork. Before submission:
- Run AppDrift/Apple Search Ads tool for volume + competition data
- Research what keywords Fishbrain and FishAngler rank for
- Identify niche keywords with lower competition: "kayak fishing log", "saltwater catch journal", "bass fishing diary"
- Consider App Store category swap: test Reference (primary) + Sports (secondary) vs current Sports + Reference — whichever surfaces "fishing logbook" searches better

---

## Skills to Build (in repo's canonical skill system)

Per the repo's skill architecture (`skills/canonical/` → `skills/adapters/` → `.claude/skills/`):

| Skill | What It Does | Feeds Into | When |
|-------|-------------|------------|------|
| `privacy-manifest-gen` | Creates PrivacyInfo.xcprivacy with correct reason declarations for Location + Photos APIs | Pre-launch, iOS worker | Week 1 🔴 |
| `brand-palette-apply` | Takes brand-guidelines.md color palette → updates `DesignTokens.swift` (currently teal) + Asset Catalog accent color | Pre-launch, iOS worker | Week 1 |
| `aso-optimizer` | Takes app + positioning docs → generates optimized ASO metadata + screenshot copy | Lane 2, App Store worker | Week 1 |
| `appstore-screenshot-gen` | Captures simulator screenshots at required sizes (6.7" + 6.5") → composites with text overlays using brand palette | Lane 2, App Store worker | Week 2 |
| `content-factory` | Takes app + niche + angle → generates slideshow stockpile (images, captions, hashtags) with rate-limited Gemini calls | Lane 3, Content worker | Week 2-3 |
| `simulator-recorder` | Records Xcode simulator flows → trims to marketing clips | Lane 3, Content worker | Week 2-3 |
| `postiz-scheduler` | Takes content folder → uploads to Postiz → schedules to drafts | Lane 4, Social worker | Week 2-3 |
| `campaign-analyzer` | Reads campaign tracker → identifies winners → generates next batch brief | Lane 6, Growth worker | Week 3-4 |
| `revenuecat-integration` | Integrates RevenueCat SDK into any iOS app via `project.yml` (XcodeGen) with inactive paywall | Lane 1, iOS worker | Month 2 (v1.1) |

---

## Budget Summary

| Item | Cost | When |
|------|------|------|
| Apple Developer Program | $99/yr (already active) | Ongoing |
| RevenueCat | $0 (free until $2.5k/mo) | Month 2 (v1.1) |
| Gemini API | $0 (free tier) | Week 1 ✅ |
| AppDrift (ASO) | $0 (free plan) | Week 1 |
| App Store Connect | $0 (included in dev account) | Week 1 |
| GitHub Pages (legal) | $0 (free) | Week 1 |
| Postiz hosted | $29/mo | Week 2-3 |
| Cheap Android (Phase 2) | ~$50 one-time | Month 2 |
| **Total to launch (v1.0)** | **$0 new spend** | |
| **Total at content scheduling** | **$29/mo** | |
| **Total at full automation** | **$29/mo + $50 one-time** | |

---

## Open Items

### Human Action Required

| # | Item | Status | Blocker? |
|---|------|--------|----------|
| 1 | ~~Decide final app name~~ | **Catchbook** (2026-04-08) | — |
| 2 | ~~Set up Gemini API key~~ | Key created, `.env` file created (2026-04-09) | — |
| 3 | ~~Create TikTok account~~ | Created, warming (2026-04-09) | — |
| 4 | ~~Provide app icon~~ | Icon provided (2026-04-08), palette extracted | — |
| 5 | **Create Instagram account** | Pending | Not a blocker for v1.0 — TikTok launches first |
| 6 | **Sign up for Postiz** | Deferred a few days — manual posting first | Blocks Lane 4 scheduling, but manual posting works without it |
| 7 | **Set up Xcode code signing** | Pending | **HARD BLOCKER** for App Store submission. Needs: Apple dev portal → create App ID for `io.aicompanyos.products.fishinglogbook` → distribution provisioning profile → configure in Xcode |
| 8 | **Choose release type** | Pending | Recommend: manual release for v1.0 (review before going live) |
| 9 | ~~Create `.env` file~~ | Created with Gemini key (2026-04-09) | — |

### Worker Tasks (no human decision needed)

| # | Task | Target File(s) | Priority |
|---|------|----------------|----------|
| 10 | 🔴 Create PrivacyInfo.xcprivacy | New file at project root, add to `project.yml` | **Week 1 — REJECTION BLOCKER** |
| 11 | Apply Catchbook brand palette | `DesignTokens.swift` (currently `.teal`), `AccentColor.colorset` (dark mode variants too) | **Week 1 — do before screenshots** |
| 12 | Place app icon in Asset Catalog | `Sources/Assets.xcassets/AppIcon.appiconset/` + generate all required sizes | Week 1 |
| 13 | ~~Update project.yml display name~~ | Done (2026-04-09) — renamed to Catchbook across all targets | — |
| 14 | Regenerate .xcodeproj | Run `xcodegen generate` to sync pbxproj with renamed project.yml | Week 1 |
| 15 | Create GitHub Pages repo | `catchbook-legal` → privacy policy + ToS + support page | Week 1 |
| 16 | Competitive analysis | Research Fishbrain, FishAngler, BassMaster → `competitive-analysis.md` | Week 1 |
| 17 | Keyword research | AppDrift/Apple Search Ads → optimize keyword list, test category placement | Week 1 |
| 18 | Update metadata draft | `appstore-metadata-draft.md` → pricing "Free", finalize subtitle, add URLs | Week 1-2 |
| 19 | Raise test coverage to 40%+ | Add: app launch test, permission denial tests, integration flow test | Week 2 |
| 20 | Test edge cases | Location denied, photo denied, large datasets, empty states → document results | Week 2 |
| 21 | Generate App Store screenshots | Xcode simulator captures → composite with text overlays (6.7" + 6.5") | Week 2 |
| 22 | Archive + TestFlight validation | Build → archive → TestFlight → test on physical iPhone | Week 2 |
| 23 | Add unit tests for new tools | `gemini_images.py` and `postiz_client.py` need tests in `tests/python/tools/` | Week 2-3 |
| 24 | Write monetization strategy doc | Revenue model, Pro features, pricing, activation trigger → `monetization-strategy.md` | Week 1-2 |

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **Apple rejects v1.0** | Delays launch 2-5 days | Medium (new developer, first app) | Ship clean binary (no unused SDKs), test privacy policy URLs before submission, verify archive build on physical device, include thorough review notes |
| **Gemini free tier hits daily quota** | Content generation stalls mid-batch | Low-Medium | Monitor quota usage, implement retry-with-backoff in content factory, have 1-week content buffer stockpiled |
| **TikTok shadowbans new account** | Marketing content gets zero reach | Medium (new account + marketing content) | Warming period (3+ days human engagement before any marketing posts), start with pure lifestyle content (not overtly promotional), manual posting from phone (not API) |
| **AI-generated images look obviously fake** | Content performs poorly, damages brand | Medium | Quality gate on every batch, iterate prompt templates aggressively in week 1, mix in real Xcode screenshots for credibility |
| **MacBook Air is single point of failure** | All automation stops if hardware dies | Low (but catastrophic) | Keep content stockpiled 1-2 weeks ahead, Postiz cloud scheduling survives Mac downtime, all code is in git |
| **Code signing setup takes longer than expected** | Delays submission | Medium (first time) | Start code signing in Week 1, not Week 2. Apple's provisioning portal can be confusing — budget extra time |
| **Missing PrivacyInfo.xcprivacy** | Guaranteed rejection | High (file doesn't exist yet) | Create in Week 1 before any build attempt. iOS 17 hard requirement since 2024. |
| **Users lose data on phone switch** | 1-star reviews, churn | Medium | Plan backup/restore workflow for v1.1. Export exists but not prominent. Consider iCloud CloudKit sync for v1.2. |
| **Low retention (no re-engagement)** | Users download but never return | High (no onboarding, no notifications) | v1.0 ships without retention features. v1.1 adds onboarding, review prompt, nudges. Accept Month 1 retention will be low. |
| **Organic-only acquisition stalls** | TikTok doesn't convert to downloads | Medium-High | Set trigger: if < 50 downloads/week by Day 14, test $10/day TikTok ads. Have alternative channels ready (Reddit, Apple Search Ads). |

---

## Code Wired Up (as of 2026-04-09)

| Module | Location | Status |
|--------|----------|--------|
| `.env` secrets pattern | `.env.example`, `.gitignore`, `packages/config/settings.py` | ✅ Ready — `.env` created with Gemini key |
| Gemini image generation client | `packages/tools/content_tools/gemini_images.py` | Ready — generates single images, 3-slide sets, and weekly stockpiles |
| Postiz scheduling client | `packages/tools/social_tools/postiz_client.py` | Ready — media upload, draft post creation, batch scheduling with manifest |
| Project rename | All files, dirs, targets renamed FishingLogbook → Catchbook | ✅ Done (2026-04-09) — needs `xcodegen generate` to sync pbxproj |

---

*v3 (revised 2026-04-09) — All planning decisions resolved. Execution started. Reviewed by: (1) PM/staff-eng pass — risk table, realistic timeline, deferred RevenueCat to v1.1, code signing hard blocker, rejection contingency. (2) iOS dev pass — PrivacyInfo.xcprivacy critical blocker, TestFlight validation required, test coverage gap, edge case testing. (3) Business manager pass — revenue model undefined, competitive analysis missing, retention strategy needed for v1.1, organic acquisition backup plan, keyword research required. Full project rename from fishing-logbook to catchbook completed.*
