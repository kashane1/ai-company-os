---
status: pending
priority: p2
issue_id: "054"
tags: [code-review, skills, polish_prompt, schema, dead-code]
dependencies: []
---

# Problem Statement

`packages/schemas/polish_prompt.py` is Python-shaped policy that no Python code consumes. The `PolishPrompt` dataclass and `to_markdown()` method are dead code. `POLISH_PROMPT_FIELDS` is referenced only as a literal path string in fixtures, never imported or asserted against. The module's docstring overclaims: it says producer fixtures "assert that the canonical body lists every field in `POLISH_PROMPT_FIELDS`" — they do not.

This is the "worst of both worlds" state both reviewers flagged: enough Python to look load-bearing, not enough behaviour to actually enforce the contract.

## Findings

- **architecture-strategist:** "Nothing mechanical imports or asserts against the tuple... if a producer canonical body drops the `Iteration cap` field, the fixture still passes unless the fixture is *also* edited. If `POLISH_PROMPT_FIELDS` is reordered or renamed, no test fails. The schema is currently documentation in Python clothing."
- **code-simplicity-reviewer:** "`PolishPrompt` and `to_markdown()` are not consumed anywhere (grep confirms — only `observability/rollup.py` has its own `to_markdown`). No runtime parser exists. CUT the dataclass and `to_markdown()` entirely (lines 51–87, 37 LOC)."

Both reviewers converged from opposite directions on the same conclusion.

## Proposed Solutions

### Option 1: Cut dead code + add mechanical assertion (recommended)

1. Delete `PolishPrompt` dataclass and `to_markdown()` method from `packages/schemas/polish_prompt.py` (lines 51-87, ~37 LOC).
2. Keep `POLISH_PROMPT_FIELDS` and `POLISH_PROMPT_MODES` tuples.
3. Update the module docstring to accurately describe what it is (a name-list for fixture cross-reference) and what it is not (a runtime parser).
4. Add a new test `tests/python/unit/test_polish_prompt_schema.py` that:
   - Imports `POLISH_PROMPT_FIELDS`
   - Reads `skills/canonical/shared/recon-scaffolding.md`
   - Asserts every field name appears verbatim in the markdown (`f"**{field}:**"` substring)
   - Asserts `simulator-driven-polish/skill.md` cites `packages/schemas/polish_prompt.py`
5. This is the minimum wiring that gives the tuple actual contract-enforcing power.

Pros: cuts confirmed dead code; makes the schema mechanical; future renames or reorders break the test
Cons: requires a new test file
Effort: Small
Risk: Low

### Option 2: Cut dead code only; leave POLISH_PROMPT_FIELDS as documentation

Same as Option 1 but skip the new test. Accept that the tuple is documentation that lives in `.py` rather than `.md`.

Pros: simplest change
Cons: doesn't fix the architecture concern that nothing mechanical fails on drift
Effort: Trivial
Risk: Low

### Option 3: Wire fully — add a runtime parser and chain integration

Add a `PolishPromptParser` that reads a backlog file and validates each emitted prompt block against `POLISH_PROMPT_FIELDS`. Then the producer-consumer contract has a runtime check, not just a static one.

Pros: full mechanical enforcement
Cons: scope creep; no consumer currently parses prompts at runtime (LLM consumes them); premature parser
Effort: Medium
Risk: Low

## Recommended Action

**Option 1.** Cuts the dead code both reviewers identified, and adds the minimum mechanical assertion that closes the architecture concern. Option 3 is the eventual end-state but is YAGNI today.

## Technical Details

- Files affected:
  - `packages/schemas/polish_prompt.py` (cut lines 51-87, update docstring)
  - `tests/python/unit/test_polish_prompt_schema.py` (new)
- The new test must run as part of `./scripts/test_python.sh` (it will be discovered by pytest automatically because of the `test_*.py` name).

## Acceptance Criteria

- [ ] `PolishPrompt` dataclass removed from `packages/schemas/polish_prompt.py`
- [ ] `to_markdown()` method removed
- [ ] Module docstring updated to accurately describe scope
- [ ] `POLISH_PROMPT_FIELDS` and `POLISH_PROMPT_MODES` tuples retained
- [ ] New `tests/python/unit/test_polish_prompt_schema.py` asserts:
  - Every `POLISH_PROMPT_FIELDS` entry appears in `recon-scaffolding.md`
  - `simulator-driven-polish/skill.md` cites the schema module
- [ ] All existing tests still pass
- [ ] No new file imports `PolishPrompt` (verified by grep returning nothing)

## Work Log

(empty)
