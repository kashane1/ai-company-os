---
title: Three new skills — ios-build-and-sign, approval-flow-review, test-coverage-audit
type: feat
status: active
date: 2026-04-27
---

# Three New Skills

## Enhancement Summary

**Deepened on:** 2026-04-27. **Reviewers:** code-simplicity, pattern-recognition.

### Tensions surfaced

- **Simplicity:** "Ship `ios-build-and-sign` only. Defer the other two — `test-coverage-audit` documents tooling not configured; `approval-flow-review` presupposes approval-spam volume that doesn't exist yet." Strong YAGNI case.
- **User instruction:** "Build only these three new skills" — explicit ask for all three with the documented adapter counts.
- **Pattern-recognition:** No skill in the repo today ships BOTH `adapters/claude/<id>.md` AND `adapters/codex/<id>.md`. Plan would be the first.

### Resolution (binding revisions)

1. **Ship all three** (honor user instruction) but mark `test-coverage-audit` and `approval-flow-review` with realistic state. They get full canonical bodies + fixtures so the contract is reviewable; whether they're `stage: active` (callable now) or `stage: deferred` (frozen contract, paused activation) depends on whether the tooling/call site exists. Per the `codex-claude-handoff` precedent (line 61 in registry: deferred but contract-frozen), `stage: deferred` is the established way to ship a skill ahead of its activation.
2. **Adapter counts honored per user spec.** `ios-build-and-sign` gets both Codex + Claude adapters. The Claude adapter is genuinely thin (it consumes the artifact emitted by the Codex run); the canonical body owns most of the contract, both adapters point back. Repo would gain its first two-adapter skill — flagged as a new convention to document in `skills/WIRING.md`.
3. **Fixture paths follow PR #11 patterns.** `ios-build-and-sign` co-locates with `ios-ui-polish-review` under `canonical/products/catchbook/fixtures/<skill-id>/happy_path.yaml`. The other two follow `canonical/shared/fixtures/<skill-id>/happy_path.yaml`. No new pattern invented.
4. **Registry placement: no fictional section.** Pattern review confirmed no "iOS skills section" header exists at the top of `skills/registry.yaml`. Place each new entry inline next to the closest existing peer (iOS skills near `ios-to-appstore-handoff`; `approval-flow-review` near `approval-token-audit`; `test-coverage-audit` near `post-run-validation`).
5. **Trigger-phrase bloat: prune to one per skill.** Plan originally listed 3-4 phrases per skill (10 total). Cut to one per skill (3 total) — the disambiguation tax compounds as `CLAUDE.md`'s trigger list grows.
6. **Drop fictional worked examples** in `test-coverage-audit` and `approval-flow-review` — both describe workflows with no current call sites; the example would go stale before being read. Keep the worked example in `ios-build-and-sign` (real failure modes, real workflow). Replace the absent worked examples with a "Worked example" section that says: "Deferred — populate when first call site exists. Tracked at `<plan-doc>`."
7. **Guard bump: 7 → 10** in `tests/python/unit/test_skill_contract_freeze.py` (all three ship `happy_path.yaml`).

### Reviewer recommendations rejected

- **Defer two of three skills entirely.** Rejected: user instruction is explicit. Mitigation: `stage: deferred` honestly represents that they're contract-frozen but not yet active.
- **Drop Claude adapter from `ios-build-and-sign`.** Rejected: user spec says "canonical + both adapters." Mitigation: keep the Claude adapter thin and document its narrow scope (read the artifact, validate identity) so it doesn't grow into a parallel build path.

### Net effect

