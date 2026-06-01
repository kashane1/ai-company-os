# Founder OS

The operating layer for the discovery loop: how decisions get made, not just
what tools exist. The platform already owns the *build → ship* half of the loop
(supervisor → workers → approval gates → App Store). This doc covers the *front*
half the discovery layer adds: **discover → rank → validate → hand to build.**

```
discover pain  →  rank opportunity  →  validate demand  →  hand to build lane
      ↑                                                          │
      └──────────  measure outcomes  ←──────────────────────────┘
                        │
                        └─→ write results back to memory  (the compounding asset)
```

## Operating principles

1. **Evidence over ideas.** An idea with three "I'd pay for this" quotes beats
   ten clever ideas with none. Every `OpportunityRecord` must carry evidence
   links — that is what drives `confidence`.
2. **Validate before you build.** Code is the most expensive way to test demand.
   Spend the cheap tests first (landing page, outreach, concierge); the build
   gate (`assert_ready_to_build`) refuses to scaffold until an experiment passes.
3. **Distribution is the product.** `distribution_path` is a top-weighted signal
   and a hard gate: a wedge with no allowed channel cannot advance.
4. **Memory compounds; tools don't.** Frameworks churn. Your accumulated record
   of what converted is the asset. Write everything back (see
   `discovery-evals.md`).
5. **Gates protect the loop.** One blacklisted domain or banned account can end
   the operation. Compliance is a feature, not friction (see
   `discovery-compliance.md`).
6. **One owner per decision.** Every consequential action has a named human
   approver via the existing approval policy. "The agent did it" is never an
   acceptable post-mortem line.

## The weekly cadence

The loop runs continuously, but humans review on a cadence. A workable rhythm:

| When | Who | Action |
|------|-----|--------|
| Continuous | discovery connectors | Pull signals → opportunity inbox |
| Daily | scoring pass | Re-score inbox; surface the top few |
| Mon | you | Pick ≤2 opportunities to validate; approve experiments |
| Tue–Thu | strategist + copywriter | Run validation experiments |
| Fri | you | Review results; pass/kill gate; write outcomes to memory |
| Monthly | you | Review evals: which niches/sources produced revenue; retune weights |

Resist validating more than two things at once. Throughput is gated by your
attention, not the connectors'.

## Decision gates (kill criteria)

A wedge advances only if it clears each gate. Killing fast is the point.

- **Discovery → Rank:** at least 2 independent evidence sources show the same
  pain (confidence model).
- **Rank → Validate:** `opportunity_score ≥ min_score_to_validate` **and**
  `confidence ≥ min_confidence_to_validate` **and** a distribution path exists,
  with no hard gate tripped. Enforced by `evaluate_opportunity`.
- **Validate → Build:** a pre-defined demand signal is hit (≥N signups, ≥M%
  conversion, ≥1 paid pilot). Define the number *before* running, in the
  `ExperimentRecord.success_criteria`. Enforced by `assert_ready_to_build`.
- **Build → Ship:** the existing platform lane takes over (QA + compliance +
  human approval gate).

If a wedge fails a gate, record *why* in `kill_reason`. Failed experiments are
training data for the scoring model — not waste.

## What the agents optimize for

Anchor every agent to **validated revenue per unit of human attention spent.**
Everything upstream (ideas found, dossiers written) is a leading indicator, not
a goal.

## Anti-goals

- Do **not** chase idea volume. A full inbox is not progress.
- Do **not** automate outreach before you can personalize and gate it.
- Do **not** let agents buy domains, run ads, or deploy without a gate.
- Do **not** scrape aggressively to win a week and lose the IP range.

## How it maps onto the existing platform

| Loop stage | Lives in | Reads | Writes |
|------------|----------|-------|--------|
| discover | `packages/discovery/connectors` | `config/sources.yaml` | raw signals → inbox |
| rank | `packages/discovery/scoring` + `policies/discovery_gates` | inbox | scored opportunities |
| validate | `schemas/experiment` + `policies/discovery_gates` + `web_handoff` | top opportunities | experiment records + WEB build goal |
| build (web) | WEB lane (`apps/worker-web/`) | passed landing-page experiment | Astro landing page |
| build (app) | existing engineering / iOS lanes | passed experiments | repo scaffold + build log |
| ship | existing appstore lane + approval gates | shipped product | release records |
| measure | `discovery-evals.md` | billing + experiment data | outcomes → memory |
