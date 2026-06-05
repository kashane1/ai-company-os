---
date: 2026-06-05
topic: bbw-copy-voice-system
product: better-business-web
status: brainstorm
---

# Better Business Web — Copy Voice System

## What We're Building

A copy-quality system for **Better Business Web** (`bbw`) so that AI-assisted website copy stops sounding like AI and starts sounding authentic, trustworthy, and conversion-focused. It covers **both** surfaces of copy in the product:

1. **The agency marketing site** (`products/better-business-web/site/.../LandingBody.astro`) — the founder's sales copy that closes customers.
2. **The client demo sites** — the per-business copy an LLM subagent generates for every prospect (`SUBAGENT-BUILD-SPEC.md`, governed by `docs/demo-site-build-playbook.md` + `docs/demo-site-learnings.md`).

The system has three artifacts that share one anti-slop layer:

- **Shared anti-slop layer** — a banned-phrase / "AI-tell" list, an em-dash budget + sentence-rhythm rule, and a draft → critique → rewrite self-critique loop. Applied to all copy.
- **Founder voice spec** (`voice.md`) — first-person "Kashane" voice for the marketing site, authored in the schema the existing `content-voice-guardrail` skill already consumes.
- **Per-business voice framework** (`demo-voice-framework.md`) — rules for making each demo sound like *that business* (not like an agency or AI), grounded only in real Google data.

These live under `docs/products/better-business-web/gtm/` and are wired into both copy pipelines so the checks run automatically (Approach B), not just when someone remembers to load a doc.

## Why This Approach

**The core insight from research:** the best teams don't teach AI "how to sound human" — they teach it *their specific voice* and force it to critique its own output. Pointing AI at a generic prompt-engineering repo produces *better-AI-sounding* copy, not authentic copy. So the value is in a voice knowledge base + few-shot examples + a self-critique loop + a banned-phrase filter — not in a clever prompt.

