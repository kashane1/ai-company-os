# Discovery Evals: The Learning Loop

The closed loop is the moat. Tools churn; your accumulated record of what
converted does not. This file defines how outcomes feed back into the discovery
layer so the scoring gets sharper over time.

A competitor can copy your prompts, your stack, even your scorecard. They cannot
copy your labeled history of "this niche, this channel, this price → this CAC
and churn." After a few months that dataset is what makes your scoring sharp and
your bets faster. Protect it, back it up, and keep writing to it.

## Write-back discipline

Every consequential action writes a result back:

- A killed wedge writes `kill_reason` → trains the scorer on what *not* to chase.
- A passed/failed experiment writes its metric value and the pre-set threshold.
- A shipped product writes CAC, conversion, revenue, churn over time.
- A workflow that worked becomes a reusable skill (procedural memory) — the
  platform already has a skill self-evolution loop for this.

## Metrics to track

Track per opportunity and aggregate per source and per niche cluster.

**Funnel**

- ideas found → scored → validated → built → shipped → revenue (counts + rates)
- per-stage drop-off: where do wedges die?

**Discovery quality**

- **source yield:** validated opportunities ÷ ideas found, per source. Kill
  low-yield sources in `config/sources.yaml`.
- **score calibration:** did high-scored wedges actually validate? (precision)
- **false-positive rate:** high score, failed validation.

**Validation efficiency**

- cost per validated wedge (spend + human hours)
- experiment pass rate by type (which tests are most informative for you)

**Growth & revenue**

- CAC by channel, conversion rate, reply rate (outreach)
- revenue, MRR, churn, LTV; LTV:CAC by niche
- wasted spend (experiments + builds that produced no revenue)

**The one number:** validated revenue per human hour spent. Everything else is
a leading indicator.

## Monthly retune

1. Pull the last month of outcomes.
2. Which **signals** actually predicted revenue? Adjust `weights` in
   `config/scoring.yaml` accordingly. (If `search_volume` kept misleading you,
   drop its weight.)
3. Which **sources** produced validated wedges? Disable the duds in
   `config/sources.yaml`; lean into the winners.
4. Which **experiment types** gave the cleanest signal for your audience? Prefer
   them.
5. Record the change and the reasoning. `scoring.yaml` is a versioned, learnable
   asset — every retune is a git commit you can diff.

## Guard against measuring the wrong thing

Agents optimize what you measure. If you reward idea volume, you get noise.
Anchor rewards to validated revenue per human hour. Vanity metrics (signups with
no intent, raw idea counts) are explicitly *not* goals.
