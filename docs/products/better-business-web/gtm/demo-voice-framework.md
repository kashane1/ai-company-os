# Better Business Web — Per-Business Demo Voice Framework

Voice rules for the GENERATED client demos. The agency's own voice lives in
`voice.md`; this governs the surface where the page must sound like the
**business**, not the agency and not AI. Read alongside
`docs/demo-site-build-playbook.md` and `voice.md`'s `## Banned phrases`.

## Principle: derive the voice from the business, never a template

Before writing, read the brief: what does THIS business actually compete on? That
"lead-with" angle comes from its reviews, photos, and services — not a genre
default. Two businesses in the same genre should read as two different businesses.

## Genre lead-with table (start here, only if the data supports it)

| Genre | Lead with |
|---|---|
| Auto repair | Honesty, transparent pricing, no upsell |
| Nail salon / beauty | The work + the experience (let the gallery carry it) |
| Bakery / cafe | Signature items + the room's character |
| Barber | The craft + the regulars |
| Coffee | Atmosphere + locals (neighborhood third place) |
| Dog grooming | Trust with your pet + gentleness |
| Gun store | Expertise + compliance / safety (calm authority) |
| Plumbing | Reliability + fast response (licensed, same-day, upfront quotes) |

For genres not listed, derive the angle the same way: the one thing reviews repeat.

## Grounding (restated hard rules)

- Copy comes only from the data. No invented services, prices, awards, dates, superlatives.
- No "lowest price / cheapest" unless evidence supports it — read negative reviews first.
- Reviews are INPUT → paraphrase, never quote verbatim.
- Named staff are a real trust signal: you may name a person the reviews name.

## Attribution rule (closes a gap)

Do NOT attach a real reviewer's name to a paraphrase you wrote. Use unattributed
("Customers regularly mention…") or aggregate ("Multiple Google reviewers note…").
You may name a person the reviews praise; you may not invent a reviewer.

## Anti-slop (apply the shared list)

Apply `voice.md`'s "Banned everywhere" subsection (skip "Agency-site only" — those
are about the studio, not a local business). Order of operations in verify:

1. **Whitelist the business's own name tokens first** ("Elevate Fitness" → keep "Elevate").
2. Literal-grep the remaining prose against the banned-everywhere words/openers.
3. LLM self-critique for constructions, em-dash budget (~1/500), rhythm, clichés, unbacked claims.
4. **Iterate on fail.** This is a real gate, not advisory.

## Language (English-only)

The banned list is English-only. For non-English markets: decide the output page
language from the business's own evidence; keep proper nouns verbatim; do NOT run
the English grep against non-English body text. Grounding rules apply in every language.
