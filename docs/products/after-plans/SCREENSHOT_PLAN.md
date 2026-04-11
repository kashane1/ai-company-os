# Screenshot Plan: After Plans

## Purpose

This document maps each App Store screenshot to a specific app screen, headline, caption, and purpose. It is designed so the App Store lane can produce screenshot assets directly from this spec.

## Screenshot Requirements

- Minimum 3, maximum 10 screenshots per device size
- Recommended: 5 screenshots for launch
- Required device: iPhone 6.7" (iPhone 15 Pro Max or 16 Pro Max)
- Recommended device: iPhone 6.1" (iPhone 15 Pro or 16 Pro)
- Format: PNG or JPEG, no alpha channel
- Orientation: portrait

## Narrative Arc

The five screenshots tell a single story:

1. **Hook** — the emotional moment that creates the need
2. **Discovery** — the app shows what is next
3. **Action** — joining is easy and low-pressure
4. **Creation** — you can start something too
5. **Trust** — it is people you know, not strangers

This arc mirrors the core loop: activity ends, open app, see options, join or create, bounded trust.

## Screenshot 1: Emotional Hook

| Field | Value |
|-------|-------|
| Headline | The best moments should not end there. |
| Caption | After Plans picks up where your plans leave off. |
| App screen shown | Home feed with context chip showing a recent activity and 2-3 discovery cards |
| Key visual elements | Context chip at top, warm discovery cards with participant avatars, "Start what's next" CTA visible |
| What this communicates | The app knows what you just did and shows what is next |
| Avoid | Empty states, settings screens, anything that looks like a generic social feed |

## Screenshot 2: Context-Aware Discovery

| Field | Value |
|-------|-------|
| Headline | See what is happening after. |
| Caption | Ranked plans from people in the same moment as you. |
| App screen shown | Home feed scrolled slightly, showing 3 discovery cards with trust badges, participant counts, and lifecycle state |
| Key visual elements | Trust badges (same-context, known-person), participant avatars, momentum indicators, time/place hints |
| What this communicates | The feed is relevant and trust-oriented, not random |
| Avoid | Cards that look like public event listings, anything resembling a dating card |

## Screenshot 3: Join-First Action

| Field | Value |
|-------|-------|
| Headline | Join with one tap. |
| Caption | No group text. No awkward "who is in?" Just tap Join. |
| App screen shown | Plan Detail view for a Forming plan, with Join and Interested buttons prominent, participant list visible |
| Key visual elements | Join button, Interested button, participant count, lifecycle state badge (Forming), bounded visibility indicator |
| What this communicates | Participation is easy, low-pressure, and visible |
| Avoid | Complex forms, chat interfaces, anything that requires effort to participate |

## Screenshot 4: Create Your Own

| Field | Value |
|-------|-------|
| Headline | Start what is next your way. |
| Caption | Exact plan, loose idea, or open intent — create in seconds. |
| App screen shown | Create Plan screen showing the three creation modes (exact plan, default option, open intent) |
| Key visual elements | Three clear creation paths, minimal form fields, fast completion affordance |
| What this communicates | Creating is fast and flexible, not just joining |
| Avoid | Long forms, complex settings, anything that makes creation look effortful |

## Screenshot 5: Bounded Trust

| Field | Value |
|-------|-------|
| Headline | People you know or are already around. |
| Caption | Plans stay in context. Not public. Not broadcast. Not strangers. |
| App screen shown | Confirmation Room or Plan Detail showing participant list with trust badges, "who can see this" indicator, and safety access |
| Key visual elements | Trust badges on participants, bounded visibility explanation, report/block access, "who can see this" line |
| What this communicates | This is a trust-bounded product, not open stranger discovery |
| Avoid | Map views, city-wide discovery, anything suggesting broadcast visibility |

## Caption Alternates

For A/B testing or localization:

### Screenshot 1 alternates
- After dinner. After class. After the meetup. What is next?
- The night does not have to end here.

### Screenshot 2 alternates
- Plans from people who were just there too.
- Context-first discovery, not random chance.

### Screenshot 3 alternates
- Signal interest first. Join when you are ready.
- Less awkward than texting everyone.

### Screenshot 4 alternates
- Got an idea? Put it out there in seconds.
- Three ways to start: exact, loose, or open.

### Screenshot 5 alternates
- Same activity. Same circle. Same evening.
- See who can see this — always.

## Design Direction

### Frame style
- Device frame: iPhone 15 Pro in natural titanium or similar neutral tone
- Background: warm gradient or solid that complements the app's color palette
- Headline placement: above or below the device frame, large and legible
- Caption placement: below headline, smaller, secondary color
- No decorative clutter — the app screen should be the focus

### Content guidelines for mock data
- Use realistic but fictional names and profile photos
- Show plans with real-world contexts: "Drinks at The Rooftop", "Walk to the taco spot", "Coffee before heading home"
- Show 3-5 participants per plan, not empty or overcrowded
- Show a mix of lifecycle states across screenshots (Forming, Confirmed)
- Contexts should be relatable: dinner, class, meetup, conference session, game night

### Typography
- Headlines should use the app's brand typeface at display size
- Captions should be readable at App Store thumbnail scale
- High contrast between text and background

## Production Checklist

- [ ] Mock data populated in demo build or design tool
- [ ] Screenshots captured at 6.7" device resolution
- [ ] Screenshots captured at 6.1" device resolution (if submitting)
- [ ] Device frames applied
- [ ] Headlines and captions overlaid
- [ ] All 5 screenshots reviewed for dating/stranger misinterpretation risk
- [ ] Final set approved by founder
