# After Plans — Founder Decisions Needed Before Submission

Four decisions were blocking the App Store lane (per the LAUNCH_PLAN.md
handoff checklist). Three are now approved (subtitle, age rating,
moderation operating path). The fourth — initial seeded launch contexts —
is intentionally deferred while the founder explores a user-built context
model that may replace pre-seeding entirely. See section 3.

Last updated: 2026-04-27

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

**Approved:** [x]   **Choice:** Keep the moment going  *(approved 2026-04-27)*

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

**Approved:** [x]   **Choice:** [x] 17+   [ ] 12+   [ ] Other: ______  *(approved 2026-04-27)*

---

## 3. Initial Seeded Launch Contexts — DEFERRED

**Status (2026-04-27):** deferred. The founder is exploring a different
shape of the same problem — instead of the platform pre-seeding 3–5
hand-picked contexts, each new user goes through a brief onboarding
where they declare their most common recurring activities and are then
prompted to either join an existing context or invite people to fill a
new one. The pre-seeded model below is preserved as the fallback if the
user-built model doesn't pan out.

This needs a brainstorm before any of it ships. Open questions worth
working through there:

- Cold-start: a brand new user with no friends on the app has an empty
  feed and no context to join. Does the onboarding gracefully convert
  them into context-creators with shareable invites, or do we still need
  a thin layer of platform-curated public contexts as a safety net?
- Discovery: how does a user find existing contexts they could join
  without breaking the bounded-visibility promise?
- De-duplication: two users in the same city declare "Wednesday Run
  Club" — does the app surface this and let them merge, or do parallel
  contexts with the same name coexist?
- Quality floor: if context creation is fully user-driven, what stops
  someone from creating a low-quality or bad-actor context? Is creation
  rate-limited, invite-only, or moderated post-hoc?
- Where the "seed" energy comes from: in the pre-seeded model, the
  founder vouches for each context. In the user-built model, that
  vouching is distributed — works only if the very first wave of users
  is high-quality.

**Approved:** [ ] *(deferred, pending brainstorm — see open questions above)*

---

### 3 (fallback). Initial Seeded Launch Contexts — pre-seeded model

Kept here as a fallback if the user-built model doesn't pan out.

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

**Approved:** [x] *(approved 2026-04-27 — recommendation accepted in full)*

**Triage owner:** Kashane (founder)
**SLA (severe):** acknowledge within 24 hours, action within 48 hours
**SLA (other):** acknowledge within 72 hours
**Backup owner / pause plan when triage owner unavailable:** TBD — at any
extended unavailability, either pre-arrange a backup triage owner or
pause the app's discoverability before the gap. To be revisited before
TestFlight expands beyond a small invite-only group.

---

## Sign-Off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Founder | Kashane | 2026-04-27 | Approved sections 1, 2, 4. Section 3 deferred pending brainstorm on a user-built context model. |

Status of downstream updates:

- [x] [APP_STORE_METADATA_DRAFT.md](APP_STORE_METADATA_DRAFT.md) —
  subtitle ("Keep the moment going") and age rating (17+) already match
  the approved decisions; verified 2026-04-27
- [ ] [APP_STORE_METADATA_DRAFT.md](APP_STORE_METADATA_DRAFT.md) — fill
  in the demo account credentials and the App Review contact info
  (founder name + phone). Email = ksakhakorn@gmail.com (the moderation
  triage owner is the same as the support contact)
- [x] [LAUNCH_PLAN.md](LAUNCH_PLAN.md) — three of four handoff checklist
  items checked off; launch contexts intentionally left unchecked
- [ ] Seeded contexts decision pending the brainstorm on the user-built
  context model. If/when the pre-seeded model is chosen instead, those
  contexts get inserted via a migration similar to `seed.sql` after the
  cloud Supabase project is provisioned
- [x] [legal/PRIVACY_POLICY.md](legal/PRIVACY_POLICY.md) and
  [legal/SUPPORT.md](legal/SUPPORT.md) — already use
  ksakhakorn@gmail.com; no sync needed
