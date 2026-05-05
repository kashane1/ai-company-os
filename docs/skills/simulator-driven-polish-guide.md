# Operator Guide — Simulator-Driven Polish

**For: anyone running the `simulator-driven-polish` skill on a product in this repo.**
**Skill:** [`skills/canonical/simulator-driven-polish/skill.md`](../../skills/canonical/simulator-driven-polish/skill.md)

This skill replaces the manual dogfood-and-iterate loop you've been running by hand on life-clock with a structured, bounded agentic loop. It builds the app, drives it live in Simulator, classifies what it finds into four decision tiers, fixes Polish/Stretch findings autonomously in tight commits, and stops to ask you about Feature and Vision-question findings — batched once per cycle, not per finding.

---

## TL;DR — quick start

When you're ready to start a session, say one of:

- `polish the app` — defaults to `freeform-polish` mode. Closest to your current life-clock workflow.
- `run the polish loop on life-clock with this fix list: [list]` — `fix-list` mode.
- `polish life-clock to match the reference in docs/products/life-clock/references/<slot>/` — `reference-match` mode.
- `run a vision-driven session on life-clock` — `vision-driven` mode (requires `vision.md` to exist).

Claude will confirm: product, scheme, simulator, mode, iteration cap, whether to run the final computer-use checkpoint. Then it builds, drives, fixes, commits, and at the end emits a session log + PR body.

---

## The four modes

| Mode | When to use | Observer (what it compares the app against) | Iter cap |
|---|---|---|---|
| `fix-list` | You have a concrete list of bullets to close out | Your bullet list | 8 |
| `freeform-polish` | The app is fundamentally right; you want to tighten it | Design system + memory conventions (e.g. lighting convention) | 8 |
| `reference-match` | You want this app to feel like a reference (image, App Store screenshots, prose, video) | An extracted "design intent spec" from your reference assets | 8 |
| `vision-driven` | You want the agent to use its own judgment toward the product's north star | `docs/products/<product-id>/vision.md` | 6 |

Default if you say "polish the app" with no mode: `freeform-polish`. Vision mode is opt-in — say it explicitly.

---

## The decision tiers (the autonomy contract)

Every finding is classified before action:

- **Polish (Auto)** — spacing, opacity within design system, copy clarity, missing a11y id, dead-end nav, stale log noise. Fixed and committed silently.
- **Stretch (Auto-with-note)** — stronger copy rewrites, animation timing, small layout reshuffles. Fixed and committed, **plus** flagged in the session log for your review.
- **Feature (Always Ask)** — new capability, paywall change, persistence/HealthKit touch, removing a feature, large visual departure. The skill *proposes*; only you *introduce*.
- **Vision-question (Always Ask)** — vision.md doesn't address it, or two valid directions exist. Skill stops, asks, optionally appends to vision.md `Open Questions`.

**Asks are batched at end-of-cycle.** Not per finding. Each Ask comes with a screenshot and 2–3 concrete options.

---

## First-time setup for a product

Do this once per product (life-clock has most of it; your next product will need the full set):

### 1. Confirm the Xcode scheme builds headlessly

```bash
cd products/<product-id>-ios
xcodebuild -list -project <project>.xcodeproj
xcodebuild -scheme <scheme> -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build
```

If headless build fails, fix that first. The loop refuses to iterate past a broken build.

### 2. Set up a seed harness (load-bearing)

The skill expects the app to expose launch-config env-vars so it can deterministically reach states like "onboarded", "day-7 user", "Pro entitlement", "HealthKit denied". life-clock has `LIFECLOCK_UI_TEST_SCENARIO` — see `LifeClockLaunchConfiguration.swift` for the menu.

For a new product, the skill bootstraps the harness as its first deliverable. Expect that first session to spend a chunk of its budget on setup work. Flag it; it pays for itself by the second session.

### 3. (For vision mode only) Create `vision.md`

Path: `docs/products/<product-id>/vision.md`. The skill bootstraps it interview-style if you ask. Required sections:

```markdown
# <Product> Vision

## One-line soul
<a single sentence — the essence>

## Core daily experience
<the 30-second loop a user lives>

## What it is not
<explicit non-goals>

## Tone
<terse | warm | clinical | playful — pick one or two>

## Open questions
<things you haven't decided; the skill APPENDS here>

## Decided constraints
<accumulated answers, dated; OPERATOR-ONLY edits>
```

