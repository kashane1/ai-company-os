---
title: "ECC gap recommendations: porting upstream patterns as canonical skills with primitives convention compliance"
date: 2026-04-15
category: architecture
severity: high
components:
  - skills/canonical/
  - skills/adapters/claude/
  - skills/registry.yaml
  - packages/tools/primitives/
  - packages/tools/skills/loader.py
  - packages/policies/
  - CLAUDE.md
tags:
  - ecc-gap-analysis
  - canonical-skills
  - primitives
  - regex-lazy-factory
  - dependency-inversion
  - verification-loop
  - skill-stocktake
  - context-budget
  - research-first-execution
  - atomic-rollout
  - convention-compliance
related_plans:
  - docs/plans/2026-04-15-feat-ecc-gap-recommendations-plan.md
  - docs/2026-04-14-everything-claude-code-gap-analysis.md
  - docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md
---

# Multi-phase plan shipping: primitives and skills convention compliance

## Problem

The ECC Gap Recommendations plan required shipping 6 new canonical skills, 10 new primitives, and 1 new policy wrapper across 5 sequential commits (Phases 0–4). The codebase has strict convention enforcement — AST-based tests forbidding module-level `re.compile()` and certain top-level imports, layered dependency rules between subpackages, and fixture-based contract tests that assert exact substring matches against canonical markdown. These constraints created seven distinct integration challenges that would silently break CI or runtime behavior if not addressed.

## Root Cause

Each challenge arose from the intersection of a correct architectural constraint with an idiomatic Python pattern that violates it:

- The primitives convention test (`test_primitives_conventions.py`) is AST-based and rejects any `ast.Call` at module scope that isn't in a small allowlist. Standard `re.compile()` is a `Call` to `compile()` — rejected.
- The primitives ADR says "no imports from `packages/tools/skills/`" — a helper needed by both layers has to live in primitives, not skills.
- Structural fixture tests use Python `in` substring matching, which doesn't span `\n` boundaries — a phrase split by word-wrap fails silently.
- Multiple skills touching the same source files (CLAUDE.md, approvals.py) can't ship as serialized PRs without merge conflicts.

## Solution

### 1. Regex convention compliance — lazy `lru_cache` factories

Replace module-level `re.compile()` with `@functools.lru_cache(maxsize=1)` factory functions. The convention test allowlists `lru_cache` as a module-level call. The pattern string lives at module level (stateless); the compiled form is lazily built on first call and cached for the process lifetime.

```python
ADAPTER_PATH_PATTERN_STR = r"^adapters/[a-z][a-z0-9_]*/[a-z0-9][a-z0-9_-]*\.md$"

@functools.lru_cache(maxsize=1)
def adapter_path_pattern() -> re.Pattern[str]:
    return re.compile(ADAPTER_PATH_PATTERN_STR)
```

Same pattern used for `_trigger_target_re()` in `registry_drift.py` and `_sensitive_field_re()` in `verification_loop_runner.py`.

### 2. Dependency inversion for shared path-safety helper

Lifted `_ADAPTER_PATH_PATTERN` from `packages/tools/skills/loader.py:42` into `packages/tools/primitives/_safe_paths.py` as the authoritative home. Refactored `loader.py` to import FROM primitives (inverting the dependency). All existing loader tests pass unchanged because the compiled regex is byte-identical.

### 3. Fixture string assertions vs line-wrapped markdown

Ensured load-bearing assertion strings appear on a single line in canonical markdown. For example, `"ask the operator which skill to invoke"` must not be word-wrapped as `"ask the operator which skill to\ninvoke"` because `in` substring matching sees the newline.

### 4. Atomic multi-component commits

Shipped co-dependent components touching shared files (CLAUDE.md trigger phrases, `approvals.py` enum) as single atomic commits, following the precedent from `docs/solutions/integration-issues/catchbook-navigation-revamp-rollout.md`.

### 5. Lazy subprocess import in primitives

Moved `import subprocess` inside function bodies to avoid the `FORBIDDEN_TOP_LEVEL_IMPORTS` AST check. Same pattern as tiktoken's lazy import in `context_budget.py`.

```python
def _git_diff_name_only(since_ref: str) -> list[str]:
    import subprocess  # lazy — primitives convention
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{since_ref}...HEAD"],
        capture_output=True, text=True, timeout=10,
        cwd=str(_repo_root()), check=False,
    )
    return [l.strip() for l in result.stdout.splitlines() if l.strip()]
```

