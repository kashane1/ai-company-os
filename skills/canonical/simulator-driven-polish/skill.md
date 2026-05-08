---
id: simulator-driven-polish
name: Simulator-Driven Polish
purpose: Drive an iOS app live in Simulator, identify gaps and rough edges with explicit decision authority, fix them in tight commits, and surface only the decisions that need the operator. Replaces the manual dogfood-and-iterate loop with a structured, bounded agentic loop.
owner_agent: ios
target_runtimes: [claude, codex]
stage: active
inputs:
  - product_id (e.g. life-clock)
  - product path under products/<product-id>-ios/
  - Xcode scheme name
  - target Simulator device + iOS version (default — newest installed iPhone runtime)
  - mode (fix-list | freeform-polish | reference-match | vision-driven)
  - mode-specific payload (the fix list, the reference assets, or a pointer to vision.md)
  - iteration cap (default 8 in polish/reference, 6 in vision)
  - optional design-system or convention doc
outputs:
  - a stack of focused commits on the working branch (one logical fix per commit)
  - a session log at docs/products/<product-id>/polish-<YYYY-MM-DD>-<slug>.md (slug = kebab-case 2–5 word descriptor of the session's focus, derived from operator's idea/mode at session start; collisions resolved by appending -2, -3, etc.)
  - updated golden screenshots under products/<product-id>-ios/.polish/goldens/
  - new accessibility identifiers added to driven elements
  - optional vision.md bootstrap or appended Open Questions
  - PR-ready body summary derived from the session log