`Decided constraints` is the **ratchet**. Only you edit it. The skill cannot. Anything in there is a hard rule the loop will not contradict.

### 4. (For reference-match mode only) Drop reference assets

Layout: `docs/products/<product-id>/references/<slot>/`. Slots let multiple references coexist:

```
docs/products/life-clock/references/
  palette/
    inspiration-1.png
    inspiration-2.png
  motion/
    capture.mov
  density/
    things-3.png
```

The skill extracts a design intent spec into `intent.md` per slot on first run.

---

## Running a session — what to expect

### Before it starts

Claude confirms (briefly): product, scheme, sim device, mode, iteration cap, `final_check` (the computer-use acceptance pass). Asks if working tree is dirty.

### During the loop

Per iteration (2–5 minutes typical):

1. AX-tree dump of the screen under work.
2. Compare to the mode's observer.
3. Classify findings.
4. Pick highest-impact Polish/Stretch finding. Edit. Rebuild. Re-drive.
5. Refresh golden screenshot for changed screen; diff goldens for screens NOT touched (catches accidental regressions).
6. Commit (`<type>(<product>): <one-line>`). Append one line to session log.
7. If a driven element lacked `accessibilityIdentifier`, add one and commit `chore(<product>): a11y id for <element>`.

You'll see the commits land on the working branch as it goes. Match your existing life-clock commit cadence.

### When it pauses to ask

End of cycle, **batched**. Looks like:

> **3 questions before continuing:**
>
> **1.** History rows feel cramped on small devices. Two directions:
>   - Option A: drop the secondary metric, keep one number per row (image)
>   - Option B: stack vertically on small screens (image)
>   - Option C: shrink the secondary metric to 11pt (image)
>   Which?
>
> **2.** ... [Feature-tier ask with options]
>
> **3.** ... [Vision-question with options + offer to append to Open Questions]

Answer in chat. Loop resumes.

### When it stops

Triggers (any of):

- Mode-specific completion (fix list closed, no more findings, intent matched, vision gaps queued)
- Iteration cap hit
- Wall-clock cap hit (default 60 min)
- Two-recurrence rule on a finding (same finding survives two attempted fixes)
- Build fails twice consecutively
- Ask-tier finding requires you, no Polish/Stretch left to do
- You interrupt

**Always emits the session log + PR body, even on partial completion.**

### After the session

You get back:

1. **A stack of commits** on the working branch — one logical fix per commit.
2. **Session log** at `docs/products/<product-id>/polish-<YYYY-MM-DD>-<slug>.md`. The slug is a 2–5 word kebab-case descriptor of the session's focus (e.g. `today-screen-morning-greeting`, `history-density-match`, `vision-day7-returning-user`). Each session gets its own file. Slug collisions resolve to `-2`, `-3`, etc. Same-day continuations (paused and resumed) MAY append `## Session HH:MM` H2 to the existing file with your confirmation.
3. **PR body draft** derived from the session log.
4. **Fresh goldens** under `products/<product-id>-ios/.polish/goldens/`.
5. **A11y identifiers** added wherever the loop touched UI.
6. **Memory writes** for any newly-validated convention (think: lighting convention).

If you said `final_check=true` (or vision mode), Claude also runs the computer-use acceptance pass before declaring done.

---

## Reference-match mode — deeper notes

The skill **extracts intent**, it doesn't clone. If a reference asset would lead to recognizable visual cloning of a third-party app, that's an Ask-tier escalation ("translate, don't clone").

The intent spec captures: palette, type rhythm, corner radii, shadow language, density, motion easing/duration, copy voice, hero-screen hierarchy. You can hand-edit `intent.md` to bias the loop — e.g., delete the palette section if you only want to match motion.

Composes with: `gemini-imagegen` (brand assets like the bezel commit), `frontend-design` (intent extraction), `content-voice-guardrail` (tone matching).

---

## Vision-driven mode — deeper notes

This is the most agentic mode and the one most likely to surprise you. Extra guards:

