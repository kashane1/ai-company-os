# Web Design Studio Lane Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Design Studio layer to the web lane so premium art direction, reference translation, imagery planning, screenshot QA, and visual critique become structured parts of the website build process.

**Architecture:** Keep the existing web/agency lanes. Add a pure Python `packages.web.design_studio` contract that produces design packets and visual review reports; markdown docs explain how prospect demos and paid client sites consume those artifacts. The existing build, deploy, and technical validation gates remain intact.

**Tech Stack:** Python dataclasses, existing `ValidationCheck`, pytest, markdown docs.

---

### Task 1: Design Studio Contract Tests

**Files:**
- Create: `tests/python/unit/test_web_design_studio.py`
- Create later: `packages/web/design_studio.py`

**Step 1: Write failing tests**

Cover:
- A local-business request produces a packet with concept, archetype, type direction, imagery plan, motion plan, reference translations, build phases, and visual QA requirements.
- Reference translation keeps sources as inspiration rather than copy targets.
- The review rubric fails a technically valid but generic page.
- The review rubric passes only with high scores and desktop/mobile screenshots.
- Packet serialization produces stable structured data.

**Step 2: Run tests to verify RED**

Run: `pytest tests/python/unit/test_web_design_studio.py -q`
Expected: fail because `packages.web.design_studio` does not exist.

### Task 2: Minimal Design Studio Implementation

**Files:**
- Create: `packages/web/design_studio.py`

**Step 1: Implement dataclasses and helpers**

Add:
- `DesignReference`
- `WebsiteDesignRequest`
- `ReferenceTranslation`
- `DesignStudioPacket`
- `VisualScore`
- `VisualReviewReport`
- `build_design_studio_packet`
- `review_visual_quality`

**Step 2: Run focused tests**

Run: `pytest tests/python/unit/test_web_design_studio.py -q`
Expected: pass.

### Task 3: Documentation Wiring

**Files:**
- Modify: `packages/web/README.md`
- Create: `docs/agency/design-studio-lane.md`
- Modify: `docs/agency/README.md`

**Step 1: Document the workflow**

Explain the new layer:
`intake/evidence -> design studio packet -> build -> screenshot -> visual review -> existing technical gates -> deploy approval`.

**Step 2: Avoid dirty files**

Do not edit the currently dirty demo playbook or generated nails assets in this pass.

### Task 4: Verification

**Files:**
- No new files unless tests require small adjustments.

**Step 1: Run focused tests**

Run: `pytest tests/python/unit/test_web_design_studio.py -q`
Expected: all tests pass.

**Step 2: Run related web tests**

Run: `pytest tests/python/unit/test_web_scaffold.py tests/python/unit/test_web_validation.py tests/python/unit/test_web_ux_audit.py tests/python/unit/test_web_design_studio.py -q`
Expected: all selected tests pass.

**Step 3: Inspect git diff**

Run: `git diff --stat` and `git diff --check`
Expected: only intended files changed, no whitespace errors.
