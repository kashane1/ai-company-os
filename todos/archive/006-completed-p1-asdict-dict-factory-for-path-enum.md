---
status: completed
priority: p1
issue_id: "006"
tags: [code-review, python, serialization, ecc-gap-plan]
dependencies: []
---

# Problem Statement

The ECC gap plan commits to `dataclasses.asdict()` for serializing `StocktakeReport` / `ContextBudgetReport` / `VerificationLoopReport` at the validator boundary. But `asdict()` does not coerce `pathlib.Path`, `datetime`, or `Enum` fields — they pass through as-is and then fail on JSON serialization downstream. The plan's `contract.yaml` stores `registry_path: Path | None`, and drift items will likely carry Path fields. Without a `dict_factory`, the first real run will crash on `TypeError: Object of type PosixPath is not JSON serializable`.

## Findings

- Kieran python review second pass finding #1: "`asdict()` does *not* handle `pathlib.Path`, `datetime`, or `Enum` — they pass through as-is and then fail JSON serialization downstream. The plan doesn't mention this. **Add it.**"
- Plan commits to `@dataclass(frozen=True)` internals with `dataclasses.asdict()` at the boundary in Phase 2 + Phase 3 deepening findings.
- `DriftItem` likely carries `fixture_path: Path | None` per the existing [reconciliation.py](/Users/simons/ai-company-os/packages/tools/skills/reconciliation.py:44) `DriftItem` which already has this problem.

## Proposed Solutions

### Option 1: `dict_factory` coercion in every validator

```python
def _json_safe_factory(pairs):
    out = {}
    for k, v in pairs:
        if isinstance(v, Path):
            out[k] = str(v)
        elif isinstance(v, (datetime, Enum)):
            out[k] = v.value if isinstance(v, Enum) else v.isoformat()
        else:
            out[k] = v
    return out

report_dict = asdict(report, dict_factory=_json_safe_factory)
```

Pros:
- One helper in `packages/tools/primitives/_serialization.py` reused by all three reports
- Handles the entire Path/Enum/datetime axis once
- Kieran's recommended idiom

Cons:
- New shared helper

Effort: trivial
Risk: low

### Option 2: Stringify in `__post_init__`

Declare `fixture_path: str` not `Path` and stringify at construction time.

Pros:
- No serialization helper
- Fields are JSON-safe by construction

Cons:
- Loses type safety on the internal representation
- Callers have to re-parse to use as Path
- Fights against Kieran's first-pass "Path everywhere at boundaries" rule

Effort: trivial
Risk: medium (type erosion)

## Recommended Action

Option 1. Add `packages/tools/primitives/_serialization.py` with `json_safe_factory(pairs)` as a Phase 2a deliverable. Every validator's return path uses it via `dataclasses.asdict(report, dict_factory=json_safe_factory)`.

## Technical Details

- New module: `packages/tools/primitives/_serialization.py`
- Consumers: Phase 2a `skill-stocktake/validator.py`, Phase 2b `context-budget/validator.py`, Phase 3 `verification-loop` (if it serializes a report).
- Test: unit test asserts `asdict` with the factory on a synthetic report containing Path + datetime + Enum round-trips through `json.dumps(...)`.

## Acceptance Criteria

- [ ] `packages/tools/primitives/_serialization.py` exists with `json_safe_factory`
- [ ] All three new validators use it at the return boundary
- [ ] Unit test: `json.dumps(asdict(synthetic_report, dict_factory=json_safe_factory))` succeeds on a report with Path, datetime, and Enum fields
- [ ] Plan document updated to cite this helper in Phase 2+3 DoD

## Work Log

### 2026-04-15 - Captured during technical review
**By:** Claude (review workflow)
**Actions:** Kieran's second-pass review caught this gap — the plan commits to `asdict()` but doesn't handle Path/Enum/datetime.