- Lower iteration cap (6 by default).
- Feature tier is ALWAYS Ask, even if vision endorses the direction. The skill cannot ship a feature without you.
- Same-finding-twice → hard stop until you answer.
- Skill cannot edit `Decided constraints` in `vision.md`. Only you.
- The computer-use acceptance pass is mandatory before declaring done.
- Each resolved Ask becomes a memory write + (with your approval) a `Decided constraints` entry. The vision **compounds** — your taste persisted.

If `vision.md` is missing, the skill offers to bootstrap it interview-style. The first cycle after bootstrap is review-only — you must explicitly authorize editing before the loop starts changing code.

---

## When to use this skill vs `ios-simulator-ux-audit`

- **`ios-simulator-ux-audit`** — review only. Produces a dated audit doc with findings and recommendations. Does not edit code.
- **`simulator-driven-polish`** — review **and** edit, with commits. Produces a session log + commit stack + PR body.

If you say something ambiguous like "do a UX pass," Claude asks which one you want.

---

## Troubleshooting

| Problem | What's happening | What to do |
|---|---|---|
| Loop stops after 2 build failures | Build failed twice in a row from a loop edit | Look at the diagnostic the skill pasted; either fix the cause or revert the offending commit and re-run. |
| Loop keeps re-finding the same issue | Two-recurrence rule fired | The fix isn't sticking. Pair on it manually, or rephrase as a Feature-tier ask. |
| Loop wants to change a Decided constraint | Vision drift attempt | Refused by design. If your taste actually changed, edit `Decided constraints` yourself, then re-run. |
| Goldens diff for screens you didn't touch | Unintended regression | Loop already flagged it. Either accept the new golden (rare; explain why in session log) or revert the offending commit. |
| Reference is ambiguous | One image, no context | Loop asks which dimension matters: palette, layout, motion, copy. |
| AX-tree dump returns nothing | Element isn't accessibility-exposed | Loop falls back to one screenshot for that screen and asks you whether to add `accessibilityElement(true)` plus a label, or to drive that screen via computer-use one-off. |
| First launch crashes | Loop cannot continue past a non-launching app | Fix the crash first. The loop is not a crash debugger. |

---

## Boundaries (what the skill will not do)

- Edit `packages/policies/`.
- Edit `state/`.
- Edit other products.
- Edit `vision.md`'s `Decided constraints` section.
- Introduce a new feature autonomously (it can propose; only you ship).
- Deploy / archive / ship — chain to `ios-to-appstore-handoff` for that.
- Generate marketing content — chain to `app-store-positioning-pack`.

---

## Extending the skill

The skill is intentionally v1. Roadmap items already noted:

- **v1.1** — variant generation (2-3 candidate fixes per finding, batched ask with screenshots), light/dark + Dynamic Type + small-device matrix, empty/error/offline state coverage, convention auto-memory.
- **v1.2** — performance pass via Instruments CLI, localization sweep, TestFlight handoff hook, accumulated reference library across products, marketing-screenshot generation.

If you want one of these promoted to v1, edit:

1. `skills/canonical/simulator-driven-polish/skill.md` — add the capability to the Strong-v1 list.
2. `skills/canonical/simulator-driven-polish/fixtures/happy_path.yaml` — add to `required_strong_v1_capabilities` so drift gets caught.
3. `skills/adapters/claude/simulator-driven-polish.md` — add Claude-specific rhythm/tools for it.
4. This guide — document operator-facing usage.

---

## File map

```
skills/canonical/simulator-driven-polish/
  skill.md                          ← canonical source of truth (edit logic here)
  fixtures/happy_path.yaml          ← contract-freeze fixture

skills/adapters/claude/
  simulator-driven-polish.md        ← Claude runtime adapter

.claude/skills/
  simulator-driven-polish.md        ← project-skill pointer (do NOT edit logic)

docs/skills/
  simulator-driven-polish-guide.md  ← this file (operator guide)

docs/products/<product-id>/
  vision.md                         ← per-product vision (vision-driven mode)
  references/<slot>/                ← reference assets (reference-match mode)
  references/<slot>/intent.md       ← extracted design intent spec (auto-generated)
  polish-<YYYY-MM-DD>-<slug>.md            ← per-session log (auto-appended)

products/<product-id>-ios/.polish/goldens/
  <screen>.png                      ← per-screen golden screenshots (auto-managed)
```