**Why both surfaces, one system:** the marketing site and the demos are genuinely different voice problems (your founder voice vs. each client's voice), but they share the same anti-slop layer and the same self-critique discipline. Building them together avoids duplicating the banned-phrase list and critique loop twice.

**Why Approach B (wire the guardrail):** the repo already has a `content-voice-guardrail` skill (fail-closed on banned phrases) and a proven `voice.md` pattern (catchbook) — but no `voice.md` for `bbw` and no Claude adapter. Approach B authors the missing `voice.md` + adapter and wires the self-critique pass into both pipelines. It captures ~90% of the value, reuses infra you already half-built, and turns the self-critique loop into a real gate instead of a suggestion. Approach A (docs only) drifts; Approach C (full critic agent + evals) is premature until demo volume is higher.

## Key Decisions

- **Scope = both surfaces, one shared system.** Same artifact set serves the marketing site and the generated demos; reuses the existing guardrail infra.
- **Brand = Better Business Web** (confirmed; "Internet Presents" is not in the repo). A descriptive, trust-forward name does the "safe to hire" work itself → copy stays straight, personality stays low.
- **Two distinct voices, not one.** Founder voice (marketing) sells the *service*; per-business voice (demos) must sound like the *client*. A shared anti-slop layer sits under both.
- **Voice posture ≈ 60% plain-friendly / 30% facts & risk-reduction / 10% light personality.** No satire. Personality only in low-stakes corners (footer, 404, empty states) — never on price or the guarantee. (NN/g: 52% of "would I hire them" is trustworthiness vs. 8% friendliness; humor *reduces* trust in high-stakes purchases.)
- **Lead with "previewed before you pay" as risk-reversal.** It's the strongest, most defensible hook — stronger than a money-back guarantee because there's no money to refund. Upsell lightly and only *after* the core promise.
- **Point AI at a curated source set, not a generic prompt repo.** Primary: `anti-ai-slop-writing` + `stop-slop` (droppable Claude skills). Reference: Mailchimp style guide, GOV.UK A–Z, Shopify Polaris, Copyhackers frameworks. (See appendix.)
- **Approach = B (wire the guardrail):** author `voice.md` in the guardrail schema, write the missing `skills/adapters/claude/content-voice-guardrail.md`, wire the banned-phrase + self-critique pass into the marketing-copy workflow and the demo `SUBAGENT-BUILD-SPEC`.

## Open Questions

*(for the planning phase)*

- **Marketing-site critique trigger:** the marketing copy is hand-authored Astro. Should the self-critique pass be a `/copy-review` skill you run before committing `LandingBody.astro` edits, or a CI check? (Lean: an on-demand skill.)
- **Demo wiring order:** wire the Claude adapter first, then the demo `SUBAGENT-BUILD-SPEC` second? Is demo volume high enough yet to justify wiring the guardrail into the subagent now?
- **Vendor vs. reference:** do we copy the banned-words lists from `anti-ai-slop-writing` / Mailchimp / GOV.UK into our `banned-phrases.md` (check licenses — Mailchimp CC-BY, GOV.UK OGL, anti-ai-slop repo license), or just link them?
- **Examples storage:** store *extracted patterns + your own best lines*, not full competitor pages (copyright + the research's "extract patterns, don't copy wording" rule). Confirm.
- **Voice calibration:** `voice.md` should be validated against 2–3 sample rewrites of real `LandingBody.astro` sections before it's locked.

## Next Steps

→ Run `/workflows:plan` for implementation details (file-by-file: `gtm/` artifacts, the Claude adapter, the two pipeline wirings, and the marketing-copy rewrite pass).

---

## Appendix A — Vetted sources to point the AI at

**Primary (droppable Claude/Cursor skills):**
- [`anti-ai-slop-writing`](https://github.com/jalaalrd/anti-ai-slop-writing) — `banned-words.md` (50+ words), 35+ banned phrases, 16 banned openers, structural linting (em-dash overuse, rule-of-three, "not X, it's Y").
- [`stop-slop`](https://github.com/hardikpandya/stop-slop) (~5.9k★) — closely related anti-slop skill.

**Reference (voice systems + banned words + frameworks):**
- [Mailchimp Content Style Guide](https://styleguide.mailchimp.com/) ([GitHub](https://github.com/mailchimp/content-style-guide), [TL;DR](https://styleguide.mailchimp.com/tldr/)) — gold-standard public voice system.
- [GOV.UK Style Guide A–Z](https://www.gov.uk/guidance/style-guide/a-to-z) — plain-English banned-words list (bans leverage, deliver, robust, transform, streamline, empower…).
- [Shopify Polaris — Voice & Tone](https://polaris-react.shopify.com/content/voice-and-tone) — "just focus on sounding human": contractions, be direct, ~7th-grade reading level, read it aloud.
- [Copyhackers / Copy School](https://cs.copyhackers.com/) — PAS, AIDA, Before-After-Bridge frameworks (conversion copywriting).
- [promptingguide.ai](https://www.promptingguide.ai/) — few-shot prompting + prompt chaining (the technique backbone for the self-critique loop).
- [ux-writing-skill](https://content-designer.github.io/ux-writing-skill/) — UI microcopy patterns (for site UI strings, buttons, empty states).

**Index / low-trust (use sparingly):**
- [Awesome-Prompt-Engineering](https://github.com/promptslab/Awesome-Prompt-Engineering) — a link index, not a playbook.
- [ai-prompt-library](https://github.com/rhadiaris/ai-prompt-library) — low-trust (1★); borrow only the voice-guide template structure.

**Companies to study for the `examples/` folder** (extract patterns, don't copy wording): DesignJoy (`designjoy.co`), Basecamp/37signals (`37signals.com`), Tiny (`tiny.com`), B12 (`b12.io`) — productized-service and "website-as-a-service" businesses, not Stripe/Linear (those sell software to technical buyers).

## Appendix B — Banned "AI-tell" list (seed for `banned-phrases.md`)

- **Verbs:** unlock, leverage, elevate, delve, harness, utilize, streamline, supercharge, embark, navigate, underscore, empower, foster, facilitate, transform.
- **Adjectives:** pivotal, robust, seamless, innovative, cutting-edge, bespoke, vibrant, holistic, transformative, dynamic.
- **Nouns:** landscape, realm, tapestry, synergy, testament, journey, ecosystem, game-changer, powerhouse.
- **Openers/transitions:** "In today's fast-paced world," "In today's competitive landscape," "In conclusion," Furthermore, Moreover, Notably, Certainly, "It's worth noting that," "When it comes to."
- **Constructions to ban outright:** "It's not just X, it's Y" / "This isn't X, it's Y" / "Forget X. Focus on Y" / "Stop X. Start Y."
- **Hype/emotion crutches:** "We're thrilled," "We're excited to," "Look no further," "rest assured," "the world of."
- **Structural tells:** em-dash overuse (budget ~1 per 500 words), rule-of-three on everything ("fast, simple, and reliable"), uniform sentence length, emoji bullets, over-hedging ("can help to potentially improve").
- **bbw-specific:** no "AI-powered" framing, no tech-speak (HTML/CSS/Webflow/widgets) — talk about *getting more customers*, not the tooling.

## Appendix C — "Say this, not that" (founder voice samples)

- **Hero:** ~~"We craft bespoke digital experiences that elevate your brand…"~~ → **"See your new website before you pay a dime."** (sub: *"I build it first. You only pay if you love it."*)
- **Value prop:** ~~"Innovative, end-to-end solutions that seamlessly empower local businesses…"~~ → **"Most roofers and dentists are stuck with a site that looks like 2009 — or no site at all. I fix that in a week, and you see the result before you spend anything."**
- **Guarantee:** ~~"Committed to delivering a robust solution that ensures total satisfaction."~~ → **"Don't like what I built? Don't pay. No deposit, no contract, no awkward conversation."**
- **CTA:** ~~"Embark on your digital transformation journey today."~~ → **"Get your free preview. Takes 2 minutes to start, and you'll see a real page by Friday."**
- **Upsell (light, after the promise):** **"One website, one flat price. Want it found on Google or a booking form added later? I can do that too — but let's get your site live first."**
