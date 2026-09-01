# HomeFromWorking Commerce Spine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build one safe, offline HomeFromWorking run from research through a publication-ready Etsy/Printify proposal with four founder approval gates and persistent lineage.

**Architecture:** Add provider-neutral commerce schemas and workflow code under `packages/commerce`, compose the existing discovery and approval records, and keep HomeFromWorking policy/config under `businesses/home-from-working`. Persist aggregate run records atomically under `state/`; external research, design, fulfillment, and marketplace calls remain typed adapters with deterministic fixture implementations.

**Tech Stack:** Python 3.12, frozen dataclasses, `str` enums, PyYAML, existing `JsonStore`/`ApprovalStore`, pytest, Ruff.

---

### Task 1: Business config and typed commerce artifacts

**Files:**
- Create: `businesses/home-from-working/README.md`
- Create: `businesses/home-from-working/config/business.yaml`
- Create: `packages/commerce/__init__.py`
- Create: `packages/commerce/config.py`
- Create: `packages/schemas/commerce.py`
- Test: `tests/python/unit/test_commerce_schemas.py`

**Step 1: Write the failing tests**

Cover:

```python
def test_home_from_working_config_keeps_product_scope_open() -> None:
    config = load_business_config()
    assert config.business_id == "home-from-working"
    assert config.allowed_product_types == []
    assert all(gate.mode is ApprovalMode.REQUIRED for gate in config.gates.values())


def test_commerce_run_round_trip_preserves_open_product_and_design_formats() -> None:
    run = sample_run(product_format="desk mat", design_format="technical diagram")
    assert CommerceRunRecord.from_dict(run.to_dict()) == run
```

Also assert evidence classification, direct parent ids, and the complete artifact-chain fields
survive `to_dict`/`from_dict`.

**Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/python/unit/test_commerce_schemas.py -q`

Expected: FAIL during collection because `packages.schemas.commerce` and
`packages.commerce.config` do not exist.

**Step 3: Implement the minimal schemas and loader**

Define frozen records and enums with explicit serialization:

```python
class EvidenceClassification(str, Enum):
    FACT = "fact"
    OBSERVATION = "observation"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"


class CommerceStage(str, Enum):
    RESEARCHED = "researched"
    AWAITING_OPPORTUNITY_APPROVAL = "awaiting_opportunity_approval"
    CONCEPTS_READY = "concepts_ready"
    AWAITING_CONCEPT_APPROVAL = "awaiting_concept_approval"
    DESIGN_READY = "design_ready"
    AWAITING_ARTWORK_APPROVAL = "awaiting_artwork_approval"
    DRAFTS_READY = "drafts_ready"
    AWAITING_PUBLICATION_APPROVAL = "awaiting_publication_approval"
    PUBLICATION_READY = "publication_ready"


@dataclass(frozen=True)
class CommerceRunRecord:
    id: str
    business_id: str
    opportunity: CommerceOpportunity
    stage: CommerceStage
    concepts: list[CreativeConcept] = field(default_factory=list)
    selected_concept_id: str = ""
    design: DesignArtifact | None = None
    product: ProductDraft | None = None
    listing: ListingDraft | None = None
    publication: PublicationPackage | None = None
    approval_ids: dict[str, str] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
```

The config loader validates business id, marketplace/provider identifiers, trust levels 0–5, all
four gates, and open product scope. `allowed_product_types: []` means unrestricted, not “none.”

**Step 4: Run tests and lint**

Run: `python3 -m pytest tests/python/unit/test_commerce_schemas.py -q`

Expected: PASS.

Run: `python3 -m ruff check packages/commerce packages/schemas/commerce.py tests/python/unit/test_commerce_schemas.py`

Expected: PASS.

**Step 5: Commit**

```bash
git add businesses/home-from-working packages/commerce packages/schemas/commerce.py tests/python/unit/test_commerce_schemas.py
git commit -m "feat(commerce): add HomeFromWorking artifact contracts"
```

### Task 2: Capability trust and four founder gates

**Files:**
- Create: `packages/policies/commerce_gates.py`
- Modify: `packages/policies/approvals.py`
- Test: `tests/python/unit/test_commerce_gates.py`
- Modify: `tests/python/unit/test_policy_violation_codes.py`

**Step 1: Write the failing tests**

Cover pending, rejected, approved, wrong action, wrong subject, optional mode, and auto-within-policy:

```python
def test_required_gate_accepts_only_matching_approved_record() -> None:
    approval = approval_record(status=ApprovalStatus.APPROVED)
    assert_gate_open(GateType.CONCEPT, "concept_1", required_policy(), approval=approval)


