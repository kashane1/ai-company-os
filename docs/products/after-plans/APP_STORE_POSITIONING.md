# App Store Positioning: After Plans

## Positioning Summary

After Plans is a join-first social continuation app for the moment after a real-world activity ends. The listing must clearly communicate three things:

1. what problem it solves — coordination friction in the after moment
2. when to use it — right after a shared activity, when people are still nearby
3. why it is different — bounded trust, people you know, no stranger-meetup framing

## Category

Primary: **Social Networking**

The product is social coordination, not event ticketing or productivity. Social Networking better matches the continuation and group-formation mechanic than Lifestyle or Entertainment.

Secondary (optional): Lifestyle — only if App Review suggests it.

## App Name

**After Plans**

Rationale: short, descriptive, immediately communicates the timing wedge. The name answers "when" rather than "what" — this is the differentiator.

## Subtitle

Recommended: **Keep the moment going**

Alternates (ranked):

1. Keep the moment going
2. See what is next after
3. Join what is happening after

Decision rationale: "Keep the moment going" leads with the emotional hook and avoids needing the user to already understand the mechanic. It is warmer than the informational alternates and does not risk dating or stranger interpretation.

Do not use: "Meet people nearby", "Find your next hangout", "Make new friends", or any phrasing that implies stranger discovery.

## Age Rating

Recommended: **17+**

Rationale: the app involves real-world meetup coordination with semi-known people. 17+ is the safest App Review posture for v1. It avoids youth-safety scrutiny, simplifies moderation policy, and aligns with the TRUST_SAFETY_GUARDRAILS.md recommendation for 18+ eligibility. The 17+ App Store rating is the closest available threshold.

This decision should be confirmed by the founder before submission.

## Messaging Hierarchy

### Primary message

Make the next plan easier right after the current one ends.

### Supporting messages (in priority order)

1. See what is happening after — context-aware discovery of what is next
2. Join with one tap — join-first, low commitment, no awkward group text
3. Start what is next your way — create exact plans, loose plans, or open intents
4. People you know or are already around — bounded trust, not stranger matching

### Messages to avoid

- dating-adjacent language (meet someone, connect with locals)
- friend-finder framing (make friends, find your crew)
- anonymous social framing (meet people nearby, local chat)
- safety overclaiming (safest way to meet people)
- loneliness framing (never be alone, always have plans)

## App Store Description

### Short description (promotional text, 170 chars)

Done with dinner but not ready to call it a night? After Plans shows what is happening next with people you know or are already around. Join with one tap.

### Full description (4000 char limit)

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

### What is New (first version)

After Plans v1 — see what is happening after, join with one tap, and keep the momentum going with people you know.

## Keywords

Primary keyword set (100 character limit):

```
after,plans,continuation,join,nearby,social,group,meetup,what next,after dinner,after class
```

Rationale: targets the timing wedge ("after"), the mechanic ("join", "plans"), and the context anchors ("after dinner", "after class"). Avoids "dating", "meet people", "friends", and "chat" to prevent category confusion.

## Screenshot Story

See SCREENSHOT_PLAN.md for the full per-screenshot storyboard.

Summary narrative arc:

1. emotional hook — the moment deserves to continue
2. context-aware discovery — see what is next
3. join-first action — one tap, no pressure
4. create your own — three creation modes
5. bounded trust — people you know, not strangers

## Review Notes

Draft review note for App Store submission:

---

After Plans is a social coordination app for the moment after a real-world activity ends (dinner, class, meetup, event). It helps users see and join what their friends or same-context acquaintances are planning next.

Key safety and trust features:

- Non-anonymous: users have a first name, photo, and verified contact method
- Bounded visibility: plans are scoped to context (same activity, same circle, invite-only) — not a public city-wide feed
- Report and block: users can report plans or users for harassment, hate, spam, sexual misuse, or unsafe behavior, and can block users immediately
- Moderation: all reports route to a moderation review queue with documented triage procedures
- No anonymous chat: the app does not include open DMs or anonymous messaging
- No dating features: no matching, swiping, or romantic framing

The app is in the Social Networking category because it coordinates social continuation among people who share real-world context, not because it connects strangers.

A test account is available upon request.

---

## Privacy Labels

Required App Store privacy nutrition labels (based on MVP feature set):

| Data type | Collection | Usage | Linked to identity |
|-----------|-----------|-------|--------------------|
| Name | Yes | App functionality | Yes |
| Email or phone | Yes | App functionality, account | Yes |
| Photos | Yes (profile) | App functionality | Yes |
| Coarse location | Yes (when in use) | App functionality | Yes |
| User content | Yes (plan text) | App functionality | Yes |
| Identifiers | Yes (device ID) | Analytics | No |

Not collected: precise location (only coarse), health data, financial data, browsing history, search history, contacts (optional import only).

The privacy label should emphasize:

- location is used only to anchor context, not to broadcast position
- no data is sold or shared with advertising networks
- profile data is minimal by design

## What Is Not In This App

This framing exists to preempt App Review and user misinterpretation:

- Not a dating app — no matching, no romantic framing, no swipe mechanic
- Not a stranger-meetup app — plans are bounded to context, not discoverable city-wide
- Not a group chat app — the app coordinates plans, then hands off to text
- Not a public events marketplace — plans are contextual and bounded, not listed publicly
- Not anonymous — real identity required, no anonymous handles

## Metadata Preparation Checklist

- [x] app name decided
- [x] subtitle recommended with alternates
- [x] category selected
- [x] age rating recommended
- [x] description drafted (short and full)
- [x] keyword set drafted
- [x] screenshot narrative defined (see SCREENSHOT_PLAN.md)
- [x] review notes drafted
- [x] privacy label mapping started
- [x] "what is not" framing documented
- [ ] founder approval on subtitle
- [ ] founder approval on age rating
- [ ] final screenshot captures (requires live build)
- [ ] app icon direction confirmed
- [ ] test account prepared for review
- [ ] privacy label finalized against actual data collection
