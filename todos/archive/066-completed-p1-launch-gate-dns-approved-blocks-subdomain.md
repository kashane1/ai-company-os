---
status: completed
priority: p1
issue_id: "066"
tags: [code-review, reliability, launch-gate, better-business-web, agency]
dependencies: []
---

# Problem Statement

§8 says v1 "can launch on the Netlify subdomain" and proposes relaxing only
`gbp_link` + `analytics` for first-party sites. But the launch checklist has a
third hard, fail-closed item — `dns_approved` — that fails unless approval is
granted, regardless of whether a custom domain is attached. As written, the
plan's own subdomain-launch path cannot pass the gate.

## Findings

- `dns_approved` is a hard checklist item: [launch.py:99](../packages/agency/launch.py:99) calls `assert_custom_domain_allowed(approval_granted=dns_approved)`.
- That policy always raises without approval: [deploy_readiness.py:61](../packages/policies/deploy_readiness.py:61) `if not approval_granted: raise PolicyViolation(DEPLOY_DNS_NOT_APPROVED, ...)`.
- `ready = all(item.passed ...)` — [launch.py:38](../packages/agency/launch.py:38) — so any failing item blocks launch.
- `dns_approved` defaults `False` ([launch.py:55](../packages/agency/launch.py:55)).
- §8 relaxation names only `gbp_link`/`analytics` — [LANDING_PAGE_PLAN.md:170](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:170). `dns_approved` is unaddressed.
- No `first_party` flag exists in `launch.py` yet (grep confirms).
- Related: the "reviewed preview" hard item has no defined artifact under the no-build file-digest flow (§4) — specify what satisfies it (draft/branch deploy URL or local `dist` walkthrough).

## Proposed Solutions

### Option 1: `first_party: bool = False` flag on the checklist builder (recommended)
When `first_party=True` and no custom domain is attached, mark `gbp_link`,
`analytics`, and `dns_approved` as `passed=True, detail="relaxed: first-party
subdomain"` so the relaxation is **recorded in the report**, not invisible. Keep
all other hard items (ux_audit, contact_form, seo_title, deploy_approved).

Pros:
- One typed, auditable code path; relaxation shows in `LaunchChecklistReport.to_dict()`
- Simpler than a parallel checklist

Cons:
- Slightly widens the builder signature

Effort: small
Risk: low

### Option 2: Separate first-party launch checklist
A dedicated builder omitting the three items.

Pros:
- Keeps client checklist untouched

Cons:
- Duplicates ux_audit/contact_form/seo_title/approval logic — second drifting code path

Effort: medium
Risk: medium

## Recommended Action

Add the `first_party` flag (Option 1), explicitly relaxing `gbp_link`,
`analytics`, **and `dns_approved`** for subdomain launches while keeping the
hard items. Add a unit test: first-party run with no `gbp_url`/no DNS approval
still reports `ready`, while a client run does not. Specify the "reviewed
preview" artifact for the no-build path.

## Technical Details

- `packages/agency/launch.py` `run_launch_checklist` (add param, relax 3 items).

## Acceptance Criteria

- [ ] First-party subdomain launch can reach `ready=True` without GBP/analytics/DNS approval.
- [ ] Relaxed items are recorded (not silently dropped) in the report.
- [ ] Hard items (contact_form, seo_title, ux_audit, deploy_approved) remain enforced.
- [ ] Unit test covers first-party vs client divergence.
- [ ] §8 names what satisfies "reviewed preview" under file-digest upload.

## Work Log

### 2026-06-02 - Initial review capture
Verified directly against launch.py / deploy_readiness.py during `/review`.

### 2026-06-02 - Fixed (Option 1)
Implemented `first_party: bool = False` in `run_launch_checklist`
([launch.py:49](../packages/agency/launch.py:49)): relaxes `gbp_link`,
`analytics`, and `dns_approved` as passed-with-reason ("relaxed: first-party …"),
recorded in the report; hard items (`ux_audit`, `contact_form`, `seo_title`,
`deploy_approved`) unchanged. Added `test_first_party_relaxes_gbp_analytics_dns`
and `test_first_party_still_requires_deploy_approval`. `pytest
tests/python/unit/test_agency_launch_checklist.py` → 6 passed. Plan §8 updated to
reference the flag and specify the no-build "reviewed preview" artifact. No
production callers existed (only tests), so the change is additive/backwards-compatible.