### 6. Serialization safety for dataclass returns

Created `packages/tools/primitives/_serialization.py` with a `json_safe_factory()` dict_factory that coerces `Path` to `str`, `Enum` to `.value`, `datetime` to `.isoformat()`. Every validator's return path uses `asdict(report, dict_factory=json_safe_factory)`.

### 7. State directory bootstrapping

`_state_writer.atomic_write_json()` calls `path.parent.mkdir(parents=True, exist_ok=True)` before the atomic temp-file + `os.replace` write and injects `schema_version: "1"` into every payload.

## Prevention Strategies

### PS-1: Skeleton-first primitive development

Before writing any module under `packages/tools/primitives/`, run `pytest tests/python/unit/test_primitives_conventions.py -x` against a skeleton file containing only the docstring and function signatures. This surfaces AST rules before any real logic is written. Every primitive PR must include a checkbox: "Confirmed: no module-level I/O, `re.compile`, or `subprocess`."

### PS-2: Grep-before-assert for markdown fixtures

Before writing any substring assertion against a markdown file, `grep -F` the exact assertion string against the target file. If grep returns nothing, the string spans a line break. Codify this as a comment convention at the top of every fixture test file. Consider a helper `assert_single_line_match(path, phrase)`.

### PS-3: Touchpoint inventory at plan time

Every multi-skill plan should include a "Shared touchpoints" table: columns are files, rows are skills, cells are "read" or "write". Any file with two or more "write" cells must be handled atomically. This table takes five minutes and prevents hours of conflict resolution.

### PS-4: One-way dependency arrow

The dependency graph is `primitives <- skills <- apps`. Never draw an arrow upward. When tempted to import from a higher layer, move the needed code down. Add a regex check in CI: no file under `packages/tools/primitives/` may contain `from packages.tools.skills` or `import packages.tools.skills`.

### PS-5: State writes go through the helper

Treat `atomic_write_json()` as the only blessed write path for `state/`. Direct `open()` calls to state directories are a code smell. Extend the helper rather than bypass it.

### PS-6: Validator return shape — the verdict-dict contract

Every validator must return `{"verdict": "pass"|"fail", ...}` at the top level, with internal typed dataclasses serialized via `asdict(..., dict_factory=json_safe_factory)`. The `test_primitive_contracts_pinned.py` test enforces field stability.

### PS-7: Drift is a follow-up, never a side-fix

When a structural audit surfaces pre-existing drift, tag it as `known_drift`, file a follow-up, and ship separately. Mixing drift repair with feature work produces PRs that are hard to review, revert, and attribute.

## Related Documentation

### Source documents
- [ECC Gap Recommendations plan](../plans/2026-04-15-feat-ecc-gap-recommendations-plan.md) — the 4-phase plan this documents
- [Everything-Claude-Code gap analysis](../2026-04-14-everything-claude-code-gap-analysis.md) — the gap analysis driving this plan
- [Hermes-Inspired Platform Upgrade plan](../plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md) — provides PolicyViolationCode, self_evolvable, per-skill-directory layout, primitives ADR

### ADRs
- [Canonical skill layout ADR](../adr/2026-04-14-canonical-skill-layout.md) — directory-preferred layout
- [Primitives subpackage ADR](../adr/2026-04-14-primitives-subpackage.md) — convention for stateless typed helpers
- [ECC skill decisions ADR](../adr/2026-04-15-ecc-skill-decisions.md) — install-surface deferral + kind/layout defaults

### Related learnings
- [Pre-existing failures are often test bugs](test-failures/pre-existing-failures-are-often-test-bugs.md)
- [Bare main import pollutes sys.modules](test-failures/bare-main-import-pollutes-sys-modules.md)
- [Catchbook navigation revamp rollout](integration-issues/catchbook-navigation-revamp-rollout.md) — atomic multi-component commit precedent
- [Skill-evolution revert dry-run](integration-issues/skill-evolution-revert-dryrun-2026-04-15.md) — Phase 3 rollback patterns
- [Plan-deepening apply-verify loop](integration-issues/plan-deepening-apply-verify-loop-2026-04-15.md) — the workflow that executed this plan
