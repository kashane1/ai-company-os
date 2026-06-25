---
id: prospect-census
name: Prospect Census
purpose: Produce a one-shot audit of every prospect in the warehouse grouped by source, cohort (verified/unverified split), verification method/verdict, and a "ready to build" rollup of verified no-website targets with contactability — so the operator can see the state of the whole pipeline at a glance.
owner_agent: supervisor
target_runtimes: [claude]
stage: active
kind: agentic
allowed_edit_boundaries:
  - state/artifacts/prospecting/
forbidden_areas:
  - packages/
  - apps/
  - products/
  - docs/
---

# Skill: prospect-census

Kind: agentic
Owner: supervisor
Runtimes: claude

## Purpose

The prospect warehouse holds tens of thousands of records across multiple
sources (Google Places, Overture, DataForSEO) and lifecycle states (discovered,
verified, dropped, ready-to-build). When the operator asks "what's the current
state of all my prospects?" or "which group did we just verify?" or "how many are
ready to build?", they need a single grouped summary — not an ad-hoc query.

This skill runs the canonical census command and interprets its output.

## Procedure

1. **Run the census command** (read-only — it never mutates records):
   ```
   python scripts/prospect_scan.py census
   ```
   Add `--out state/artifacts/prospecting/census-<YYYY-MM-DD>.md` to also save a
   dated snapshot, or `--json` for machine-readable output.

2. **Read the output**, which has five sections:
   - **By source** — record counts per discovery source.
   - **By cohort (verified / unverified)** — every cohort with how many are
     verified vs. still queued. `A_gold`/`A2` are the target cohorts;
     `S_source_candidate` is the unworked raw queue; `E_has_site` are drops.
   - **By verification method** — `(unverified)` vs `manual_browser`/`brave`/etc.
   - **Verified verdicts** — `none_found`/`social_only`/`marketplace_only` are
     targets; `owned_site` are drops; `ambiguous` need hand-review.
   - **Ready to build** — verified no-website targets, broken down by cohort ×
     source, with how many have a phone and how many have a digital contact
     (email/IG/FB/booking). This is the actionable build queue.

3. **Summarize for the operator.** Lead with: total prospects, the size of each
   target cohort, and the ready-to-build counts. If they asked about a specific
   batch (e.g. "the group we just verified"), name the matching
   cohort × source row from the ready-to-build table. Do not dump every table
   verbatim unless asked — surface the rows that answer the question.

## Notes

- The "ready to build" rollup only counts records that are **verified** AND have
  a target verdict — so it reflects genuinely actionable leads, not raw discovery.
- A digital-contact count well below the target count means a contact-enrichment
  pass is needed before email/DM outreach (phone outreach works without it).
- This is a reporting skill: never edit records from it.
