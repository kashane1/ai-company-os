---
status: complete
priority: p1
issue_id: "096"
tags: [security, product-planning, guppy]
dependencies: []
---
# Guppy audit and independent collector-app founder pack

## Problem Statement
Audit the founder's installed and running Guppy app and deliver an executable founder pack for an independently written public-source alternative.

## Findings
Installed Guppy 26.9.14, bundle so.guppy.desktop, DropKit Inc. Running collector/shopping agent. Private audit evidence belongs only in locally Git-excluded state/guppy-audit/.

## Proposed Solutions
1. Evidence-based local audit plus product concept research and complete plan (selected).
2. Full reverse engineering and live transaction testing (outside necessary scope; avoid real purchases or data changes).

## Recommended Action
Run independent security and public-research lanes; root integrates runtime/UI evidence, recommendations, founder requirements, design options, architecture, backlog, tests, economics, and public-repo handoff.

## Acceptance Criteria
- [x] Context and app identity verified.
- [x] Founder preference question asked; assumptions labeled if unanswered.
- [x] Signature, runtime, network, persistence, permissions, static security audited with explicit limits.
- [x] Product alternatives and adopt/adapt/defer/skip matrix documented.
- [x] Proposed design and executable implementation plan delivered without copying vendor code.
- [x] Private audit evidence excluded from Git; public-pack links and completeness reviewed.

## Work Log
### 2026-09-20 — Started
Read workspace routing, project agent model, security and brainstorming skills. Delegated static audit and public research. User authorized research and planning; future app repository must be public. No app implementation or public publication in this task.

### 2026-09-20 — Completed audit and founder pack
Delivered private audit report under state/guppy-audit/2026-09-20/AUDIT-REPORT.md and the independent founder pack under docs/products/open-collector/README.md, with canonical plan pointer under docs/plans/. Verified signatures/Gatekeeper, DMG-to-vendor-feed SHA512, process and network observations, selected macOS permissions, persistence locations, targeted packaged-code review, local health metadata, and app UI settings. Found unsupported Electron 41.2.0 and documented sensitive capabilities without claiming malware/exploit proof. No app settings, permissions, missions or credentials changed; no purchase attempted.

Product pack includes research, feature decisions, requirements, UI flows/wireframe, architecture/security/data contracts, milestones, first implementation tickets, free/paid economics, validation/launch, and fresh public-repository handoff. Independent reviewers corrected deduplication, pause races, browser-handoff replay, purchase reconciliation and audit wording. Assumptions remain proposed; no application implementation or public repository was created. Final checks: ten documentation files have valid local links/fences/whitespace; private-data marker scan passed; 37 evidence files indexed; source hash agrees; audit tree excluded and untracked. No application tests apply to documentation-only delivery; future commands are explicitly labeled unrun.
