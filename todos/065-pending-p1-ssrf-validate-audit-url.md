---
status: pending
priority: p1
issue_id: "065"
tags: [code-review, security, ssrf, better-business-web, agency]
dependencies: []
---

# Problem Statement

The BBW landing-page plan adds a public form whose "current site" URL is routed
into the Stage-2 verification loop, which performs **live website audits** of
that URL. The plan specifies no validation of the user-supplied URL. A public
form field that flows into an automated server-side fetch is a classic SSRF /
abuse vector, and no guard exists today in the agency/discovery/web packages.

## Findings

- The form collects a "current site/none" field — [LANDING_PAGE_PLAN.md:156](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:156).
- §10 routes submissions into the Stage-2 loop which does "live website audits" — [LANDING_PAGE_PLAN.md:194](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:194).
- The audit fetch path is real code: `packages/policies/verification_loop.py` and `packages/tools/primitives/verification_loop_runner.py`. A grep for `allowlist`/`ssrf`/`169.254`/private-range guards across `packages/agency`, `packages/discovery`, `packages/web` returns nothing — no protection exists.
- Attack surface: `http://169.254.169.254/...` (cloud metadata), `http://localhost:<port>`, `127.0.0.1`, RFC-1918 internal hosts on the always-on Mac running local infra (per CLAUDE.md). Also redirect-to-internal, decompression bombs, slow-loris to exhaust operator compute.
- "Manual for v1" reduces but does not remove the risk — a human pasting an attacker URL into the automated auditor still triggers the fetch.

## Proposed Solutions

### Option 1: Validate-and-deny at the audit boundary (recommended)
Before any fetch in the Stage-2 runner: require `https?://` scheme only; resolve
the hostname and reject loopback, link-local (169.254/16), and RFC-1918 ranges;
re-validate after each redirect (no redirect to internal); cap response size and
timeout.

Pros:
- Closes SSRF at the one chokepoint regardless of how the URL arrives
- Reusable for the outbound prospect lane too

Cons:
- Requires DNS-rebind-aware re-resolution to be fully correct

Effort: medium
Risk: low

### Option 2: Treat "current site" as display-only in v1; never auto-fetch
Collect the URL but require explicit operator confirmation + manual paste into a
sandboxed audit; no automated fetch from form input in v1.

Pros:
- Zero new code; fully removes the automated SSRF path for v1

Cons:
- Defers the real fix; relies on operator discipline

Effort: small
Risk: medium (human still triggers fetch)

## Recommended Action

Make the Stage-2 spec treat the submitted URL as untrusted and add scheme +
private-IP-range validation with redirect re-validation before the first fetch.
Decouple "submission received" from "audit runs" (see 074).

## Technical Details

- Add validation in `packages/tools/primitives/verification_loop_runner.py` (or a shared `packages/policies` helper) consumed wherever an external URL is fetched.

## Acceptance Criteria

- [ ] The plan/spec states the audited URL is untrusted input.
- [ ] Scheme allowlist (`http`/`https` only) enforced before fetch.
- [ ] Loopback, link-local, and RFC-1918 destinations rejected, re-checked after redirects.
- [ ] Response size + timeout caps specified.

## Work Log

### 2026-06-02 - Initial review capture
Surfaced by security-sentinel during `/review` of the landing-page plan.

### 2026-06-02 - Plan amended (diagnose+fix, P1 pass)
Plan §7 now requires the "current site" URL be treated as untrusted: scheme
allowlist, reject loopback/link-local/RFC-1918, re-validate after redirects,
size/timeout caps — before any fetch. **Runtime hardening still pending**: add
the guard at the fetch boundary (`verification_loop_runner.py` + prospect-site
build). Keep open until the code guard + a unit test land.
