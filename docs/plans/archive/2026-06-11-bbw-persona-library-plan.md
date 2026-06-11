---
status: done
change_id: bbw-persona-library
owner: kashane
last_reviewed: 2026-06-11
---

# BBW Persona Library Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reusable Conversion Lab persona library that can audit most Better Business Web small-business categories through core buyer personas plus vertical modifiers.

**Architecture:** Keep persona content in YAML under `packages/agency/conversion_personas/`. Preserve existing `load_persona_pack(vertical)` behavior, then add `load_audience_panel(vertical)` to compose universal personas with a category modifier and any existing full vertical pack. Update the operator CLI to use the composed panel by default.

**Tech Stack:** Python 3.12, YAML, dataclasses, pytest, existing `packages/agency/conversion_personas` loader and `scripts/agency/run_conversion_lab.py`.

---

### Task 1: Add Audience Panel Tests

**Files:**
- Modify: `tests/python/unit/test_agency_conversion_personas.py`

**Step 1: Write failing tests**

Add tests that assert:

```python
panel = load_audience_panel("plumber")
assert panel.vertical == "plumber"
assert panel.modifier.modifier_id == "home_services"
assert len(panel.personas) >= 12
assert any(p.persona_id == "urgent-problem-solver" for p in panel.personas)
```

Also test aliases:

```python
assert load_audience_panel("barber_shop").modifier.modifier_id == "personal_care"
assert load_audience_panel("dentist").modifier.modifier_id == "health_wellness"
assert load_audience_panel("auto_repair").modifier.modifier_id == "auto_services"
```

**Step 2: Run red**

Run:

```bash
python -m pytest tests/python/unit/test_agency_conversion_personas.py -q
```

Expected: FAIL because `load_audience_panel` does not exist.

### Task 2: Implement Core Personas And Modifiers

**Files:**
- Modify: `packages/agency/conversion_personas/__init__.py`
- Create: `packages/agency/conversion_personas/core.yaml`
- Create: `packages/agency/conversion_personas/modifiers.yaml`
- Test: `tests/python/unit/test_agency_conversion_personas.py`

**Step 1: Add dataclasses**

Add:

```python
@dataclass(frozen=True)
class VerticalModifier:
    modifier_id: str
    verticals: list[str]
    objections: list[str]
    trust_signals: list[str]
    decision_triggers: list[str]
    compliance_notes: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class AudiencePanel:
    vertical: str
    modifier: VerticalModifier
    personas: list[ConversionPersona]
```

**Step 2: Add YAML files**

Create `core.yaml` with at least 12 core personas.

Create `modifiers.yaml` with at least 10 modifiers:

- `home_services`
- `personal_care`
- `health_wellness`
- `professional_services`
- `food_hospitality`
- `auto_services`
- `retail`
- `classes_activities`
- `real_estate_property`
- `pet_services`

**Step 3: Add loader**

Add `load_audience_panel(vertical, *, root=None)`:

- load `core.yaml`
- resolve the modifier by exact vertical or alias
- append existing full vertical pack personas if `<vertical>.yaml` exists
- validate duplicate persona IDs
- return `AudiencePanel`

**Step 4: Run green**

Run:

```bash
python -m pytest tests/python/unit/test_agency_conversion_personas.py -q
```

Expected: PASS.

### Task 3: Update Prompt Preparation To Use Audience Panels

**Files:**
- Modify: `scripts/agency/run_conversion_lab.py`
- Test: `tests/python/unit/test_agency_conversion_lab_cli.py`

**Step 1: Write failing CLI test**

Add a test that prepares `--vertical plumber` and asserts `PROMPTS.md` contains
core persona content and home-services modifier content.

**Step 2: Run red**

Run:

```bash
python -m pytest tests/python/unit/test_agency_conversion_lab_cli.py -q
```

Expected: FAIL because the CLI still loads only full vertical packs.

**Step 3: Update CLI**

Change `run_conversion_lab.py prepare` to call `load_audience_panel(args.vertical)`
and build prompts from `panel.personas`.

**Step 4: Run green**

Run:

```bash
python -m pytest tests/python/unit/test_agency_conversion_lab_cli.py -q
```

Expected: PASS.

### Task 4: Document The Library

**Files:**
- Modify: `docs/agency/conversion-lab.md`
- Create: `docs/agency/conversion-lab/persona-library.md`
- Modify: `docs/agency/INDEX.md`

**Step 1: Add docs**

Document the two-layer model, the supported modifiers, and how to add a new
modifier or full vertical pack.

**Step 2: Regenerate index**

Run:

```bash
python3 scripts/docs/gen_doc_index.py docs/agency
```

**Step 3: Verify docs**

Run:

```bash
./scripts/ci/check_doc_paths.sh
```

Expected: PASS.

### Task 5: Final Verification

Run:

```bash
python -m pytest \
  tests/python/unit/test_agency_conversion_personas.py \
  tests/python/unit/test_agency_conversion_lab.py \
  tests/python/unit/test_agency_conversion_lab_cli.py \
  tests/python/unit/test_conversion_lab_schema.py \
  -q
```

Run:

```bash
make plans-index-check
./scripts/ci/check_doc_paths.sh
```

Expected: PASS.

Commit:

```bash
git add packages/agency/conversion_personas scripts/agency/run_conversion_lab.py tests/python/unit/test_agency_conversion_personas.py tests/python/unit/test_agency_conversion_lab_cli.py docs/agency docs/plans
git commit -m "feat: expand conversion lab persona library"
```
