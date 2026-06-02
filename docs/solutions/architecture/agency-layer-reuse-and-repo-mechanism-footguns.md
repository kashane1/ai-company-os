---
title: "Agency layer: reuse over rebuild, and four repo-mechanism footguns that derail plans"
category: architecture
date: 2026-06-01
tags:
  - agency-layer
  - prospecting
  - web-lane
  - product-registry
  - policy-gates
  - skill-wiring
  - planning
module: packages/agency
symptom: "A from-scratch-sounding feature request (turn the repo into a local-SMB agency) was 60% already built, and the first implementation plan described three repo mechanisms the way they 'should' work rather than how they actually work — each would have derailed execution if not caught in review."
root_cause: "Plans written from the outside (reading commit messages / file names) assume conventional mechanisms. This repo's registry loader, approval gates, and skill loader each enforce stricter contracts than their names imply. Verifying every load-bearing claim against the source before coding turned three latent P1s into doc edits instead of failed phases."
---

# Agency layer: reuse over rebuild, and four repo-mechanism footguns

## The reuse insight (compounding win)

The "turn `ai-company-os` into a local-SMB agency" request sounded greenfield. It
wasn't. Two shipped subsystems already covered most of it:

- **Prospecting (Phase 1–2)** already finds the exact target — local SMBs with no
  owned website — and human-verifies them (`packages/prospecting`,
  `packages/schemas/prospect.py`).
- **The web lane (F1–F8)** already scaffolds → builds → deploys → audits →
  monetizes a site (`packages/web/{scaffold,validation,ux_audit,deploy,stripe_monetization}.py`).

The only genuinely missing piece was the **client-lifecycle seam** connecting the
two halves. Lesson for future "build X" requests here: **inventory the shipped
lanes first** — the highest-leverage work is usually a thin connective seam, not a
new subsystem. The agency layer added ~9 small modules and reused everything else.

## The four footguns (each was a plan claim that didn't match the source)

These are general — they will bite any future feature that touches the registry,
policy gates, or skills. Verify against the source, don't assume.

### 1. The product registry is a strict typed loader, not a tolerant bag

`packages/config/products.py:load_product_configs` reads `platform`, `repo_id`,
`source_path`, `docs_root` as **required keys** and builds a `frozen`
`ProductConfig`. `ProductPlatform` had only `IOS`/`WEB`. A plan that says "add a
field to `products.json` and tolerate it" is wrong — unknown keys are dropped,
missing required keys raise. **Adding a record shape = a `packages/schemas/`
edit + a loader branch (founder-approved), not a JSON-only change.** New optional
fields must default so legacy records keep loading (`type: ProductType =
PRODUCT`, `client: ClientConfig | None = None`).

### 2. An approval gate is a function, not an enum member

`packages/policies/approvals.py` holds only the `PolicyViolationCode` enum +
`PolicyViolation` + `is_approval_granted`. Adding an enum member does **nothing**
on its own. The real pattern (see `deploy_readiness.assert_deploy_ready` /
`assert_custom_domain_allowed`, `discovery_gates.assert_bulk_crawl_allowed`) is a
**dedicated `assert_<action>(*, approval_granted: bool)` function in its own
policy module** that raises `PolicyViolation(code, detail)`. The agency layer
added `packages/policies/agency_gates.py`. Also: `tests/python/unit/test_policy_violation_codes.py`
enumerates codes — new codes + their raise sites + a presence assertion must land
together.

### 3. The skill loader is fixture-gated; reuse the package, not the skill

`packages/tools/skills/loader.py` refuses to load any `kind: agentic` skill with
`fixture_status != "passing"` in `mode="autonomous"`. `landing-page-build` and
`web-ux-audit` are both `fixture_status: missing` — so "compose the skill"
doesn't work autonomously. The composable units are the **pure callables**:
`packages.web.ux_audit.audit_dist()` (note: `.passed` is a **property**, not a
method), `packages.web.validation.validate_web_dist()`, `packages.web.scaffold`.
The launch checklist composes `audit_dist`, not the `web-ux-audit` skill.

### 4. `.claude/skills/` is operator-owned and agent-write-blocked

Skill wiring is canonical → adapter → `registry.yaml` → `.claude/skills/` pointer.
An agent **cannot write the `.claude/` pointer** (protected surface). The drift
detector (`packages/tools/primitives/registry_drift.py`) flags `orphan_canonical`
(canonical file with no registry entry) and `dangling_project_skill` (registry
entry whose pointer is missing) — but **skips entries with no `project_skill`
key**. So the clean wiring an agent *can* fully land is: canonical + adapter +
registry entry **with `project_skill` omitted**, leaving the `.claude/` pointer as
a documented one-line operator follow-up. This introduces zero drift.

## Environment note (this sandbox only)

14 repo modules use `datetime.UTC` (Python 3.11+); the agent sandbox runs 3.10, so
those modules and ~15 test files fail to *collect* and ~5 supervisor/worker tests
fail — all pre-existing and reproducible on pristine `main`. Keep new code
3.10-importable (use `datetime.now(timezone.utc)`) so its tests run here; the full
suite is green under the repo's target 3.12.

## What "verify before coding" bought

Three claims that read as reasonable in the plan — "tolerate the new registry
field", "add an approval code and wire it", "compose the web-ux-audit skill" —
were each wrong about the actual mechanism. Catching them in an adversarial plan
review (and again in a final code review) cost minutes; shipping them would have
cost failed phases. Related: [pre-existing-failures-are-often-test-bugs](../test-failures/pre-existing-failures-are-often-test-bugs.md).