- 3 canonical bodies, 4 adapters total (2 codex + 2 claude — `approval-flow-review` is claude-only), 3 project pointers, 3 fixtures, 3 registry entries, 3 trigger phrases, guard bump.
- ~14 file changes (down from the original plan's ~22).
- Two of three skills ship `stage: deferred` — contract frozen, activation paused until tooling/call site lands.

---

## Overview

Ship three new skills from the audit Tier 1 + Tier 2 list. All artifacts under `skills/` and `CLAUDE.md`; no runtime/policy code. One PR.

| Skill | Runtimes | Why |
|---|---|---|
| `ios-build-and-sign` | codex + claude | iOS build/sign workflow is currently a procedural black box in `worker-ios`. Make the contract explicit so retries, signing-state validation, and certificate-renewal handling become reviewable rather than implicit. |
| `approval-flow-review` | claude | `packages/policies/approvals.py` defines policy; no skill audits whether an approval request matches the policy *before* it reaches the founder. Reduces approval-spam and pre-validates context. |
| `test-coverage-audit` | codex + claude | `packages/policies/testing.py` defines coverage policy (55% Python, 20% iOS) but enforcement only happens in CI post-merge. Skill audits worktree diffs against policy before commit. |

## Problem Statement

The audit found these as **Tier 1 (real-problem)** new skills:

- **iOS build + sign** is a black box. Recent commits in `apps/worker-ios` and `infra/scripts/` touch fastlane, certs, schemes, but nothing captures the contract. Result: silent failures, no explicit retry semantics, no reviewable signing-state record.
- **Approval-flow review** is missing the gate that filters out malformed or policy-violating requests *before* the founder sees them. Today every approval request lands in the founder's inbox raw.
- **Test-coverage audit** is policy-as-code in `testing.py` but enforcement is post-merge only. Pre-merge audit lets workers fix coverage in the same task, not as follow-up tickets.

## Proposed Solution

Three skills, each shipping the full wiring chain per `skills/WIRING.md`:

```
canonical → adapter(s) → project pointer → fixture → registry entry → CLAUDE.md trigger phrase
```

All three follow the established 9-section canonical body convention proven in PR #11 (Purpose, Contract, Allowed edit boundaries, Forbidden areas, Dependencies, Instructions, Failure modes, Worked example, References).

All three use the existing `test_skill_contract_freeze.py` glob-parametrized runner (PR #11). Drop a `happy_path.yaml` under `<skill-dir>/fixtures/`; the runner picks it up automatically.

## Implementation Phases

This PR stacks on top of `feat/skill-completeness-pack` (PR #11) so the contract-freeze runner is available. If #11 hasn't merged when this PR is ready, rebase onto main once it lands.

### Phase 1 — `ios-build-and-sign`

**Files:**
- `skills/canonical/products/<product>/ios-build-and-sign.md` — canonical (full procedure: load product config, locate cert + provisioning profile, archive build, sign, verify, emit artifact record)
- `skills/adapters/codex/ios-build-and-sign.md` — Codex adapter (fastlane invocation, cert-renewal fallback, retry policy, parsing fastlane stdout for `binary_path` + `code_sign_identity`)
- `skills/adapters/claude/ios-build-and-sign.md` — Claude adapter (status-check the artifact, validate signing identity matches expected, surface failures with concrete next-step guidance)
- `.claude/skills/ios-build-and-sign.md` — project pointer
- `skills/canonical/products/<product>/fixtures/ios-build-and-sign/happy_path.yaml` — contract-freeze fixture
- Registry entry under "iOS skills" section (next to existing iOS skills near top)
- CLAUDE.md trigger phrases: "build the iOS app", "sign the build", "archive and sign", "produce a TestFlight-ready binary"

**Contract:**
- **Inputs:** `product_id`, `build_configuration` (release|debug), `certificate_id` (optional — defaults to product config)
- **Outputs:** `binary_path`, `code_sign_identity`, `provisioning_profile`, `build_number`, `build_validated` (bool)

**Decision: which `<product>` directory?** Catchbook is the only iOS product in submission phase. Mirror the existing iOS skill placements:
- `ios-ui-polish-review` lives at `skills/canonical/products/catchbook/`
- `ios-to-appstore-handoff` lives at `skills/canonical/handoffs/` (cross-product)

`ios-build-and-sign` is a per-build operation but parameterized on `product_id`. Best home: `skills/canonical/products/catchbook/ios-build-and-sign.md` — co-located with the polish-review skill, reflects current scope (Catchbook is the only iOS product). If a second iOS product appears later, promote to `skills/canonical/shared/`. **YAGNI: don't pre-promote.**

**Estimated effort:** 0.5 day.

### Phase 2 — `approval-flow-review`

**Files:**
- `skills/canonical/shared/approval-flow-review.md` — canonical
- `skills/adapters/claude/approval-flow-review.md` — Claude adapter
- `.claude/skills/approval-flow-review.md` — project pointer
- `skills/canonical/shared/fixtures/approval-flow-review/happy_path.yaml` — fixture
- Registry entry
- CLAUDE.md trigger phrases: "review this approval request", "audit the approval flow", "is this approval well-formed", "should the founder see this"

**Contract:**
- **Inputs:** approval request envelope (`action`, `actor`, `context`, `risk_level`), policy config path (`packages/policies/approvals.py` — read-only)
- **Outputs:** `ApprovalReviewVerdict` with:
  - `verdict`: `approved | needs_clarification | escalate_to_founder`
  - `reason`: short string
  - `preconditions_missing`: list (e.g. "missing `risk_level`", "actor lane not declared")
  - `policy_rules_referenced`: list of rule ids consulted

**Decision: should this be `kind: agentic` or `kind: validator`?** Validator = pure Python, deterministic, replay-testable. Agentic = LLM-driven judgment. The audit logic ("does the request match the policy?") is mechanical for the structural part (preconditions, well-formedness) but **judgment-heavy** for the verdict bucket (`needs_clarification` vs `escalate_to_founder` requires reading context). Therefore `kind: agentic`. The structural pre-checks can ship as a Python helper later (separate plan); for now, the skill body documents both layers and Claude executes them.

**Estimated effort:** 0.5 day.

### Phase 3 — `test-coverage-audit`

**Files:**
- `skills/canonical/shared/test-coverage-audit.md` — canonical
- `skills/adapters/codex/test-coverage-audit.md` — Codex adapter (run `coverage`, `xccov`, parse output, compute lane coverage)
- `skills/adapters/claude/test-coverage-audit.md` — Claude adapter (audit diff, propose tests with file:line, surface exemption reasons)
- `.claude/skills/test-coverage-audit.md` — project pointer
- `skills/canonical/shared/fixtures/test-coverage-audit/happy_path.yaml` — fixture
- Registry entry
- CLAUDE.md trigger phrases: "audit test coverage", "check coverage policy", "do my changes meet the coverage bar", "what tests should I add"

**Contract:**
- **Inputs:** `worktree_path`, `coverage_report_path` (or trigger generation), `changed_files` (auto-detected via `git diff --name-only main...HEAD` if not supplied)
- **Outputs:** `TestCoverageVerdict` with:
  - `coverage_percent`: float (overall) plus per-lane (`python`, `ios`)
  - `policy_verdict`: `meets_policy | needs_tests | valid_exception`
  - `tests_to_add`: list of `{file, line_range, reason}` suggestions
  - `exemption_reason`: optional `NoTestReasonCode` if applicable

**Estimated effort:** 0.5 day.

### Phase 4 — Wire-up + smoke-tests

**Deliverables:**
- Single edit to `skills/registry.yaml` adding all 3 entries.
- Single edit to `CLAUDE.md` adding 3 skill bullets and 3 trigger-phrase lines.
- The 3 fixtures land at the paths above; `tests/python/unit/test_skill_contract_freeze.py` (from PR #11) picks them up automatically — bumping its `at_least_seven_skills_have_happy_path_fixtures` guard from 7 to 10.

**Acceptance:**
- `pytest tests/python/unit/test_skill_contract_freeze.py -v` shows 10 skill::case rows passing.
- `skill-stocktake` reports zero drift after the PR lands.
- All three skills appear under the right section in CLAUDE.md.

## Decision Points

### Decision 1: bump the `_at_least_seven_skills` guard

PR #11's runner has a guard `assert len(skills_with_fixtures) >= 7`. After this PR, the count rises to 10. Update the guard to 10 in the same PR — otherwise it's an underfloor that doesn't catch a future deletion.

### Decision 2: rendering Codex vs Claude differences

Two skills (ios-build-and-sign, test-coverage-audit) have BOTH Codex and Claude adapters. They serve different purposes:

- **Codex adapter:** invokes the actual tool (fastlane, coverage). Parses output. Returns structured artifact paths. Has retry logic.
- **Claude adapter:** consumes the structured artifact. Validates against policy. Surfaces failures with next-step guidance. Does not run the tool itself.

This is the pattern already established in `post-run-validation` (Codex adapter only) and `bounded-codex-implementation` (Codex only). No prior skill has both adapters with this division of labor — but the canonical body can document the contract once, and each adapter can declare its slice.

**The contract-freeze fixture asserts strings exist in the *canonical* body, not in adapters.** So the canonical must contain enough surface to capture both adapters' contracts. Keep canonicals comprehensive; adapters can be thinner pointers.

### Decision 3: stacking on PR #11 vs branching from main

This PR's contract-freeze fixtures need the runner shipped in PR #11 to be testable. Two options:
- (a) Stack on `feat/skill-completeness-pack` — fixtures testable now; rebase onto main once #11 merges.
- (b) Branch from main — fixtures land but won't run via the shared runner until #11 merges.

**Recommend (a).** Stacking matches the prior pattern (PR #11 stacked on PR #10 conceptually) and makes both PRs reviewable in parallel.

## Honored learnings (from PR #10 + PR #11 reviews)

- **No new registry keys.** Reuse `target_runtimes`, `kind`, `fixture_status` — all exist.
- **One fixture per skill** (happy_path.yaml). Boundary/adversarial added only if a real regression motivates them later.
- **No line-count metric.** Canonical bodies are sized by content, not target line counts.
- **Single-line fixture assertions** (`grep -F`-verified).
- **No module-level `re.compile`** if any helper code lands.
- **The contract-freeze pattern protects bodies, not behavior** — these skills are agentic; replay tests don't apply.

## System-Wide Impact

- `skills/registry.yaml`: +3 entries.
- `CLAUDE.md`: +3 skill bullets, +3 trigger-phrase lines.
- `tests/python/unit/test_skill_contract_freeze.py`: 7 → 10 cases (no test code change beyond the guard bump).
- `skill-stocktake` should report no drift; if it does, the new skills' wiring is incomplete.
- No `apps/`, `packages/`, `infra/` changes.
- No new dependencies.

## Acceptance Criteria

### Functional

- [x] `ios-build-and-sign` ships with canonical + Codex adapter + Claude adapter + project pointer + fixture + registry entry (stage: active) + CLAUDE.md trigger phrase.
- [x] `approval-flow-review` ships with canonical + Claude adapter + project pointer + fixture + registry entry (stage: deferred) + CLAUDE.md trigger phrase.
- [x] `test-coverage-audit` ships with canonical + Codex adapter + Claude adapter + project pointer + fixture + registry entry (stage: deferred) + CLAUDE.md trigger phrase.
- [x] All 3 fixtures pass via per-skill contract-freeze tests (consolidated into a single glob runner once PR #11's review fix lands).
- [x] PR #11's `test_skill_contract_freeze.py` consolidation isn't on this branch yet — using per-skill test files matching the existing pattern. Will deduplicate when PR #11 merges.

### Non-functional

- [ ] No new dependencies in `pyproject.toml`.
- [ ] All existing tests stay green (excluding pre-existing unrelated catchbook GTM failure).
- [ ] No `re.compile` at module scope anywhere.

## Out of scope

- Actual fastlane integration (just the contract here; implementation is a separate plan).
- New policy code in `packages/policies/`.
- Replay-test loaders for any of the three skills (all are agentic; structural fixture only).
- Any overlap with PR #10 (harness) or PR #11 (skill completeness).

## Sources & References

- `skills/WIRING.md` — wiring convention.
- `skills/canonical/shared/app-store-positioning-pack.md` — canonical body shape reference.
- `skills/canonical/shared/post-run-validation.md` — Codex-adapter-only pattern.
- `skills/canonical/handoffs/ios-to-appstore-handoff.md` — multi-runtime adapter pattern.
- `tests/python/unit/test_skill_contract_freeze.py` — runner that picks up new fixtures (from PR #11).
- `packages/policies/approvals.py` — input policy for `approval-flow-review`.
- `packages/policies/testing.py` — input policy for `test-coverage-audit`.
- Sibling plans: `2026-04-27-feat-postmortem-schema-and-adaptive-feedback-loop-plan.md` (PR #10), `2026-04-27-feat-skill-completeness-pack-plan.md` (PR #11).
