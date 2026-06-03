---
status: pending
priority: p2
issue_id: "071"
tags: [code-review, reliability, netlify-forms, better-business-web, agency]
dependencies: []
---

# Problem Statement

§4 deliberately bypasses `astro build` and publishes via raw file-digest upload
to save Netlify minutes. §7 then relies on Netlify auto-detecting the form from
deployed HTML — a feature traditionally tied to build/post-processing. The two
decisions may be incompatible: with no build, auto-detection may never fire and
the CTA (the funnel's only conversion point) silently posts into the void. The
plan flags "test-deploy and verify" but specifies no fallback if verify fails.
Separately, the Python-side render (§4) could drop the `data-netlify`/honeypot
attributes during token injection.

## Findings

- No-build file-digest upload — [LANDING_PAGE_PLAN.md:100](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:100); deploy mechanism at [deploy.py:159](../packages/web/deploy.py:159).
- Form auto-detection dependency + "must be test-deployed and verified... don't assume" — [LANDING_PAGE_PLAN.md:157](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:157).
- Markup is rendered Python-side, not by Astro — risk the netlify attributes are dropped by partial injection.

## Proposed Solutions

### Option 1: Verify, with a pre-committed fallback handler (recommended)
Test-deploy and confirm detection. If it fails, fall back to either (a) a minimal
Netlify function form-handler, or (b) a one-off built deploy solely to register
the form schema. Add form-attribute presence + a live test submission to the §8
launch hard items so it fails closed.

Pros:
- CTA can't silently die; recovery path exists before launch

Cons:
- Maintains a fallback path

Effort: medium
Risk: low

### Option 2: Accept one Astro build for this single site
Let Astro build the one rarely-changed site so native form detection just works
(see 076).

Pros:
- Detection is the supported happy path; removes the incompatibility

Cons:
- Spends (small) build minutes the plan tried to avoid

Effort: small
Risk: low

## Recommended Action

Verify detection under file-digest upload; pre-commit a fallback; make form
detection + a live test submission a hard launch-gate item.

## Acceptance Criteria

- [ ] Form detection confirmed on a real deploy of the file-digest artifact.
- [ ] A fallback is specified and ready if detection fails.
- [ ] `data-netlify`/honeypot attribute presence asserted in the render guard.
- [ ] Launch gate fails closed if the form isn't detected.

## Work Log

### 2026-06-02 - Initial review capture
Surfaced by audit + spec-flow-analyzer + security-sentinel during `/review`.

### 2026-06-02 - Resolved by build decision (Option 2)
Operator chose to let Astro build the BBW site (plan §4 decision update), so
native Netlify form detection is the supported happy path — the no-build↔detection
tension is gone. Still verify on a real deploy before launch (keep open until the
first deploy confirms the form is detected).

### 2026-06-02 - CONFIRMED on first deploy: form NOT detected
Deployed the site to production via `NetlifyDeployTarget` (file-digest API deploy,
not a Netlify build). `GET /sites/{id}/forms` returns `[]` — Netlify's
form-detection postprocessing does not run for file-digest API deploys, even with
the static `form-name` hidden input present. The site is live and the form posts
to `/thanks/`, but submissions are not captured. **Fix:** git-link the repo to
Netlify so it runs `astro build` (base dir `products/better-business-web/site`) —
that triggers native detection — OR add a Netlify Function POST handler. The
`deploy_bbw.py` file-digest path is fine for the static pages but cannot enable
Forms. Still open; P2 → effectively P1 for launch since the form is the funnel's
only conversion point.
