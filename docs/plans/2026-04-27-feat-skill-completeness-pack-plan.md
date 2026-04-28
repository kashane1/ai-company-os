---
title: Skill Completeness Pack — fixtures + iOS bodies + GTM internal-only marking
type: feat
status: active
date: 2026-04-27
---

# Skill Completeness Pack

## Enhancement Summary

**Deepened on:** 2026-04-27
**Review agents used:** architecture-strategist, code-simplicity-reviewer, pattern-recognition-specialist

### Binding revisions (override the original phase content where they conflict)

1. **Reuse existing `target_runtimes` primitive — do NOT introduce `internal_only`.** Pattern review found `target_runtimes: []` is the existing convention for "not directly Claude-invocable" (see `bounded-codex-implementation`, `worktree-lifecycle`, `repo-sync` in [skills/registry.yaml](../../skills/registry.yaml)). The 5 GTM internal skills currently mis-declare `target_runtimes: [claude]` despite having no Claude adapter — that's the actual drift to fix. Add `invoked_by: [...]` as the *only* new key, capturing the composition relationship that `target_runtimes` doesn't express.

2. **Per-skill test files in `tests/python/unit/`, not grouped integration files.** Existing convention is `tests/python/unit/test_<skill_id>_fixtures.py` (see `test_codex_claude_handoff_fixtures.py`, `test_product_artifact_chain_fixtures.py`, `test_supervisor_goal_decomposition_fixtures.py`). Original plan's `test_gtm_skill_fixtures.py` / `test_ios_skill_fixtures.py` grouped files broke this — replaced with 7 per-skill files in `tests/python/unit/`.

3. **Bare fixture names for single-fixture cases.** GTM-skill neighbors (`content-voice-guardrail`, `social-post-safety`, `aso-keyword-refresh`, `creator-outreach-draft`) all use bare `happy_path.yaml`. Use that form. Suffix only when a skill genuinely needs multiple fixtures per category (the `verification-loop` precedent).

4. **One fixture per skill, not three.** Simplicity review correct: for agentic skills with no replay loader, three variants of an unexecuted shape contract is theater. Ship one `happy_path.yaml` per skill (7 fixtures, not 21). Add boundary/adversarial only when a real regression motivates them.

5. **Drop the "≥250 lines" iOS body metric.** Replace with: "must contain 8 named sections, each non-empty." Pattern review found `verification-loop` (the stated structural template) has 8 actual sections — mirror those exactly: Purpose, When to invoke, Contract, Sub-checks (or Procedure for non-composing skills), Severity enum (where applicable), Caller → entry-point mapping, Boundaries and failure modes, References. Original plan listed 10 invented sections — corrected.

6. **Drop helper-code unit tests for content-factory and content-scheduler.** Out of scope for "skill completeness." The Postiz envelope-shape regression already has its own solutions doc — if a test is wanted there, it's a one-file follow-up plan, not bundled scope. Removing this drops Phase 2 effort by ~0.5 day.

7. **Drop the `## Internal Only` body section.** Duplicate signaling. Registry `target_runtimes: []` + `invoked_by: [...]` is the machine-readable source of truth; no need for prose blurb that will drift. Skill-stocktake update can surface the relationship once instead of 5×.

8. **Schedule a `/schedule` cron at merge time for orphan cleanup, not a TODO comment.** Architecture review correct: TODOs are predicted to fail. Use the `schedule` skill to queue a 2026-05-27 review of `aso-keyword-refresh` and `creator-outreach-draft` (delete or re-wire decision).

### Adjustments rejected

- **Split Item C into its own PR** (architecture review). Rejected because pivoting to `target_runtimes: []` (an existing primitive) means no schema-extension cost — no loader changes, no rippling impact. The "let it bake" justification dissolves. Keep single PR.
- **Reverse-edge invariant check** (`invoked_by` → grep parent adapter for child skill_id). Useful but adds skill-stocktake work outside this plan's scope. Defer to a follow-up that hardens skill-stocktake.
- **Delete orphans NOW** (simplicity review). Rejected because both have `fixture_status: passing` (someone invested in fixtures), suggesting planned-but-unused. Marking + scheduled review preserves the option; deletion forecloses it. Reversibility wins on a low-risk decision.
- **Mocked vs live API contract framing** (architecture). Conceded but moot — helper-code tests are dropped per #6.

