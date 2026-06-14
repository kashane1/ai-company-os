# Funnel Report

_Updated: 2026-06-13T00:57:45Z_

Stage counts measured from primary sources (records, audited CSVs, built sites, deploy URLs, the outreach touch store, the lane ledger, and billing). Conversion is each stage as a percent of the one before it; delta is the change since the previous run.

## Pipeline

| Stage | Count | Δ vs last | Conversion | Source |
|---|---|---|---|---|
| Collected | 29820 | — | — | state/prospects/records/*.json |
| Audited | 2428 | — | 8.1% | state/prospects/audited/*.csv (web_verify_verdict) |
| Built | 586 | — | 24.1% | state/prospects/sites/*/dist-v2/index.html |
| Deployed | 18 | — | 3.1% | records with mockup_url |
| Sent | 11 | — | 61.1% | outreach_touches (distinct place_id) |
| Replied | 0 | — | 0% | outreach-lane client-status.json |
| Won | 0 | — | — | outreach-lane client-status.json |
| Active clients | 0 (no source) | — | — | state/agency/billing/*.json (ACTIVE) |

## Outcomes

- Replied: 0
- Won: 0
- Lost: 0
- Active clients: 0
- MRR (catalog prices): $0.00

## Audited verdicts

_896 of 2428 audited are build targets (no owned site)._

| Verdict | Count | Target |
|---|---|---|
| ambiguous | 43 |  |
| marketplace_only | 422 | ✓ |
| none_found | 34 | ✓ |
| owned_site | 1489 |  |
| social_only | 440 | ✓ |

## Sent breakdown

By channel (distinct prospects):

- call: 2
- email: 4
- sms: 5

By variant (touches):

- demo-link: 12

## Stages with zero data

- Replied (outreach-lane client-status.json)
- Won (outreach-lane client-status.json)
- Active clients (state/agency/billing/*.json (ACTIVE))