def test_auto_mode_falls_back_to_human_when_outside_policy() -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_gate_open(
            GateType.PUBLICATION,
            "package_1",
            auto_policy(),
            approval=None,
            within_policy=False,
        )
    assert exc.value.code == "commerce_publication_not_approved"
```

**Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/python/unit/test_commerce_gates.py tests/python/unit/test_policy_violation_codes.py -q`

Expected: FAIL because the gate module and canonical codes do not exist.

**Step 3: Implement the policy**

Add four canonical codes and a fail-closed gate:

```python
GATE_ACTIONS = {
    GateType.OPPORTUNITY: "commerce_opportunity_selection",
    GateType.CONCEPT: "commerce_concept_selection",
    GateType.ARTWORK: "commerce_artwork_selection",
    GateType.PUBLICATION: "commerce_publication",
}


def assert_gate_open(
    gate: GateType,
    subject_id: str,
    policy: GatePolicy,
    *,
    approval: ApprovalRecord | None,
    within_policy: bool = False,
) -> None:
    if policy.mode is ApprovalMode.OPTIONAL:
        return
    if policy.mode is ApprovalMode.AUTO_APPROVE_WITHIN_POLICY and within_policy:
        return
    if not _matching_approval(gate, subject_id, approval):
        raise PolicyViolation(GATE_CODES[gate], detail=f"{gate.value} requires founder approval")
```

**Step 4: Run tests and lint**

Run: `python3 -m pytest tests/python/unit/test_commerce_gates.py tests/python/unit/test_policy_violation_codes.py -q`

Expected: PASS.

Run: `python3 -m ruff check packages/policies/commerce_gates.py packages/policies/approvals.py tests/python/unit/test_commerce_gates.py`

Expected: PASS.

**Step 5: Commit**

```bash
git add packages/policies/commerce_gates.py packages/policies/approvals.py tests/python/unit/test_commerce_gates.py tests/python/unit/test_policy_violation_codes.py
git commit -m "feat(commerce): enforce capability-specific founder gates"
```

### Task 3: Atomic run storage and reverse lineage

**Files:**
- Create: `packages/commerce/storage.py`
- Modify: `packages/config/settings.py`
- Test: `tests/python/unit/test_commerce_storage.py`
- Modify: `tests/python/unit/test_settings_and_stores.py`

**Step 1: Write the failing tests**

```python
def test_repository_round_trips_run_and_answers_reverse_lineage(tmp_path: Path) -> None:
    repository = JsonCommerceRunRepository(tmp_path)
    repository.save(complete_run())
    assert repository.get("run_1") == complete_run()
    assert repository.lineage("run_1", "publication_1") == [
        "observation_1", "opportunity_1", "concept_1", "design_1",
        "product_1", "listing_1", "publication_1",
    ]
```

Also assert missing ids fail explicitly and the runtime directory is created by
`ensure_runtime_directories`.

**Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/python/unit/test_commerce_storage.py tests/python/unit/test_settings_and_stores.py -q`

Expected: FAIL because the repository and commerce runtime path do not exist.

**Step 3: Implement the repository**

Wrap existing `JsonStore`; default root is
`state/checkpoints/businesses/<business-id>/commerce-runs`. Build a parent map from typed records
and traverse one direct-parent chain with cycle detection. Do not write runtime data beneath the
business source directory.

**Step 4: Run tests and lint**

Run: `python3 -m pytest tests/python/unit/test_commerce_storage.py tests/python/unit/test_settings_and_stores.py -q`

Expected: PASS.

Run: `python3 -m ruff check packages/commerce/storage.py packages/config/settings.py tests/python/unit/test_commerce_storage.py`

Expected: PASS.

**Step 5: Commit**

```bash
git add packages/commerce/storage.py packages/config/settings.py tests/python/unit/test_commerce_storage.py tests/python/unit/test_settings_and_stores.py
git commit -m "feat(commerce): persist runs with reverse lineage"
```

### Task 4: Typed adapters and deterministic first product fixture

**Files:**
- Create: `packages/commerce/adapters.py`
- Create: `packages/commerce/demo_adapters.py`
- Test: `tests/python/unit/test_commerce_adapters.py`

**Step 1: Write the failing tests**

Verify the research fixture emits classified, cited evidence and zooms in/out/sideways; concepts
are distinct and research-grounded; the design fixture writes a real local asset with explicit
production metadata; the draft adapter emits provider-neutral product data plus Etsy listing
metadata without an external call.

**Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/python/unit/test_commerce_adapters.py -q`

Expected: FAIL because adapter protocols and fixtures do not exist.

**Step 3: Implement protocols and fixture adapters**

```python
class ResearchAdapter(Protocol):
    def enrich(self, opportunity: OpportunityRecord) -> CommerceOpportunity: ...

class ConceptAdapter(Protocol):
    def propose(self, opportunity: CommerceOpportunity) -> list[CreativeConcept]: ...

class DesignAdapter(Protocol):
    def generate(self, concept: CreativeConcept, *, output_dir: Path) -> DesignArtifact: ...

class DraftAdapter(Protocol):
    def prepare(
        self, opportunity: CommerceOpportunity, design: DesignArtifact
    ) -> tuple[ProductDraft, ListingDraft]: ...
```

Fixture data may use an aviation-maintenance profession seed, but no code path restricts future
runs to that niche, apparel, or a design style.

**Step 4: Run tests and lint**

Run: `python3 -m pytest tests/python/unit/test_commerce_adapters.py -q`

Expected: PASS.

Run: `python3 -m ruff check packages/commerce/adapters.py packages/commerce/demo_adapters.py tests/python/unit/test_commerce_adapters.py`

Expected: PASS.

**Step 5: Commit**

```bash
git add packages/commerce/adapters.py packages/commerce/demo_adapters.py tests/python/unit/test_commerce_adapters.py
git commit -m "feat(commerce): add replaceable offline adapters"
```

### Task 5: Approval-gated commerce workflow

**Files:**
- Create: `packages/commerce/workflow.py`
- Test: `tests/python/unit/test_commerce_workflow.py`

**Step 1: Write the failing tests**

Test each transition independently, including no creation before opportunity approval, no design
before concept approval, no drafts before artwork approval, and no publication-ready package
before publication approval. Assert pending approvals use the existing `ApprovalRecord` contract
and mismatched approvals cannot be replayed across artifacts.

**Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/python/unit/test_commerce_workflow.py -q`

Expected: FAIL because the workflow does not exist.

**Step 3: Implement the state machine**

Expose narrowly scoped methods:

```python
start(opportunity: OpportunityRecord) -> CommerceRunRecord
request_opportunity_approval(run_id: str) -> ApprovalRecord
generate_concepts(run_id: str) -> CommerceRunRecord
request_concept_approval(run_id: str, concept_id: str) -> ApprovalRecord
generate_design(run_id: str) -> CommerceRunRecord
request_artwork_approval(run_id: str) -> ApprovalRecord
prepare_drafts(run_id: str) -> CommerceRunRecord
request_publication_approval(run_id: str) -> ApprovalRecord
finalize_publication_package(run_id: str) -> CommerceRunRecord
```

Every mutating method loads the last persisted run, checks the exact stage and approval, performs
one adapter call, then saves. Approval requests are idempotent for the same gate and subject.

**Step 4: Run tests and lint**

Run: `python3 -m pytest tests/python/unit/test_commerce_workflow.py -q`

Expected: PASS.

Run: `python3 -m ruff check packages/commerce/workflow.py tests/python/unit/test_commerce_workflow.py`

Expected: PASS.

**Step 5: Commit**

```bash
git add packages/commerce/workflow.py tests/python/unit/test_commerce_workflow.py
git commit -m "feat(commerce): add approval-gated commerce workflow"
```

### Task 6: Safe operator demo and architecture documentation

**Files:**
- Create: `scripts/home_from_working_demo.py`
- Test: `tests/python/unit/test_home_from_working_demo.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/agent-model.md`
- Modify: `docs/architecture.md`
- Create: `docs/founder/home-from-working-guide.md`
- Modify: `docs/founder/INDEX.md`

**Step 1: Write the failing demo tests**

Assert the default demo stops at a pending opportunity approval and the explicit
`--approve-all --founder <name>` path completes only an internal publication-ready package with
all four distinct approved records and full reverse lineage. Assert no Etsy/Printify HTTP client
or credentials are referenced.

**Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/python/unit/test_home_from_working_demo.py -q`

Expected: FAIL because the script does not exist.

**Step 3: Implement the demo and docs**

The CLI prints run id, current stage, pending approval id, artifact paths, and the exact statement
“No external product was created or published.” Document:

```bash
python3 scripts/home_from_working_demo.py
python3 scripts/home_from_working_demo.py --approve-all --founder kashane
```

Update all four architecture documents because introducing a first-class `businesses/` boundary
is material. State that business source/config lives under `businesses/`, runtime business state
remains under `state/`, and commerce does not bypass discovery or approval policy.

**Step 4: Run focused and full verification**

Run: `python3 -m pytest tests/python/unit/test_commerce_*.py tests/python/unit/test_home_from_working_demo.py -q`

Expected: PASS.

Run: `python3 scripts/home_from_working_demo.py --approve-all --founder test-founder --state-root /tmp/home-from-working-demo`

Expected: exits 0 at `publication_ready`, prints four approval ids and the no-publication safety statement.

Run: `python3 -m ruff check packages/commerce packages/schemas/commerce.py packages/policies/commerce_gates.py scripts/home_from_working_demo.py tests/python/unit/test_commerce_*.py tests/python/unit/test_home_from_working_demo.py`

Expected: PASS.

Run: `./scripts/test_python.sh`

Expected: PASS with the repository coverage threshold met.

**Step 5: Commit**

```bash
git add scripts/home_from_working_demo.py tests/python/unit/test_home_from_working_demo.py README.md AGENTS.md docs/agent-model.md docs/architecture.md docs/founder/home-from-working-guide.md docs/founder/INDEX.md
git commit -m "feat: add HomeFromWorking commerce vertical slice"
```

### Task 7: Final diff and safety audit

**Files:**
- Review only; modify only if verification exposes an issue.

**Step 1: Inspect scope**

Run: `git status --short`

Expected: pre-existing `.claude/launch.json` and `products/pokemon-tcg-search/` changes remain
untouched; HomeFromWorking work is committed.

Run: `git diff 9469043..HEAD --stat && git diff 9469043..HEAD --check`

Expected: only planned commerce/business/docs/test files; no whitespace errors.

**Step 2: Re-run critical policy tests**

Run: `python3 -m pytest tests/python/unit/test_commerce_gates.py tests/python/unit/test_commerce_workflow.py tests/python/unit/test_policy_violation_codes.py -q`

Expected: PASS.

**Step 3: Confirm no external execution surface**

Run: `rg -n "requests\.|httpx\.|etsy|printify" packages/commerce scripts/home_from_working_demo.py`

Expected: Etsy/Printify appear only as provider identifiers or copy; no HTTP execution call exists.

**Step 4: Record completion**

Update the session plan and report the committed design, implementation commits, verification
commands, and the intentionally deferred live integrations.
