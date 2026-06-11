# Conversion Lab

Conversion Lab is Better Business Web's preflight workflow for auditing a
website, landing page, promo page, or ad before redesign or spend. It uses
synthetic audience panels as an internal review method, but the client-facing
product is conversion intelligence: clearer copy, sharper objections, and a
ranked set of improvements.

## Positioning

Sell the business outcome:

- Find conversion blockers before rebuild work.
- Identify trust gaps before ad spend.
- Rewrite the sections most likely to affect calls, forms, bookings, or purchases.
- Prioritize what to fix first instead of handing the owner a generic AI report.

Do not sell "AI focus groups" as the product, and do not claim deterministic
revenue prediction. The promise is better preflight judgment, not guaranteed lift.

## Good Fits

- Med spas, dentists, roofing, HVAC, restaurants, auto services, personal care,
  professional services, and other local service businesses covered by the
  persona library.
- Existing websites with traffic but weak lead flow.
- Package C ad campaigns before go-live.
- Warm prospects where a teardown can make the sales conversation concrete.
- Promo pages where the offer, proof, and CTA need to be tightened quickly.

The reusable audience panel model is documented in
[`conversion-lab/persona-library.md`](conversion-lab/persona-library.md).

## Inputs

- Business name
- Vertical
- City or service area
- URL or pasted copy
- Target service or offer
- Desired conversion action
- Known customer notes, reviews, calls, or objections
- Any compliance limits for the vertical

## Manual Workflow

1. Select the audience panel for the business vertical.
2. Extract the page or paste the page copy into the run notes.
3. Ask each persona for clarity, trust, objection, and action-likelihood feedback.
4. Summarize cross-persona patterns.
5. Rewrite the highest-impact sections.
6. Score the page with the scorecard rubric.
7. Create the client-facing report.
8. If the client has Package C, fold the strongest angle into the ad draft.

## Scorecard

| Area | What To Look For |
|---|---|
| Clarity | Can a visitor understand what is offered in five seconds? |
| Trust | Are credentials, reviews, proof, and safety signals visible? |
| Offer strength | Is the reason to act specific and relevant? |
| Friction | Is the next step obvious and easy? |
| Local relevance | Does the page feel grounded in the owner's market? |
| Conversion action | Does the page make calling, booking, or submitting feel worthwhile? |

Use scores as prioritization aids, not scientific predictions.

## Report Sections

- Executive summary
- Audience panel
- Scorecard
- Conversion blockers
- Trust gaps
- Persona objections
- Copy rewrites
- Priority backlog
- Confidence and caveats

## Delivery Modes

### Conversion Snapshot

A short audit for one page or ad. Use it as a paid diagnostic or proposal sweetener.

### Conversion Audit

A deeper report for one website or campaign page. Use it before a rebuild or as a
standalone paid entry product.

### Ad Copy Lab

A recurring Package C add-on for testing ad angles and copy before operator-approved
campaign changes.

## Boundaries

- Exploratory preflight only.
- No guaranteed revenue predictions.
- No private customer data in persona packs without client permission.
- No fake testimonials, credentials, awards, medical claims, or legal outcomes.
- No automated ad launch or spend.
- No outbound messages are sent by the system.

## Runtime Artifacts

Once the typed workflow exists, reports should land under:

```text
state/clients/<product_id>/conversion_lab/<run_id>/
```

Keep reusable templates and operating docs in `docs/agency/conversion-lab/`, but
keep client-specific run output in `state/`.
