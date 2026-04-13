# Catchbook — Content Taxonomy

Source of truth for content archetype definitions, mix targets, and scheduling
rules. The GTM worker uses this file to classify, score, and balance backlog
items.

## Scoring weights

| Dimension | Weight | What it measures |
|---|---|---|
| Virality | 0.30 | Engagement potential — shares, saves, comments |
| Niche fit | 0.25 | Audience specificity — do anglers care? |
| Content gap | 0.20 | Underserved by existing creators |
| Timeliness | 0.15 | Relevant right now |
| Product alignment | 0.10 | Natural product connection (lowest weight intentionally) |

Composite = V(0.30) + NF(0.25) + CG(0.20) + T(0.15) + PA(0.10)

---

## Archetypes

### 1. Pain Point — 20% target

**Trigger:** Frustration, recognition of a problem the audience lives with.
**Primary engagement:** Comments, saves, DMs.
**Voice note:** Name the pain with specificity. Don't exaggerate — anglers smell
manufactured outrage. Let the audience confirm in the comments.
**Product proximity:** High — pain points are where the product naturally enters.
Product mentions allowed when the pain directly maps to a feature.

**Example hooks:**
- "Your secret spots aren't safe — and anglers know it" (Score: 78)
- "What did I throw last spring at this spot? I can't remember" (Score: 77)
- "Why every angler starts a log and quits within a month" (Score: 75)

---

### 2. Value / Educational — 20% target

**Trigger:** Desire to improve, learn, or gain an edge.
**Primary engagement:** Saves, follows, shares to fishing buddies.
**Voice note:** Be the knowledgeable friend, not the professor. Use the lexicon.
Name the specific technique, species, and condition — vague tips feel generic.
**Product proximity:** Medium — product mentions allowed when a tip naturally
connects to logging or recall. Never force.

**Example hooks:**
- "The Excel angler — why serious fishermen use spreadsheets" (Score: 68)
- "Dawn vs dusk — when bass actually bite" (Score: 65)
- "3 lures that work when nothing else does" (Score: 64)

---

### 3. Debate / Hot Take — 15% target

**Trigger:** Tribal identity, strong opinion, desire to defend a position.
**Primary engagement:** Comments (3x volume vs. educational), duets/stitches.
**Voice note:** State the position clearly but don't be mean. Respect both sides.
Let the audience debate in comments. Never insult a fishing style or species
preference.
**Product proximity:** Low — product mentions only if the debate directly relates
to logging, privacy, or spot sharing. Never shoehorn.

**Example hooks:**
- "Fishbrain used to be free — now it's a money grab" (Score: 72)
- "Is social media ruining fishing?" (Score: 68)
- "Forward-facing sonar is changing fishing — is that good?" (Score: 67)

---

### 4. Identity / Tribal — 10% target

**Trigger:** Belonging, self-identification, "this is MY people."
**Primary engagement:** Shares, follows, profile visits.
**Voice note:** Celebrate the identity without gatekeeping. Bank anglers, kayak
anglers, dads who fish — all valid. The tribe is anyone who takes the water
seriously.
**Product proximity:** Medium — "the angler who logs" is an identity that maps
naturally to the product. Use it sparingly.

**Example hooks:**
- "Bank fishing is real fishing — stop gatekeeping from your $60K boat" (Score: 75)
- "The angler who logs beats the angler who guesses" (Score: 74)

---

### 5. Aspirational / Aesthetic — 10% target

**Trigger:** Desire, admiration, "I want that moment."
**Primary engagement:** Shares, saves, follows. Instagram-dominant.
**Voice note:** Let the image or moment carry the emotion. Caption should be
understated — quiet pride, not hype. Golden hour, trophy bass, clean gear.
**Product proximity:** Medium — PB stories and catch memories tie naturally to
the product's PB tracking feature.

**Example hooks:**
- "The PB that changed everything" (Score: 70)
- "Their first fish — the moment that hooks them for life" (Score: 68)

---

### 6. Humor / Relatable — 10% target

**Trigger:** Recognition, self-deprecation, shared frustration.
**Primary engagement:** Shares, comments. Very high TikTok share rate.
**Voice note:** Self-deprecating, never mean. Laugh with anglers, not at them.
Skunked trips, tangled line, the one that got away — universal.
**Product proximity:** Medium — skunked trip content maps directly to the
logging feature. "I got skunked and it still counts" is on-brand.

**Example hooks:**
- "I got skunked again — and it still counts" (Score: 72)

---

### 7. Seasonal / Timely — 10% target

**Trigger:** Urgency, FOMO, "this is happening RIGHT NOW."
**Primary engagement:** Saves, shares, comments asking for local detail.
**Voice note:** Time-specific content needs a confident, insider voice. Reference
specific water temps, spawn stages, and moon phases. Generic seasonal content
("spring is here!") is noise.
**Product proximity:** High — "your log from last spring tells you what to throw"
is the natural bridge. Pre-spawn and fall turnover are peak product-alignment
windows.

**Example hooks:**
- "Pre-spawn bass — the 3-week window where your log matters most" (Score: 77)
- "Fall turnover — the second-best bite window of the year" (Score: 73)

---

### 8. Behind-the-Scenes / Process — 5% target

**Trigger:** Curiosity, transparency, insider access.
**Primary engagement:** Saves, follows, DMs.
**Voice note:** Show the work, not the polish. Raw data, real patterns, honest
analysis. This archetype is the biggest content gap in fishing — no major
creator shows what systematic logging actually reveals.
**Product proximity:** Very high — this is the unique Catchbook content angle.
Data storytelling is the product in action.

**Example hooks:**
- "My 6-month fishing data revealed a pattern I never expected" (Score: 80)

---

## Mix rules

1. **Never 3+ of the same archetype in a row** on any platform.
2. **Weekly minimum:** At least 1 Debate/Hot Take + 1 Identity/Tribal post.
3. **Seasonal content overrides** the calendar when real-world events are active
   (pre-spawn, fall turnover, Bassmaster Classic, tournament weeks).
4. **Product mentions** are allowed only in Pain Point and Value/Educational
   posts — and only when the connection is natural. Debate, Humor, and
   Aspirational posts must never feel like ads.
5. **Campaign Zero** (pre-launch): No product mentions in any archetype. Pure
   audience building.
6. **Campaign One** (post-launch): Product mentions follow proximity rules above.