allowed_edit_boundaries:
  - products/<product-id>-ios/**
  - docs/products/<product-id>/**
  - skills/adapters/claude/simulator-driven-polish.md (only when explicitly editing the skill itself)
  - skills/adapters/codex/simulator-driven-polish.md (only when explicitly editing the skill itself)
forbidden_areas:
  - packages/policies/
  - state/
  - other products under products/
  - vision.md "Decided constraints" section (read-only; only the operator edits)
preconditions:
  - Xcode scheme exists in the project (verify with xcodebuild -list)
  - target Simulator runtime is installed (verify with xcrun simctl list devices available)
  - app builds for the chosen simulator destination before the loop starts
  - working tree is clean OR operator has explicitly authorized starting from a dirty tree
  - if mode is vision-driven, docs/products/<product-id>/vision.md exists or operator has authorized bootstrap
  - if mode is reference-match, reference assets are present under docs/products/<product-id>/references/<slot>/
dependencies:
  - canonical/ios-simulator-ux-audit (sister skill; this one is the editing counterpart)
  - canonical/verification-loop (run before declaring session done)
  - canonical/handoffs (for handing accumulated changes back)
  - docs/ux-audit-playbook.md
validation_steps:
  - app builds for the target simulator before each commit
  - each commit is scoped to one logical fix
  - session log appended once per iteration
  - golden screenshots refreshed for screens the loop intentionally changed; flagged for screens it did not touch
  - any logic-bearing changes update or add iOS tests
  - Ask-tier findings are surfaced in a single batched ask per cycle, not per finding
handoff_contract:
  what_is_handed_off: the commit stack + session log; PR body is derived from the log
  handed_to: operator for review, then standard PR pipeline
  channel: docs/products/<product-id>/polish-<YYYY-MM-DD>-<slug>.md (the session log IS the handoff)
codex_adaptation_notes: |
  Codex follows the canonical loop through
  skills/adapters/codex/simulator-driven-polish.md. The adapter owns runtime
  translation: shell-first xcodebuild/simctl invocation, apply_patch edits,
  numbered chat asks, Computer Use final-check rules, and repo-backed session
  logs in place of assistant memory writes.
---

# Simulator-Driven Polish

Use this skill when an iOS product needs hands-on improvement, not just a code-only opinion. The loop builds the app, drives it live in Simulator, observes against the chosen reference (a fix list, the design system, an external reference, or the product vision), classifies each finding into a decision tier, and either fixes-and-commits or stops to ask.

This is the editing counterpart to `ios-simulator-ux-audit`. That skill audits and reports; this skill audits AND edits AND commits, under explicit decision authority.

## Modes

The loop primitives are identical across modes. What changes is the **observer** — what the agent compares the running app against.

- `fix-list` — operator hands a bullet list. Loop closes each item and exits.
- `freeform-polish` — observer is the design system + memory conventions (e.g. the lighting convention, mascot rim rules). Default mode.
- `reference-match` — observer is an extracted *design intent spec* derived from operator-supplied reference assets (image, App Store URL, screen capture, prose).
- `vision-driven` — observer is `docs/products/<product-id>/vision.md`. The most agentic mode. Lower iteration cap, harder Ask gates.

Default when invoked with no mode argument: `freeform-polish`.

## Decision Layer (the autonomy contract)

Every observed gap is classified into one of four tiers before action:

| Tier | Examples | Action |
|---|---|---|
| **Polish** (Auto) | spacing, opacity within design system, copy clarity, missing a11y id, dead-end nav, stale log noise | fix + commit silently |
| **Stretch** (Auto-with-note) | stronger copy rewrites, animation timing, small layout reshuffles, tone tightening | fix + commit + flag in session log for operator review |
| **Feature** (Always Ask) | new capability, paywall change, persistence/HealthKit touch, removing a feature, large visual departure | stop, batch, ask in cycle-end summary |
| **Vision-question** (Always Ask) | the vision doesn't address this; or two valid directions exist | stop, batch, ask; offer to append to vision.md Open Questions |

Rules:

1. The skill MAY propose features. It MUST NOT introduce them autonomously.
2. The skill MAY append `## Open Questions` entries to vision.md. It MUST NOT edit `## Decided constraints` — that section is the ratchet, operator-only.
3. Asks are batched at end-of-cycle, not per finding. One queue, with screenshots and 2–3 concrete options per Ask where possible.
4. If the same finding reappears after an attempted fix, count it. After two recurrences, stop and escalate.

## Vision Artifact (`docs/products/<product-id>/vision.md`)

A lightweight, alive document — not a PRD. Required only for `vision-driven` mode; the skill bootstraps it via interview if absent and operator approves.

Required sections:

```
# <Product> Vision

## One-line soul
<a single sentence — what this product is, in essence>

## Core daily experience
<the 30-second loop a user lives>

## What it is not
<explicit non-goals>

## Tone
<terse | warm | clinical | playful — pick one or two>

## Open questions
<things you haven't decided yet; the skill APPENDS here, never overwrites>

## Decided constraints
<accumulated answers, dated; OPERATOR-ONLY edits>
```

The skill reads this at the start of every vision-driven cycle. Decided constraints are non-negotiable; the loop will refuse to take actions that contradict them and escalate instead.

## Procedure

1. **Pre-flight.** Confirm preconditions. Read product docs, the design system, and any prior session logs under `docs/products/<product-id>/polish-*.md`. In `vision-driven` mode, read vision.md.
2. **Build headlessly.** `xcodebuild` to a fresh Simulator. Reuse the build path from `ios-build-and-sign`. Fail fast if the build fails — do not iterate past a broken build.
3. **Boot + drive.** Boot the chosen device, install the app, launch with the appropriate fixture (see Seed Harness). Drive the app via accessibility tree first; fall back to screenshots only when the tree is insufficient.
4. **Observe.** Compare the live app to the mode's observer. Generate a candidate-finding list.
5. **Classify.** Each finding gets one of the four tiers above.
6. **Iterate.** For Polish + Stretch: pick the highest-impact finding, fix it, rebuild, re-verify the same flow, refresh the golden for that screen, commit (`<type>(<product>): <one-line>`). Append one line to the session log.
7. **Cycle close.** When the cycle's findings are exhausted OR the iteration cap is hit OR an Ask-tier finding requires it, batch all queued Asks into a single operator prompt with screenshots and concrete options.
8. **Verify.** Before declaring the session done, run `verification-loop` (or its lighter changed-surface check), confirm the diff against the golden screenshots is intentional, and produce a PR body from the session log.

## Strong-v1 Capabilities (load-bearing — do not skip)

### 1. Seed harness

Launch states are first-class inputs. The skill expects the product to expose a launch-config env-var menu (e.g. `LIFECLOCK_UI_TEST_SCENARIO=onboarded`). On entry, the skill chooses the right seed for the flow under polish:

- `fresh` — fresh install / onboarding flows
- `onboarded` — day-1 returning user
- `streak_n` — long-running user (n days)
- `pro` — entitlements unlocked
- `permission_denied:<capability>` — HealthKit/Notifications/etc denied

If the product lacks a seed harness, bootstrapping it is the loop's first deliverable, before any UX work. Flag the cost in the session log.

### 2. Per-iteration screenshot regression diff

Before each iteration, capture a screenshot of every top-level screen the loop has visited this session. After each fix, recapture and diff. Goldens live at `products/<product-id>-ios/.polish/goldens/<screen>.png`.

- Screens the loop INTENDED to change → expect diff; refresh the golden; one-line note in session log.
- Screens the loop did NOT touch but that diffed → regression suspect; classify as Polish (revert) or Vision-question (escalate).

This catches the "fixed mascot, accidentally broke history rows" failure mode.

### 3. Accessibility-id accrual

Every time the loop drives an element via accessibility tree:

- If the element has a stable `accessibilityIdentifier`, record it for future reuse.
- If not, ADD one in source (`accessibilityIdentifier("<screen>.<element>")`), commit it as `chore(<product>): a11y id for <element>`.

Compounds across sessions into a fully-labeled app, free XCUITest stubs, and cheaper future loops.

### 4. Session log → PR body

The session log under `docs/products/<product-id>/polish-<YYYY-MM-DD>-<slug>.md` follows a stable structure (see Output Style). At session end, the loop emits a PR body derived from the log: summary line, list of commits with one-line rationale, screenshots for visually-meaningful changes, queued Asks (resolved + outstanding), and a "next pass" section.

## Reference Mode

When `mode=reference-match`:

1. Operator drops reference assets under `docs/products/<product-id>/references/<slot>/`. Slots let multiple references coexist (e.g. `palette/`, `motion/`, `density/`).
2. The loop extracts a **design intent spec** — a structured doc capturing palette, type rhythm, corner radii, shadow language, density, motion easing/duration, copy voice, hero-screen hierarchy. Save to `docs/products/<product-id>/references/<slot>/intent.md`.
3. Diff loop runs per-screen: screenshot live app, compare against intent spec dimension-by-dimension, generate one targeted fix per iteration.
4. **Translate, don't clone.** The loop produces something that *feels* like the reference but is the product's own. Direct visual cloning of a recognizable third-party app is an Ask-tier escalation.
5. Stops when intent spec is matched within tolerance OR an Ask-tier deviation appears (e.g. licensing-required font).

Composes with: `gemini-imagegen` (brand assets), `frontend-design` (intent extraction), `content-voice-guardrail` (tone matching).

## Vision-Driven Mode

When `mode=vision-driven`:

1. Read vision.md. If absent, offer bootstrap (interview the operator: soul → core experience → non-goals → tone). Save the result. The first cycle after bootstrap is review-only; operator must explicitly authorize editing.
2. Drive the app toward the vision's named "core daily experience." Record friction, gaps, missing affordances.
3. Generate gap inventory; classify into four tiers.
4. Execute Polish + Stretch silently, per fix, per commit.
5. Queue Feature + Vision-question for batched Ask at cycle close.
6. **Final computer-use checkpoint** (see below) is mandatory in vision mode before declaring session done.

Guardrails specific to this mode:

- Lower iteration cap (default 6 vs 8).
- Feature tier is ALWAYS Ask, even if vision endorses the direction.
- Same-finding-twice → hard stop until operator answers.
- Vision drift impossible by construction: skill cannot edit `Decided constraints`.
- Memory ratchet: each resolved Ask is written to memory + appended (with operator approval) to `Decided constraints`.

## Computer-use Final Checkpoint (opt-in / mandatory in vision mode)

After the loop's Polish/Stretch work is done, drive the macOS Simulator app via computer-use to perform a final user-style acceptance pass: real gestures (long press, multi-touch, swipe-back), keyboard, multitasking, slow-motion observation. Use this when:

- A new feature has shipped this session and needs end-to-end validation.
- A flow involves gestures that accessibility-tree driving cannot fully express.
- It is the final gate before the session emits its PR body (mandatory in vision mode).

Default: opt-in via `final_check=true`. Mandatory in vision mode regardless.

## Stop Conditions

The loop stops when ANY of the following:

- Mode-specific completion: fix list exhausted / no observable issues / intent spec matched / vision gaps queued.
- Iteration cap reached.
- Wall-clock cap reached (default 60 minutes).
- Two-recurrence rule fires on any finding.
- Build fails 2 cycles in a row that the loop introduced.
- Ask-tier finding requires operator input AND no Polish/Stretch work remains.
- Operator interrupts.

On stop, ALWAYS emit the session log + PR body, even on partial completion.

## Output Style

Session log structure (`docs/products/<product-id>/polish-<YYYY-MM-DD>-<slug>.md`):

```
# Polish Session — <product> — <YYYY-MM-DD> — <slug>

## Mode
<mode + payload summary>

## Iterations
- [<HH:MM>] <commit-sha> — <type>(<product>): <one-line> — <Polish|Stretch> — <screen>
- ...

## Stretch decisions (operator review)
- <commit-sha> — <one-line> — why this direction over alternatives

## Asks
### Resolved this session
- <question> → <operator answer> → <commit-sha> (+ vision update if any)

### Outstanding (cycle-end batch)
- <question> + screenshot + 2–3 options

## Regressions caught
- <screen>: <intended|unintended> diff — <action taken>

## A11y identifiers added
- <screen>.<element>

## Vision updates
- Open Questions appended: <bullets>
- Decided constraints proposed (operator-only edit): <bullets>

## Next pass
- <follow-ups for the next session>
```

**Slug derivation.** At session start, after confirming inputs, the skill picks a 2–5 word kebab-case slug describing the session's focus (e.g. `today-screen-morning-greeting`, `history-density-match`, `vision-day7-returning-user`, `fix-list-onboarding-back-nav`). For `fix-list` mode, summarize the list theme. For `vision-driven` open-ended runs, prefix with `vision-` and follow with the seed state or focus. Confirm the slug with the operator before starting so they can override if it doesn't read right.

**Collision policy.** If `polish-<YYYY-MM-DD>-<slug>.md` already exists, append `-2`, then `-3`, etc. Don't merge unrelated work into one file. Same-day re-runs that share a focus (e.g. paused mid-session, resumed an hour later) MAY append a `## Session HH:MM` H2 to the existing file — but only if the operator confirms it's a continuation, not a new effort.

## Failure Modes

- **Simulator won't boot** → stop, report device/scheme/iOS version, ask operator before retrying.
- **Scheme not present** → stop, list `xcodebuild -list` output, ask which scheme.
- **First launch crashes** → fix the crash first; the loop cannot continue past a non-launching app.
- **Onboarding gated by permission** (Apple ID, iCloud, push, HealthKit) → use a launch fixture; if no fixture, stop and ask.
- **No seed harness** → bootstrap one as the loop's first deliverable; flag the cost.
- **No XCUITest target** → bootstrapping it is in scope when accessibility-id accrual depends on it.
- **Reference assets missing or unparseable** (reference-match mode) → stop, ask operator to drop assets.
- **vision.md missing** (vision-driven mode) → offer bootstrap, do not invent silently.
- **Build fails twice consecutively** → stop, surface the build error, ask before retrying.
- **Two-recurrence rule fires** → stop, surface the finding, ask.
- **Operator authorizes contradicting Decided constraints** → refuse; require operator to first edit `Decided constraints` themselves.
- **Findings without evidence** (no screenshot / no AX-tree node / no source path) → drop them. Code-only opinions are out of scope.

## Boundaries

This skill edits the product source and the product's docs. It does NOT:

- edit `packages/policies/`
- edit `state/`
- edit other products
- edit `vision.md`'s `Decided constraints` section
- ship or deploy anything (chain to `ios-to-appstore-handoff` for that)
- generate marketing content (chain to `app-store-positioning-pack`)
- run the verification loop autonomously beyond the changed-surface check at session end