### Net effect

- Phase scope shrinks: 21 fixtures → 7; 2 helper test files → 0; 5 body sections + 5 registry annotations → 5 registry annotations only; `internal_only` schema extension → reuse `target_runtimes: []` + add `invoked_by`.
- Effort estimate revised: ~4 days → ~2 days.
- Surface area: 7 fixture files, 7 test files, 1 registry update with 5 entries modified, 3 iOS canonical body expansions, no helper code, no new keys beyond `invoked_by`.

---

## Overview

Three items from the 2026-04-27 audit, scoped to `skills/` and `tests/` only:

- **Item A** — Add regression fixtures + integration tests for 4 GTM skills currently `fixture_status: missing` (`niche-research-brief`, `gtm-artifact-refresh`, `content-factory`, `content-scheduler`).
- **Item B** — Flesh out canonical bodies + add fixtures for 3 critical-path iOS skills (`ios-ui-polish-review`, `ios-to-appstore-handoff`, `app-store-positioning-pack`).
- **Item C** — Resolve callability ambiguity for 5 GTM internal skills by explicitly marking them internal-only in the registry with caller annotations (`content-voice-guardrail`, `social-post-safety`, `aso-keyword-refresh`, `creator-outreach-draft`, `approval-token-audit`).

Ships as **one PR with three phases** since all artifacts touch the same surfaces (`skills/registry.yaml`, `skills/canonical/`, `skills/adapters/claude/`, `tests/python/integration/`) and benefit from a single atomic commit per the multi-component-commit pattern documented in [docs/solutions/architecture/multi-phase-plan-shipping-primitives-skills.md](../solutions/architecture/multi-phase-plan-shipping-primitives-skills.md).

## Problem Statement

The 2026-04-27 audit found:

- **13 skills with `fixture_status: missing`.** Of those, 7 are in active use (4 GTM content-pipeline skills + 3 iOS skills). Without fixtures, they're unprotected against regression as the canonical body or contract evolves.
- **3 incomplete iOS skills.** Catchbook is in App Store submission phase — `ios-ui-polish-review` (117 lines, sparse checklist), `ios-to-appstore-handoff` (105 lines, sparse build-readiness steps), `app-store-positioning-pack` (176 lines, more detailed but missing examples). Each has a Claude adapter but the canonical bodies are too thin to drive consistent agent behavior.
- **5 GTM internal skills with no Claude adapter.** Research confirms 3 are *composed dependencies* (invoked by another skill's adapter, not by Claude directly): `content-voice-guardrail` is called by `gtm-artifact-refresh`, `social-post-safety` is called by `content-scheduler`, `approval-token-audit` is called by `apps/api/approval_endpoint.py`. The other 2 (`aso-keyword-refresh`, `creator-outreach-draft`) have **zero** invocations — orphaned. The registry doesn't disambiguate composed-vs-orphan.

## Proposed Solution

### Item A — Fixtures for 4 GTM agentic skills

All 4 skills are `kind: agentic` (LLM-driven). Per `packages/tools/skills/loader.py:load_validator()`, only `kind: validator` skills can be replay-tested. Therefore "fixtures" here are **shape/contract YAML files** validated for structure, not replay tests. Two test layers:

1. **Schema reconciliation** — every fixture YAML parses, declares `skill_id`, `case_name`, and the canonical body's documented input/output fields.
2. **Helper-code unit tests** — for skills with Python helpers, test the helpers directly:
   - `content-factory` calls `packages/tools/content_tools/gemini_images.py` + `text_overlay.py`. Test the text-overlay output shape (output paths, file existence) using a stub gemini client. (Don't hit the real Gemini API in tests.)
   - `content-scheduler` calls a Postiz API client. Test the post-payload shape (Postiz draft envelope per `docs/solutions/integration-issues/social-media-publishing-nuances.md`: `posts[].integration.id`, media `id` + `path`, per-platform hashtag caps).
   - `niche-research-brief` and `gtm-artifact-refresh` are pure-LLM with no Python helpers — schema reconciliation only.

### Item B — Flesh out 3 iOS skills + fixtures

Per skill:
1. Expand canonical body to include explicit step-by-step procedure, severity taxonomy (for review-type skills), required outputs, edit boundaries, failure modes, and at least one worked example. Target ~250-350 lines, not 100-180.
2. Add 3-4 fixture YAMLs covering: happy path, boundary case, adversarial / common-mistake case.
3. Update registry `fixture_status: passing`.

### Item C — Mark 5 GTM internal skills internal-only

**No new adapters.** Per the WIRING.md convention, the adapter chain is for skills Claude invokes directly. Composed dependencies invoked by another skill's adapter are internal to that skill — adding a separate Claude adapter would create dual call paths and registry confusion.

Per skill, add to `skills/registry.yaml`:

```yaml
- id: content-voice-guardrail
  ...
  internal_only: true
  invoked_by: [gtm-artifact-refresh]
  notes: |
    Composed dependency. Invoked by gtm-artifact-refresh during the
    refresh procedure as a hard voice gate. Not callable directly by
    Claude.
```

For orphans (`aso-keyword-refresh`, `creator-outreach-draft`): mark `internal_only: true` and `invoked_by: []` with a note flagging them for cleanup or re-wiring in a future plan.

Also add a one-line `## Internal Only` section to each canonical body so anyone reading the canonical knows the call shape without grepping the registry.

## Implementation Phases

### Phase 1 — Item C (smallest, do first)

**Deliverables:**
- `skills/registry.yaml` updates for the 5 internal-only skills (one block per skill: `internal_only: true`, `invoked_by: [...]`, `notes`).
- `## Internal Only` section appended to each canonical body (5 files):
  - `skills/canonical/content-voice-guardrail/skill.md`
  - `skills/canonical/social-post-safety/skill.md`
  - `skills/canonical/aso-keyword-refresh/skill.md`
  - `skills/canonical/creator-outreach-draft/skill.md`
  - `skills/canonical/approval-token-audit/skill.md`
- Skill-stocktake unchanged (the existing `skill-stocktake` skill already detects orphan adapters — flag it in the plan if it surfaces these as drift).

**Tests:**
- Extend `tests/python/unit/test_skill_reconciliation.py` (or create) to assert: every skill in the registry with `internal_only: true` has `invoked_by` populated, and at least one referenced caller exists. For orphans (`invoked_by: []`), assert a note explains why.

**Acceptance:**
- Registry validates.
- `skill-stocktake` reports zero drift around these 5 skills.
- Reading any of the 5 canonical bodies, the call shape is obvious within the first 20 lines.

**Estimated effort:** 0.5 day.

### Phase 2 — Item A (4 GTM skills, fixtures + helper tests)

**Deliverables:**

Per skill (4 ×):
- `skills/canonical/<skill-id>/fixtures/` directory with 3 fixture YAMLs:
  - `happy_path_contract_shape.yaml` — minimal valid input/output the skill should accept/produce.
  - `boundary_<topic>.yaml` — domain-specific boundary (e.g. for `gtm-artifact-refresh`: empty backlog; for `content-factory`: text-only post no image).
  - `adversarial_<topic>.yaml` — common-mistake guard (e.g. for `content-scheduler`: Postiz payload missing `integration.id`).

Helper-code tests where applicable:
- `tests/python/unit/test_content_factory_helpers.py` — exercises `text_overlay.py` shape. Use a stub gemini client that returns a fixed-bytes image; assert text-overlay output is a PNG of expected dimensions and the path layout matches the canonical body's "Output" section.
- `tests/python/unit/test_content_scheduler_postiz_payload.py` — given a content backlog item + product config, assert the produced Postiz draft envelope shape (`posts[].integration.id` not `channelId`; per-platform hashtag caps from `docs/solutions/integration-issues/social-media-publishing-nuances.md`).

Schema reconciliation:
- `tests/python/integration/test_gtm_skill_fixtures.py` — for each of the 4 skills, glob the fixtures dir, parse each YAML, assert it declares `skill_id`, `case_name`, `inputs`, `expected_outputs` (or `expected_verdict`), and that `skill_id` matches the directory.

Registry:
- Update `fixture_status: passing` for all 4 skills.

**Acceptance:**
- All new tests pass.
- Test count delta ≥ 12 fixture-shape assertions + ≥ 6 helper-code assertions.
- Existing 412+ passing unit tests stay green.

**Estimated effort:** 1.5 days (most time in writing realistic fixture content, not boilerplate).

### Phase 3 — Item B (3 iOS skills, body expansion + fixtures)

**Deliverables:**

For each iOS skill:
1. Expanded canonical body with these sections (use `verification-loop/skill.md` as the structural template):
   - Purpose (existing)
   - When to invoke (existing)
   - Procedure — explicit numbered steps
   - Inputs (typed list with examples)
   - Outputs (typed list with examples)
   - Severity taxonomy (for `ios-ui-polish-review` and `ios-to-appstore-handoff`)
   - Edit boundaries — what the skill is allowed to write
   - Failure modes — what to do when an input is missing or invalid
   - Worked example
   - References

2. 3-4 fixture YAMLs per skill:
   - `ios-ui-polish-review/fixtures/`: happy_path (clean polish), warning (minor polish issues), failing (major polish gaps). Inputs are file paths + screenshots; outputs are severity-tagged findings.
   - `ios-to-appstore-handoff/fixtures/`: ready_for_handoff, missing_screenshots, metadata_validation_failure.
   - `app-store-positioning-pack/fixtures/`: minimal_brief_to_positioning, character_limit_boundary, multi_locale_boundary.

3. Registry updates: `fixture_status: passing` for all 3.

**Tests:**
- `tests/python/integration/test_ios_skill_fixtures.py` — same shape-reconciliation pattern as Phase 2.

**Acceptance:**
- Each canonical body ≥ 250 lines and structurally complete.
- All fixtures parse and reconcile.
- The 3 iOS skills no longer appear in `skill-stocktake`'s "incomplete" list.

**Estimated effort:** 2 days (heavy on writing — these bodies need real domain content for the App Store submission flow).

## Decision Points

### Decision 1: composed-dependency wiring

**Q:** Should `content-voice-guardrail` and `social-post-safety` get their own Claude adapters since Claude *might* want to invoke them ad-hoc?

**Recommendation: NO.** Reasons:
- They're hard gates inside specific pipelines (GTM refresh, social scheduling). Direct invocation outside that context produces meaningless verdicts.
- Adding adapters creates a dual call path (via parent skill *or* via Claude direct) — registry confusion + ambiguity about which path is canonical.
- The `internal_only: true` annotation honored by future tooling (skill-stocktake, context-budget) is a cleaner long-term primitive than a thin pass-through adapter.

If the founder later wants direct invocability, a follow-up plan can promote one or both. Don't pre-build for hypothetical use.

### Decision 2: orphan handling

**Q:** Should `aso-keyword-refresh` and `creator-outreach-draft` be deleted instead of marked internal-only?

**Recommendation: mark, don't delete (yet).**
- Both skills have `fixture_status: passing` (someone wrote fixtures), suggesting they were planned for active use.
- Deletion is irreversible; orphan-marking is a safer signal that says "needs decision."
- Add a 30-day TODO in each skill body: "If this is still orphaned by 2026-05-27, delete via a follow-up cleanup plan."

### Decision 3: helper-code test scope for content-factory and content-scheduler

**Q:** Do we mock the Gemini and Postiz APIs, or skip those tests entirely (since they're not the skill itself)?

**Recommendation: mock.** The shape contracts (PNG output for content-factory; Postiz draft envelope for content-scheduler) are EXACTLY where regressions hide and where the prior incident in `social-media-publishing-nuances.md` happened (a hardcoded 5-cap silently truncated Instagram hashtags). Mock the API client, not the helper. Helper-code tests are unit tests; the agentic skill itself remains schema-reconciliation only.

## Honored learnings

From `docs/solutions/`:

1. **Single-line fixture assertions** (`docs/solutions/architecture/multi-phase-plan-shipping-primitives-skills.md` PS-2) — every substring assertion in a fixture-shape test must be `grep -F`'d against the source before commit. Word-wrapped strings fail silently.
2. **Atomic multi-component commits** (same file, Solution #4) — ship Phases 1+2+3 as one PR/commit since they all touch `skills/registry.yaml`. Avoid intermediate states where the registry is half-updated.
3. **No module-level `re.compile`** (same file) — if any helper test introduces regex, use `@functools.lru_cache(maxsize=1)` factories.
4. **Schema-before-adapter** (`docs/solutions/integration-issues/content-intelligence-skill-pair-design.md`) — for the GTM content-pipeline fixtures, validate against the existing `memory-schema.yaml` files; do not invent new field names that drift from canonical.
5. **Postiz nested payload** (`docs/solutions/integration-issues/social-media-publishing-nuances.md`) — `content-scheduler` helper test must assert `posts[].integration.id` (not `channelId`) and per-platform hashtag caps (Instagram 8, TikTok 5, Threads 3, X 3).

## System-Wide Impact

### Interaction graph

- Skill stocktake (`skills/canonical/skill-stocktake/`) reads `skills/registry.yaml` → recognizes new `internal_only` and `invoked_by` keys (will need a small update if it actively schemas the registry).
- Verification-loop (structural) → will see no change in drift since fixtures land alongside their `fixture_status: passing` flip.
- Worker-supervisor → unaffected. None of these skills are in the supervisor decomposition path.
- Worker-gtm `apps/worker-gtm/gtm/runner.py` → unchanged behaviorally; the skills it composes (`content-voice-guardrail`, `social-post-safety`) gain registry annotations but no code shape change.

### Error & failure propagation

- Phase 1 (Item C) is registry-metadata-only. No runtime failure surface added.
- Phase 2 (Item A) helper tests use mocked clients; cannot break production paths.
- Phase 3 (Item B) is documentation + fixture YAMLs; cannot break production paths.

### State lifecycle risks

None. No new state directories, no schema migrations, no on-disk artifact changes.

### API surface parity

- The only API surface change is the registry adding `internal_only` and `invoked_by` keys. Skill stocktake should be updated in the same commit to recognize these (otherwise drift detection will warn). The existing `skill-stocktake` skill at `skills/canonical/skill-stocktake/` is the reader.

### Integration test scenarios

1. After Phase 1: skill-stocktake reports zero drift; reading the registry, every `internal_only: true` skill has at least one referenced caller (or a documented orphan note).
2. After Phase 2: `tests/python/integration/test_gtm_skill_fixtures.py` passes; helper tests for content-factory + content-scheduler pass with mocked clients.
3. After Phase 3: `tests/python/integration/test_ios_skill_fixtures.py` passes; the 3 iOS canonical bodies each contain the 8 required sections.
4. End-to-end: `skills/registry.yaml` `fixture_status` count for `missing` drops by 7 (4 GTM + 3 iOS).

## Acceptance Criteria

### Functional (revised per deepening)

- [x] 5 GTM internal skills each have `target_runtimes: []` + `invoked_by: [...]` (or `[]` for orphans) in `skills/registry.yaml`. Reused existing `target_runtimes` primitive instead of inventing `internal_only`.
- [x] Per-skill explanatory comment in registry; canonical body sections dropped per simplicity review.
- [x] 4 GTM agentic skills each have a `happy_path.yaml` fixture and `fixture_status: passing`. Helper-code unit tests deferred to follow-up plan.
- [x] 3 iOS skill canonical bodies extended with severity taxonomy / record-schema / failure-modes / worked-example sections. Line count metric dropped per architecture review.
- [x] 3 iOS skills each have a `happy_path.yaml` contract-freeze fixture and `fixture_status: passing`.
- [x] Per-skill `tests/python/unit/test_<skill>_fixtures.py` files (7 total) exist and pass.

### Non-functional

- [ ] No new external dependencies in `pyproject.toml`.
- [ ] All new tests pass.
- [ ] Existing 412+ tests stay green (excluding the pre-existing unrelated `test_real_catchbook_chain_valid` failure on main).
- [ ] No `re.compile` at module scope in any new file.
- [ ] Every fixture-shape substring assertion is `grep -F`-verified single-line.

### Quality gates

- [ ] `skill-stocktake` reports zero drift after the PR lands.
- [ ] `context-budget` reports each affected lane within budget.

## Success metrics

- `skills/registry.yaml` `fixture_status: missing` count drops by 7 (from 13 → 6).
- iOS canonical body line counts: `ios-ui-polish-review` ≥ 250 (from 117), `ios-to-appstore-handoff` ≥ 250 (from 105), `app-store-positioning-pack` ≥ 250 (from 176).
- Number of internal-only-but-unannotated skills drops to 0 (from 5).

## Dependencies & risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| iOS canonical body expansion produces stale or wrong content (founder hasn't reviewed) | Med | Med | Pull as much content as possible from existing Catchbook submission docs (`docs/products/catchbook/remaining-steps-before-ios-submission.md`, `docs/products/after-plans/founder-decisions-needed.md`); mark expansions clearly as draft for founder review |
| Mocked Postiz / Gemini tests drift from real API shape | Low | Med | Reference real-API gotchas from `docs/solutions/integration-issues/social-media-publishing-nuances.md`; add a comment in each test linking to the source |
| `internal_only` registry key not recognized by skill-stocktake | Low | Low | Update skill-stocktake in the same commit; add a regression test |
| 30-day cleanup TODOs for orphans get forgotten | Med | Low | Add as `/schedule` reminder when PR merges |

## Out of scope (explicit)

- No new harness / runtime code. The harness PR (#10) shipped this morning; this plan does not extend it.
- No re-architecture of any of these skills. Just complete + protect them.
- No deletion of orphan skills (deferred to a follow-up cleanup plan).
- No new app-side code. Worker entry points are unchanged.

## Sources & References

### Internal references
- `skills/registry.yaml` — registry schema (current: lines 1-450 cover the 12 affected skills).
- `skills/WIRING.md` — convention: canonical → adapter → project skill.
- `packages/tools/skills/loader.py:load_validator()` — replay-test gate for `kind: validator` skills.
- `tests/python/integration/test_failure_mode_regression.py` — validator test pattern.
- `skills/canonical/failure-mode-regression/fixtures/*.json` — JSON fixture shape.
- `skills/canonical/verification-loop/fixtures/*.yaml` — YAML fixture shape (preferred for new agentic skills).
- `docs/solutions/architecture/multi-phase-plan-shipping-primitives-skills.md` — single-line assertions, atomic commits, lazy regex.
- `docs/solutions/integration-issues/content-intelligence-skill-pair-design.md` — schema-before-adapter discipline.
- `docs/solutions/integration-issues/social-media-publishing-nuances.md` — Postiz payload shape.

### Related plans
- `docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md` — house-style reference for phase structure and fixture conventions.
- `docs/plans/2026-04-27-feat-postmortem-schema-and-adaptive-feedback-loop-plan.md` — sibling plan shipped today; same author, same conventions.
