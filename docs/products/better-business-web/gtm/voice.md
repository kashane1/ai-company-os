# Better Business Web — Brand Voice

Source of truth for `copy-review` (and `content-voice-guardrail` if bbw ever
posts social). Treated as opaque reference text by the skills; edits here require
re-running their fixtures. The `## Banned phrases` heading is read
programmatically — it is the single anti-slop list for both surfaces.

## Who we are

Better Business Web is a one-person web studio run by Kashane. I design and build
clean, modern websites for small businesses — roofers, dentists, landscapers, the
shop on Main Street. I sell risk reduction, not technology. The whole pitch: you
see a real preview of your site before you pay a cent, so hiring me is a decision
you can't lose on. I write in the first person ("I build it, you review it").

## Voice pillars

<!-- posture: ~60% plain-friendly / 30% facts & risk-reduction / 10% light personality. No satire. -->

- **Plain.** Short words, short sentences, contractions. ~7th-grade reading level.
- **Specific over adjectives.** "Live preview in ~48 hours" and "$0 until you
  approve" beat "fast" and "affordable."
- **Calm confidence.** State the facts; let the preview do the selling. No hype.
- **Risk-reducing — lead with it.** "Previewed before you pay" is the first thing
  a visitor should understand. Every section reinforces that they're never exposed.
- **Light personality, only in low-stakes corners** (footer, 404, empty states) —
  never on price or the guarantee.
- **Light upsell, only after the core promise.** Get the site live first; mention
  add-ons as "I can do that too," never instead of the core offer.

## Banned phrases

### Banned everywhere (marketing site + demos)

The list is deliberately short. The `## Preferred vocabulary` table below teaches
the voice by example, which does far more work than fencing off words — and a
short list gets obeyed where a 40-word listicle gets skimmed. These are only the
words a model actually reaches for when writing *local-business* copy:

Single words (any inflected form):
- elevate, unlock, leverage, streamline, supercharge, seamless, robust, transform

Openers that signal AI on sight:
- "In today's fast-paced world", "In today's competitive landscape", "Look no further".

Constructions (LLM-judged, not grep) — the real structural tells that survive into
otherwise-clean copy: "It's not just X, it's Y" / "This isn't X, it's Y" /
"Forget X. Focus on Y" / "Stop X. Start Y" / "Say goodbye to X". Hype crutches:
"We're thrilled/excited to", "rest assured", "the world of".

Structural tells (counted, not banned): em-dash BUDGET ~1 per 500 words (count,
don't ban); rule-of-three on everything; uniform sentence length; emoji bullets.

### Agency-site only (NOT applied to client demos)

- "AI-powered", "AI-driven", "AI-generated" — never frame the studio's work as AI.
- Tech-speak: HTML, CSS, Webflow, WordPress, "responsive", "mobile-first",
  "widgets", "the stack".
- Studio-of-one honesty: no "our team", "our experts", "world-class",
  "industry-leading".

<!-- NOTE: "guarantee" is intentionally NOT banned — it is bbw's core promise.
     Do not add it. -->

## Preferred vocabulary

Say this, not that — tuned for roofers / dentists / landscapers:
- "elevate your brand" → "make your business look professional on a phone"
- "digital transformation journey" → "a new website, live by Friday"
- "leverage cutting-edge technology" → "a fast, clean site that works on every phone"
- "bespoke digital experiences" → "a website built for your business, not a template"
- "responsive, mobile-first design" → "looks right on the phone, where your customers find you"
- "we craft / we deliver solutions" → "I build it"
- "boost your online presence" → "show up when someone searches for a roofer near them"
- "drive conversions" → "turn the people who look you up into the people who call"
- "robust, end-to-end solution" → "everything your site needs, in one flat price"
- "schedule a consultation" → "ask for a free review"
