# App Store Metadata Draft: After Plans

This is a field-by-field draft for App Store Connect. Each field maps directly to an App Store Connect input. Copy into ASC when the App Store lane begins.

## App Information

| Field | Value |
|-------|-------|
| App name | After Plans |
| Subtitle | Keep the moment going |
| Primary category | Social Networking |
| Secondary category | Lifestyle (optional) |
| Content rights | Does not contain third-party content |
| Age rating | 17+ |

## Pricing

| Field | Value |
|-------|-------|
| Price | Free |
| In-app purchases | None in v1 |

## Version Information

### Promotional Text (170 chars, editable without review)

Done with dinner but not ready to call it a night? After Plans shows what is happening next with people you know or are already around. Join with one tap.

### Description

After Plans is for the moment right after a real-world activity — when the energy is still there but no one wants to be the one to text the group chat.

**See what is happening after**

Open After Plans after a dinner, class, meetup, or hangout. The app shows you what people around you or people you know are planning next — ranked by relevance, not random chance.

**Join with one tap**

Skip the awkward "so, what now?" text. See a plan that looks good, tap Join, and you are in. No group chat negotiation. No pressure to commit before you are ready — signal interest first, join when it feels right.

**Start what is next your way**

Got an idea? Create a plan in seconds. Pick an exact spot, suggest a default, or just put out an open intent and let the group converge. The app does the coordination, not you.

**People you know or are already around**

After Plans is not a stranger-matching app. Plans are bounded to your context — same activity, same circle, same evening. You will see people you recognize, people who were just there, and people your friends already trust.

**Low pressure, real momentum**

Plans move from forming to confirmed as people join. You can see the momentum building. When enough people are in, the plan locks and you get a simple handoff to continue the conversation however you want — text, group chat, or just showing up.

**Your safety, built in**

Report or block anyone. See who can see each plan. Visibility is bounded by default — not public, not broadcast, not discoverable by strangers across town. Plans stay in context.

### What is New

After Plans v1 — see what is happening after, join with one tap, and keep the momentum going with people you know.

### Keywords (100 chars max)

```
after,plans,continuation,join,nearby,social,group,meetup,what next,after dinner,after class
```

### Support URL

https://kashane1.github.io/afterplans-support/

Canonical source: [legal/SUPPORT.md](legal/SUPPORT.md). Published mirror at
[github.com/kashane1/afterplans-support](https://github.com/kashane1/afterplans-support).
Swap to a custom-domain URL when one is purchased.

### Marketing URL

TBD — optional for App Store Connect; worth standing up once a domain exists.

## Screenshots

See SCREENSHOT_PLAN.md for the full storyboard. Minimum 3, recommended 5.

Required device sizes:

- iPhone 6.7" (iPhone 15 Pro Max / 16 Pro Max) — required
- iPhone 6.1" (iPhone 15 Pro / 16 Pro) — recommended
- iPad Pro 12.9" — only if iPad version ships

## App Review Information

### Review Notes

After Plans is a social coordination app for the moment after a real-world activity ends (dinner, class, meetup, event). It helps users see and join what their friends or same-context acquaintances are planning next.

Key safety and trust features:

- Non-anonymous: users have a first name, photo, and verified contact method
- Bounded visibility: plans are scoped to context (same activity, same circle, invite-only) — not a public city-wide feed
- Report and block: users can report plans or users for harassment, hate, spam, sexual misuse, or unsafe behavior, and can block users immediately
- Moderation: all reports route to a moderation review queue with documented triage procedures
- No anonymous chat: the app does not include open DMs or anonymous messaging
- No dating features: no matching, swiping, or romantic framing

The app is in the Social Networking category because it coordinates social continuation among people who share real-world context, not because it connects strangers.

### Demo Account

Provide a test account with pre-seeded plans and context so the reviewer can experience the core loop without needing other live users.

| Field | Value |
|-------|-------|
| Username | TBD |
| Password | TBD |

### Contact Information

| Field | Value |
|-------|-------|
| First name | TBD |
| Last name | TBD |
| Phone | TBD |
| Email | TBD |

## App Privacy

### Privacy Policy URL

https://kashane1.github.io/afterplans-privacy/

Canonical source: [legal/PRIVACY_POLICY.md](legal/PRIVACY_POLICY.md). Published
mirror at [github.com/kashane1/afterplans-privacy](https://github.com/kashane1/afterplans-privacy).
Swap to a custom-domain URL when one is purchased.

### Privacy Nutrition Labels

Reconciled 2026-04-25 against the actual shipping posture (no location, no
contacts, no photos, no third-party analytics; identity-light backend on
Supabase anonymous auth).

| Data type | Collected | Purpose | Linked to identity |
|-----------|-----------|---------|-------------------|
| Name (first name only) | Yes | App functionality | Yes |
| User content (plan titles, descriptions, place suggestions, report notes) | Yes | App functionality | Yes |
| User ID (server-issued UUID) | Yes | App functionality | Yes |

Data **not** collected:

- Email address
- Phone number
- Physical address
- Photos, video, audio
- Contacts
- Precise or coarse location
- Health, fitness, financial, sensitive info
- Browsing history, search history
- Device IDs, advertising IDs
- Diagnostics, performance, crash data (beyond Apple's standard, which the
  user opts into via iOS settings — we do not run our own crash analytics)

### Data Use Declarations

- Data is not sold to data brokers or advertising networks
- Data is not used for tracking across other apps or websites
- No third-party advertising or analytics SDKs
- No location data of any kind

## Age Rating Questionnaire Answers

| Question | Answer |
|----------|--------|
| Cartoon or fantasy violence | None |
| Realistic violence | None |
| Sexual content or nudity | None |
| Profanity or crude humor | Infrequent or mild (UGC) |
| Alcohol, tobacco, or drug references | Infrequent or mild (social context) |
| Simulated gambling | None |
| Horror or fear themes | None |
| Medical or treatment information | None |
| Unrestricted web access | No |

These answers should yield a 12+ or 17+ rating. **Decision (2026-04-27): select 17+** to match the eligibility posture in TRUST_SAFETY_GUARDRAILS.md and the user-facing language in legal/PRIVACY_POLICY.md. See [founder-decisions-needed.md](founder-decisions-needed.md) section 2.

## Pre-Submission Checklist

- [ ] Founder approves subtitle
- [ ] Founder approves age rating
- [ ] App icon finalized and exported at required sizes
- [ ] Screenshots captured on required device sizes
- [ ] Support URL live
- [ ] Privacy policy URL live
- [ ] Marketing URL live (optional)
- [ ] Demo account created and seeded
- [ ] Privacy labels match actual data collection
- [ ] Review notes finalized
- [ ] Contact information filled in
- [ ] Build uploaded via Xcode or Transporter
