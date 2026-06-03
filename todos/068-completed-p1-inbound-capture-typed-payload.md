---
status: completed
priority: p1
issue_id: "068"
tags: [code-review, architecture, agent-native, better-business-web, agency]
dependencies: []
---

# Problem Statement

The CTA's fulfillment path is "manual for v1," and as specified a submission
lands only in a human inbox (email/Slack notification) — nowhere the platform
can observe or act on it. This breaks the repo's agent-native model ("Structured
task I/O with typed payloads", "the platform owns orchestration") and orphans
the one new user-facing entry point. The end-to-end flow (where the record
lives, who owns it, the SLA, how it re-enters the system) is undefined.

## Findings

- §7: "configure a notification (email/Slack) so submissions reach the operator" — [LANDING_PAGE_PLAN.md:160](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:160).
- §10: "Route form submissions into that loop (manual for v1)" — [LANDING_PAGE_PLAN.md:194](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:194). "Manual" here means *no flow*, just a human reading email.
- The outbound prospect lane already does this correctly: `packages/prospecting/run.py` saves typed `ProspectRecord`s via `JsonStore` into `state/prospects/` with an `audited/` stage. The inbound funnel is the orphan.
- The typed-capture pattern to mirror exists: `packages/agency/intake.py` `ClientIntake`.
- The Stage-2 audit the captured record should feed: `packages/policies/verification_loop.py`, `packages/tools/primitives/verification_loop_runner.py`.

## Proposed Solutions

### Option 1: Capture submission as a typed record in state/ (recommended)
Netlify form-submission webhook → small handler that writes a typed
`WebsiteReviewRequest`/`InboundLead` dataclass (peer of `ClientIntake`) via
`JsonStore` into `state/prospects/inbound/`. Email/Slack stays as a secondary
notification, not the system of record. Name the task contract that hands the
record's URL to `verification_loop_runner` (operator-invoked in v1).

Pros:
- Reuses existing JsonStore / audited-stage / verification_loop infra
- "Manual for v1" becomes *manual trigger of an automatable step*, not manual data entry

Cons:
- Adds one webhook handler hop

Effort: medium
Risk: low

### Option 2: Netlify notification only, defer typed capture
Ship v1 with inbox-only, add state capture later.

Pros:
- Least work now

Cons:
- Ossifies a parity break on the core entry point; loses leads to inbox

Effort: small
Risk: medium-high

## Recommended Action

Adopt Option 1: define the inbound typed payload (with the `site_url` field the
audit consumes), persist into `state/`, and name the trigger contract into the
Stage-2 loop. Specify the full inbound→notify→operator→audit hop chain in the
plan even if each hop is manual.

## Technical Details

- New dataclass + handler under `packages/agency/`; `state/prospects/inbound/`; bridge to `verification_loop_runner`.

## Acceptance Criteria

- [ ] Submissions persist as a typed record in `state/`, not just inbox.
- [ ] The record carries the field the Stage-2 audit consumes.
- [ ] The plan names the inbound→fulfillment hop chain and owner.

## Work Log

### 2026-06-02 - Initial review capture
Surfaced by agent-native-reviewer + spec-flow-analyzer during `/review`.

### 2026-06-02 - Plan amended (diagnose+fix, P1 pass)
Plan §7 now specifies capturing each submission as a typed `WebsiteReviewRequest`
(peer of `ClientIntake`) via `JsonStore` into `state/prospects/inbound/`, with the
email/Slack notification secondary. §10 names the two consumers (preview + audit).
**Pending build step:** define the dataclass + webhook handler + the trigger
contract into `verification_loop_runner` / prospect-site. Keep open until the
typed capture lands in code.

### 2026-06-02 - DONE: typed capture pipeline live
Added `WebsiteReviewRequest` + `InboundReviewRepository` (packages/agency/inbound.py)
persisting to state/prospects/inbound/ via JsonStore. Netlify Function captures the
submission (todo 071) → Blobs → `scripts/web/pull-inbound.mjs` writes typed records
the platform reads. Verified end-to-end. Record carries `website` (the field the
preview/audit consumes). Remaining: notification + auto-poll + fulfilment trigger.
