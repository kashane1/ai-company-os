---
status: completed
priority: p2
issue_id: "013"
tags: [code-review, plan-doc, ecc-gap-plan]
dependencies: []
---

# Problem Statement

Five plan-documentation clarifications surfaced during the technical review that are text-only fixes but need to land before Phase 1 implementation begins. Bundled into one todo because each is small and they all live in the same plan document.

## Findings

### 1. Legacy `self_evolvable` invariant test (spec-flow #7)

The plan's invariant says six new skills ship with `self_evolvable: false` explicit. The existing 22 skills have it implicit-false. The deferred `registry_schema_drift` check is the only thing that would catch a legacy entry being implicitly promoted. There's no flow that catches a legacy entry getting `self_evolvable: true` added without going through the Hermes allowlist.

**Fix:** Add `tests/python/unit/test_no_legacy_self_evolvable_promotion.py` to Phase 2a (not deferred with the rest of schema-drift). Asserts every entry NOT in the Hermes Phase 3 allowlist has `self_evolvable` either absent or explicitly `false`.

### 2. Follow-up issue authorship is undefined (spec-flow #8)

Plan says "captures as follow-up issue" but never names the author. Closed properly by todo 005 (`followup_issue_writer.py`), but the plan text still needs a sentence pointing at that primitive.

**Fix:** Phase 2a + Phase 4 Deliverables sections cite `packages/tools/primitives/followup_issue_writer.py` as the drift-capture sink.

### 3. Trigger-phrase disambiguation rule (spec-flow #10)

"check the docs" (documentation-lookup), "audit the skill estate" (skill-stocktake), "pre-PR sweep" (verification-loop) — several new phrases overlap. An operator typing an ambiguous phrase could be routed to the wrong skill. The plan relies on Claude runtime matcher but matcher semantics aren't specified.

**Fix:** Add a Phase 1 DoD item: CLAUDE.md trigger-phrase section gains a one-sentence rule at the top: "If multiple trigger phrases could apply, Claude MUST ask which skill to invoke rather than guess." Add an `adversarial_ambiguous_phrase.yaml` fixture per Phase 1 skill asserting the canonical body instructs disambiguation.

### 4. Verification-loop caller-mapping table (arch strategist #5)

Two entry points (`packages/policies/verification_loop.py` for gating, `packages/tools/primitives/verification_loop_runner.py` for advisory) with no documented caller mapping. Duplicate-logic vector.

**Fix:** Add a table in the Phase 3 section listing each caller (CI, trigger-phrase invocation, `release_readiness.py` future composition, Codex via deferred runner, Hermes evolution worker) and which entry point it uses. Pin it in `verification_loop.py`'s module docstring too.

### 5. Follow-up authoring sink reference

Plan text should reference todo 005's `followup_issue_writer.py` wherever it currently says "captures as a follow-up issue" (Phase 2a Risks, Phase 4 Deliverables, Phase 2b Risks).

## Proposed Solution

Single plan-doc edit PR that adds all five clarifications. No runtime code changes. Ships before Phase 1 kickoff so Phase 1 PR authors have the clarifications.

## Acceptance Criteria

- [ ] `test_no_legacy_self_evolvable_promotion.py` scoped into Phase 2a deliverables (plan doc)
- [ ] Phase 2a + Phase 4 reference `followup_issue_writer.py` as the drift-capture sink
- [ ] Phase 1 DoD includes the CLAUDE.md disambiguation rule + adversarial fixture per skill
- [ ] Phase 3 section includes a caller→entry-point mapping table
- [ ] Plan references todo 005 wherever "follow-up issue" is mentioned

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
**Actions:** Bundled five plan-doc clarifications from spec-flow-analyzer and architecture-strategist into one edit.
