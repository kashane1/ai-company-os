---
description: Audit ALL prospects grouped by state (source, cohort, verification, ready-to-build). Invoke for "summary of all prospects", "prospect census", "current state of my prospects", "which group did we verify", "how many are ready to build".
canonical_source: skills/canonical/prospect-census/skill.md
---

# Prospect Census (Claude adapter)

You are running the `prospect-census` skill from
`skills/canonical/prospect-census/skill.md`. Follow the canonical definition.

## Quick reference

1. Run (read-only): `python scripts/prospect_scan.py census`
   - `--out state/artifacts/prospecting/census-<date>.md` saves a dated snapshot.
   - `--json` for machine-readable output.

2. The report has five sections: **By source**, **By cohort (verified/unverified)**,
   **By verification method**, **Verified verdicts**, **Ready to build**.
   - Targets = `none_found` / `social_only` / `marketplace_only` verdicts.
   - Drops = `owned_site`. Hand-review = `ambiguous`.
   - `A_gold`/`A2` = target cohorts; `S_source_candidate` = unworked queue;
     `E_has_site` = drops.

3. Summarize, don't dump: lead with totals, target-cohort sizes, and the
   ready-to-build counts. If the operator asked about a specific batch, point to
   the matching cohort × source row. Flag when digital-contact counts lag target
   counts (means a contact-enrichment pass is needed before email/DM outreach).

Never edit records from this skill — it is reporting only.
