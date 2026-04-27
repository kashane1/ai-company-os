# After Plans — Founder Decisions Needed Before Submission

Four decisions are blocking the App Store lane (per the LAUNCH_PLAN.md
handoff checklist). Each is summarized below with a recommendation and
the trade-offs you need to weigh.

This document is designed so you can sit down for 15 minutes and approve
all four in one pass. Mark your decision in the "Approved" box at the
bottom of each section. Sign and date at the end.

Last updated: 2026-04-26

---

## 1. App Store Subtitle

**The question:** What two-line phrase appears under "After Plans" in the
App Store?

**Recommendation:** **"Keep the moment going"**

**Why:** Reads as warm and continuation-focused without being a feature
list. Already woven through the onboarding and the App Store description
draft, so the brand voice stays coherent.

**Alternatives, ranked:**

1. Keep the moment going  *(recommended)*
2. See what is next after
3. Join what is happening after

**Trade-offs to weigh:**

- "Keep the moment going" is the most evocative; reviewers and users won't
  immediately know what the app does from the subtitle alone.
- "See what is next after" is more functional but starts to read like
  feature copy.
- "Join what is happening after" leans into the action but is the longest
  and feels imperative.

**Constraint:** App Store subtitle limit is 30 characters. All three
options are within budget ("Keep the moment going" is 21 chars).

**Approved:** [ ]   **Choice:** ____________________

---

## 2. Age Rating

**The question:** What age rating do we declare on App Store Connect?

**Recommendation:** **17+**

**Why:** After Plans coordinates real-world meetups between semi-known
people. 17+ is the safest App Review posture for v1: it sidesteps youth-
safety scrutiny, simplifies moderation policy, and matches the eligibility
intent in TRUST_SAFETY_GUARDRAILS.md (which favored 18+; 17+ is the
nearest App Store threshold). The privacy policy already declares the app
is intended for users 17 and older.

**Alternative:** **12+** with explicit youth safeguards.

**Trade-offs to weigh:**

- **17+** is more conservative. Possibly limits organic reach. Cleaner
  review path. No need to argue youth-safety design with Apple.
- **12+** opens a larger user base but requires stronger youth-safety
  defaults (stricter visibility, age-gated invite flows, moderation SLA),
  more complex App Privacy disclosures, and likely a longer review.

**Approved:** [ ]   **Choice:** [ ] 17+   [ ] 12+   [ ] Other: ______

---

## 3. Initial Seeded Launch Contexts

**The question:** Which 3–5 real-world communities or groups should be
seeded as the very first contexts in the production database?

**Why this matters:** The app is bounded — a fresh user with no shared
context sees an empty feed. Seeded contexts are the first surface where
the app "works" out of the box for someone who downloads from the App
Store cold.

**Recommendation:** Pick 3–5 contexts that satisfy all of these:

1. **You can vouch for them personally** (you know an organizer or
   regular). This matters because the very first wave of plans needs to
   come from real people, not synthetic seeds.
2. **They have weekly or higher cadence.** A monthly meetup gives one
   opportunity per month for the app to feel useful.
3. **They are local to a single city** so the proximity heuristics work
   without map UI.
4. **They cover different "moods"**: at least one class/cohort, one
   recurring social meetup, one community/event.

**Examples to consider** (replace with your own):

- A pottery / ceramics class you've taken
- A weekly run club you know an organizer of
- A monthly product/design meetup in your city
- A bouldering gym's open-gym night
- A book club or recurring discussion group

**Trade-offs to weigh:**

- **Too few (1–2 contexts):** brittle — if no one starts a plan in the
  first week, the app feels dead.
- **Too many (10+):** thinly populated feeds; signals to early users that
  the app is broader than it actually is.
- **Strangers to you:** outreach is slower, harder to debug if a context
  doesn't catch on.

**Operationally:** each context needs (a) a title, (b) a venue name,
(c) a one-line trust note, and (d) a couple of seeded `context_members`
who agree to be the first joiners. Item (d) is the hardest — it requires
real conversations with real people before launch.

**Approved:** [ ]

**Contexts (list 3–5 with names + a sentence each):**

1. ________________________________________________________
2. ________________________________________________________
3. ________________________________________________________
4. ________________________________________________________
5. ________________________________________________________

---

## 4. Moderation Operating Path

**The question:** When a user files a report, who reviews it, on what
SLA, and what actions do they take?

**Why this matters:** Apple's App Review Guideline 1.2 (UGC) requires a
documented moderation flow. The TRUST_SAFETY_GUARDRAILS.md doc commits to
"all reports route to a moderation review queue with documented triage
procedures" — that promise needs an owner before the app ships.

**Recommendation (v1, indie posture):**

- **Triage owner:** you (the founder), checked once per day.
- **Tooling:** a saved query in Supabase Studio against
  `public.reports`, ordered by `created_at desc`. No custom dashboard for
  v1.
- **SLA:**
  - Severe (harassment, hate, sexual misuse, unsafe behavior):
    acknowledge within 24 hours, action within 48 hours.
  - Other (spam, dating misuse): acknowledge within 72 hours.
- **Actions available:**
  1. Dismiss with no action.
  2. Warn (out-of-band, via the support email).
  3. Soft-suspend (temporarily hide all of a user's plans).
  4. Hard-block at the auth layer (delete profile and all plans).
- **Escalation:** for anything ambiguous, default to soft-suspend
  + reach out via support email before hard action.
- **Logging:** keep a private spreadsheet (or a follow-on `moderation_actions`
  table later) noting each report, the action taken, and the reasoning.

**Trade-offs to weigh:**

- This is **manual and won't scale beyond a few reports a week.** That's
  appropriate for v1 with seeded contexts. Reassess at the first sign of
  10+ reports/week or any incident that would need faster turnaround.
- The 24/48-hour SLA is **a commitment we have to actually meet.** If
  you're going to be unreachable for a stretch (travel, etc.), either
  pause the app's discoverability or pre-arrange a backup triage owner.
- Hard-block is **irreversible to the user**; document the reasoning
  every time.

**Approved:** [ ]

**Triage owner:** ____________________
**SLA (severe):** ____________________
**SLA (other):** ____________________
**Backup owner / pause plan when triage owner unavailable:** ____________________

---

## Sign-Off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Founder | | | |

Once all four sections are approved, update:

- [ ] [APP_STORE_METADATA_DRAFT.md](APP_STORE_METADATA_DRAFT.md) —
  subtitle, age rating, age-rating questionnaire confirmation
- [ ] [APP_STORE_METADATA_DRAFT.md](APP_STORE_METADATA_DRAFT.md) — fill
  in the demo account credentials and contact info from the moderation
  triage owner
- [ ] [LAUNCH_PLAN.md](LAUNCH_PLAN.md) — check off the four handoff
  checklist items
- [ ] Seeded contexts inserted into the production Supabase project
  (after it's provisioned) via a migration similar to `seed.sql`
- [ ] [legal/PRIVACY_POLICY.md](legal/PRIVACY_POLICY.md) and
  [legal/SUPPORT.md](legal/SUPPORT.md) — sync the support email if it
  changes from the placeholder
