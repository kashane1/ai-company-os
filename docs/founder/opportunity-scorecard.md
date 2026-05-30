# Opportunity Scorecard

How a raw signal becomes a ranked opportunity. This doc is the spec; the
implementation is `packages/discovery/scoring.py`, the weights live in
`packages/discovery/config/scoring.yaml`, and the advancement decision is owned
by `packages/policies/discovery_gates.py` (policy, not tools).

## The twelve signals

Each signal is scored 0–10 (10 = strongest). The field names below are the
canonical keys used by the config and the `OpportunitySignals` schema in
`packages/schemas/opportunity.py`. Definitions are deliberately concrete so two
analysts (or agents) score them the same way.

| Key | Signal | 0 means | 10 means |
|-----|--------|---------|----------|
| `search_volume` | Search volume | No one searches for this | High, growing search demand |
| `buyer_intent` | Buyer intent | Curiosity only | Searching with wallet out ("pricing", "alternative to") |
| `urgency` | Urgency | Nice-to-have someday | Painful now; people hacking workarounds today |
| `willingness_to_pay` | Willingness to pay | Expect it free | Already paying for inferior solutions |
| `competition_weakness` | Competition weakness | Strong, loved incumbents | Incumbents exist but users openly complain |
| `community_pain` | Community pain | Quiet | Repeated, specific complaints across communities |
| `repeated_workflow` | Repeated manual workflow | One-off | A recurring manual task many people do |
| `distribution_path` | Distribution path | No obvious channel | A clear, allowed channel you can reach cheaply |
| `expected_margin` | Expected margin | Thin / heavy ops | Software-like margins |
| `build_feasibility` | Build feasibility | Needs a moonshot | Buildable MVP in days–weeks |
| `defensibility` | Defensibility | Trivially cloned | Data, integration, or distribution moat possible |
| `risk` | Regulatory/ToS risk *(inverted)* | High risk | Clean, low-risk |

> `risk` is **risk-inverted**: 10 means *low* risk. This keeps "higher is always
> better" true across the board, so the weighted sum stays monotonic.

## The score

```
opportunity_score = Σ ( weight_i × signal_i ) / Σ ( weight_i ) × 10
```

A normalized 0–100. Default weights (tune in `config/scoring.yaml`):

| Signal | Weight | Rationale |
|--------|--------|-----------|
| `buyer_intent` | 3 | The single best predictor of revenue |
| `willingness_to_pay` | 3 | Paying-but-unhappy is the sweet spot |
| `distribution_path` | 3 | Where most projects actually die |
| `urgency` | 2 | Drives conversion speed |
| `community_pain` | 2 | Evidence you can quote in copy |
| `competition_weakness` | 2 | Room to win |
| `build_feasibility` | 2 | Time-to-validated-revenue |
| `risk` | 2 | A hard gate, not just a score input (see below) |
| `expected_margin` | 1.5 | Determines whether it's worth it |
| `repeated_workflow` | 1.5 | Recurring value, lower churn |
| `search_volume` | 1 | Useful but gameable / lagging |
| `defensibility` | 1 | Matters later, not at validation |

## Hard gates (override the score)

Some conditions **disqualify** regardless of score. These live in
`config/scoring.yaml` under `hard_gates` and are enforced by
`evaluate_opportunity` in `packages/policies/discovery_gates.py`:

- **ToS/legal blocker** — `risk` ≤ `reject_if_risk_at_or_below` (default 2) →
  the opportunity is routed to compliance review, not low-scored.
- **Blocked compliance flag** — a flag in `block_compliance_flags`
  (`tos-risk`, `regulated-data`) → blocked pending a named compliance owner.
- **No distribution path** — `distribution_path` below `min_distribution_score`
  (default 1) → cannot advance to validation.

## Confidence

Score quality depends on evidence. Confidence is tracked separately:

```
confidence = min(1, evidence_links / target_evidence) × diversity_factor
```

`diversity_factor` rewards multiple distinct evidence hosts (0.7 with one
source, up to 1.0). A score of 82 with confidence 0.2 (one Reddit thread) is a
*hypothesis*; a 70 with confidence 0.9 (five sources across three platforms) is
*actionable*. Rank by score, but never advance a low-confidence opportunity —
the validate gate blocks anything below `min_confidence_to_validate` (default
0.6) and sends it back to the researcher for more evidence.

## Worked example

A wedge: "Etsy sellers manually resize product photos for each marketplace."

| Signal | Score | × weight |
|--------|-------|----------|
| `search_volume` | 5 | 5 |
| `buyer_intent` | 7 | 21 |
| `urgency` | 6 | 12 |
| `willingness_to_pay` | 7 | 21 |
| `competition_weakness` | 6 | 12 |
| `community_pain` | 8 | 16 |
| `repeated_workflow` | 9 | 13.5 |
| `distribution_path` | 7 | 21 |
| `expected_margin` | 8 | 12 |
| `build_feasibility` | 8 | 16 |
| `defensibility` | 3 | 3 |
| `risk` (inv.) | 9 | 18 |

Σ(weight×signal) = 170.5; Σ(weight) = 24 → 170.5 / 24 ≈ 7.10 → **71/100**.
With five evidence links across three platforms, confidence ≈ 1.0 →
**actionable**. This is verified in `tests/python/unit/test_discovery_scoring.py`
and reproduced by `scripts/discovery_demo.py`.
