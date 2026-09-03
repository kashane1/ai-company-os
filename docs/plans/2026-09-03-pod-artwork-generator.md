# POD Artwork Generator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a repo-native Codex skill that proposes founder-cleared art directions before generating and validating transparent merchandise artwork.

**Architecture:** Keep creative and approval logic in a canonical agentic skill, place the reusable visual vocabulary in one adjacent reference, and translate tool usage in a Codex adapter. Register the skill with passing behavioral fixtures and add only a thin `AGENTS.md` discovery route; generated artwork remains runtime state and all Printify/Etsy writes stay outside this skill.

**Tech Stack:** Markdown canonical skills, YAML contracts/fixtures/registry, Codex built-in image generation, Pillow-based read-only inspection commands, pytest skill reconciliation.

---

### Task 1: Record RED-phase behavior

**Files:**
- Create: `skills/canonical/pod-artwork-generator/fixtures/happy_path.yaml`
- Create: `skills/canonical/pod-artwork-generator/fixtures/boundary_product_adaptation.yaml`
- Create: `skills/canonical/pod-artwork-generator/fixtures/adversarial_skip_clearance.yaml`
- Create: `skills/canonical/pod-artwork-generator/contract.yaml`

**Step 1: Run baseline scenarios without the skill**

Use an independent agent that cannot read the proposed skill. Exercise a vague
shirt idea, a mug request based on a reference, and a request that combines image
generation with an unapproved Printify upload.

**Step 2: Verify the baseline exposes missing behavior**

Expected: at least one scenario generates or plans to generate before a dedicated
style-clearance stop, treats RGBA as sufficient proof of transparency, fails to
adapt composition to the product, or does not cleanly separate artwork creation
from external publishing operations.

**Step 3: Write the contract and behavioral fixtures**

Each fixture contains non-empty `input` and `expected` mappings. Freeze outcomes,
not exact prose: direction count, required clearance, distinctness, product-aware
composition, transparent PNG validation, exact text, output location, and no
Printify/Etsy mutations.

**Step 4: Run the intake validator to verify RED**

Run: `infra/scripts/validate-skill-intake.sh pod-artwork-generator`

Expected: FAIL because `skill.md` does not exist yet.

### Task 2: Write the minimal canonical skill

**Files:**
- Create: `skills/canonical/pod-artwork-generator/skill.md`
- Create: `skills/canonical/pod-artwork-generator/style-directions.md`

**Step 1: Implement only behavior required by the fixtures**

Define inputs, outputs, allowed runtime output paths, forbidden external actions,
the mandatory style-direction clearance, generation/revision flow, actual-alpha
checks, exact-text review, and product-specific recomposition.

**Step 2: Add the curated style vocabulary**

Describe visual traits and good-fit signals for the seven families inferred from
the founder's examples. Treat them as starting points, not a fixed rotation or a
request to imitate a particular artist.

**Step 3: Run canonical intake validation**

Run: `infra/scripts/validate-skill-intake.sh pod-artwork-generator`

Expected: PASS through all ten structural checks, with registry promotion still
reported as pending.

### Task 3: Add Codex routing

**Files:**
- Create: `skills/adapters/codex/pod-artwork-generator.md`
- Modify: `AGENTS.md`

**Step 1: Write the Codex adapter**

Map canonical generation to the built-in image-generation capability, one call
per approved direction. Include non-destructive save behavior, local inspection,
inline previews, and final reporting without duplicating the entire canonical
skill.

**Step 2: Add a narrow AGENTS route**

Add one trigger rule for requests to create transparent POD, shirt, mug, or
merchandise artwork. Route to the adapter and do not place creative logic in
`AGENTS.md`.

**Step 3: Inspect the diff**

Run: `git diff -- AGENTS.md skills/adapters/codex/pod-artwork-generator.md`

Expected: only the thin route and adapter are present; existing founder workflow
instructions remain unchanged.

### Task 4: Register and reconcile the skill

**Files:**
- Modify: `skills/registry.yaml`

**Step 1: Add the registry entry**

Register `pod-artwork-generator` as an internal, active, agentic, Codex-targeted
skill with passing fixtures and its Codex adapter.

**Step 2: Run focused checks**

Run: `infra/scripts/validate-skill-intake.sh pod-artwork-generator`

Expected: PASS with registry provenance and promotion confirmed.

Run: `.venv/bin/pytest tests/python/unit/test_skill_reconciliation.py -q`

Expected: PASS.

Run: `python3 scripts/skills/gen_project_skills.py --check`

Expected: PASS with no Claude project-skill drift because this skill targets
Codex only.

### Task 5: GREEN-phase behavioral verification

**Files:**
- Modify if a demonstrated gap requires it: `skills/canonical/pod-artwork-generator/skill.md`
- Modify if runtime translation is unclear: `skills/adapters/codex/pod-artwork-generator.md`

**Step 1: Re-run the baseline scenarios with the skill**

Use an independent agent with the canonical skill and Codex adapter. Do not call
the live image generator; ask for the intended response and action sequence.

**Step 2: Verify GREEN**

Expected: the agent proposes three to five distinct directions, recommends a
fit, pauses for founder clearance before generation, retains exact wording,
adapts mug/apparel layouts, verifies actual transparency rather than file mode,
and stops before all Printify/Etsy mutations.

**Step 3: Refactor only demonstrated gaps**

Tighten ambiguous language if the evaluation finds a loophole, then repeat the
same scenario until it passes.

**Step 4: Run final verification**

Run: `infra/scripts/validate-skill-intake.sh pod-artwork-generator`

Run: `.venv/bin/pytest tests/python/unit/test_skill_reconciliation.py -q`

Run: `git diff --check`

Expected: all commands pass with no whitespace errors or unrelated changes.

