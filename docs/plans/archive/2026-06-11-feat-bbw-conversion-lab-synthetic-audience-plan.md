---
status: done
change_id: feat-bbw-conversion-lab-synthetic-audience
owner: kashane
last_reviewed: 2026-06-11
---

# BBW Conversion Lab Synthetic Audience Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Better Business Web "Conversion Lab" product line that uses synthetic customer panels to audit, rewrite, and prioritize website, landing page, and ad copy before client spend or rebuild work.

**Architecture:** Start as a manual, operator-delivered agency service, then encode the winning workflow into typed schemas, service catalog entries, artifacts, and guarded agency CLIs. Keep synthetic audience output as exploratory conversion intelligence, not an automated promise that a variant will produce revenue.

**Tech Stack:** Python 3.12, dataclass schemas under `packages/schemas/`, agency modules under `packages/agency/`, docs under `docs/agency/`, state artifacts under `state/clients/`, pytest under `tests/python/unit/`.

---

## Product Verdict

This should become a Better Business Web offer, but not a standalone SaaS first.

Sell it as **Conversion Lab**, not "AI focus groups." The wedge is:

> "Before we rebuild or advertise, we pressure-test the page through the likely buyer objections, trust gaps, and conversion blockers for your vertical."

The useful product is the audit and rewrite package. The synthetic panel is the internal method. It should attach to demo-site outreach, Package B booking/conversion readiness, Package C ad and promo-page preflight, and existing-site inbound as a paid audit before a rebuild.

Best first verticals:

- med spas
- dentists
- roofing
- HVAC
- plaintiff or local law firms

Do **not** start with broad local SMB coverage. Persona quality is the asset, and generic panels will make the service feel like commodity AI.

## Research Notes

The research supports this as a rapid preflight and qualitative simulation layer, with caveats:

- Stanford HAI summarized work where interview-backed agents simulated 1,052 people and matched participants on General Social Survey answers at 85% of human test-retest consistency, with lower performance on other task types. This argues for rich, evidence-backed personas over thin demographic prompts. Source: https://hai.stanford.edu/news/ai-agents-simulate-1052-individuals-personalities-with-impressive-accuracy
- INFORMS reported a Marketing Science study finding 75%-85% agreement between LLM-generated and human data sets for certain market research perceptual-analysis tasks. Useful, but not proof that ad revenue can be predicted deterministically. Source: https://www.informs.org/News-Room/INFORMS-Releases/News-Releases/Can-Large-Language-Models-Replace-Human-Participants-in-Some-Future-Market-Research
- NN/g's practical synthesis warns that accuracy depends on demographic group, task, context, and model-building method, and recommends starting from data-rich touchpoints such as survey histories or interviews before heavier techniques. Source: https://www.nngroup.com/articles/ai-simulations-studies/
- NIM's silicon-samples guidance warns not to take LLM outputs at face value, and recommends benchmarking against human data, careful model selection, prompt design, and added context through RAG or fine-tuning where justified. Source: https://www.nim.org/en/publications/detail/using-silicon-samples-in-marketing-research

Implication for BBW: market it as "conversion preflight," "objection mapping," and "copy improvement," not as "92% accurate revenue prediction."

## Offer Shape

### Tier 1: Conversion Snapshot

Price target: `$99-$199` standalone, or free/discounted as a sales tool for a warm prospect.

Inputs:

- URL or pasted page copy
- business category and city
- target service or offer
- top desired action: call, form, booking, checkout

Outputs:

- 1-page scorecard
- top 5 conversion blockers
- top 5 trust gaps
- rewrite of hero, CTA, and one service section
- "Should we rebuild?" recommendation

### Tier 2: Conversion Audit

Price target: `$299-$750` early, `$750-$1,500` once deliverables look premium.

Outputs:

- audience-panel report
- persona-by-persona objections
- trust and clarity audit
- booking/friction audit
- rewritten homepage or landing page copy
- implementation backlog ranked by expected impact and effort

### Tier 3: Ad Copy Lab

Price target: add-on to Package C, `$150-$300/mo` early or included in a higher Package C price.

Outputs:

- Google or Meta ad variants
- persona critiques
- compliance/trust flags
- ranked winner and rationale
- monthly learning log

## Integration Strategy

Do this in three product phases:

1. **Manual service proof:** Create docs, templates, and sample artifacts. Sell and fulfill 3-5 audits by hand using LLMs and operator judgment.
2. **Typed agency workflow:** Add schemas, catalog services, artifact writers, and CLIs once the deliverable stabilizes.
3. **Automation lane:** Add a bounded `conversion_lab` worker flow only after the manual service proves repeatability and client demand.

Do not add a new top-level `products/synthetic-audience-lab/` application yet. This is first an agency capability under `packages/agency/` and `docs/agency/`.

## Task 1: Add Manual Conversion Lab Runbook

**Files:**

- Create: `docs/agency/conversion-lab.md`
- Modify: `docs/agency/INDEX.md`
- Modify: `docs/agency/prospect-to-client-pipeline.md`

**Step 1: Write the runbook doc**

Create `docs/agency/conversion-lab.md` with:

```markdown
# Conversion Lab

Conversion Lab is BBW's preflight workflow for auditing a website, landing page, promo page, or ad before redesign or spend.

## Positioning

Sell the business outcome:

- Find conversion blockers before rebuild work.
- Identify trust gaps before ad spend.
- Rewrite the sections most likely to affect calls, forms, bookings, or purchases.

Do not sell "AI focus groups" as the product, and do not claim deterministic revenue prediction.

## Inputs

- Business name
- Vertical
- City or service area
- URL or pasted copy
- Target service or offer
- Desired conversion action
- Known customer notes, reviews, calls, or objections

## Manual Workflow

1. Select one vertical persona pack.
2. Run page extraction or paste the page copy.
3. Ask each persona for clarity, trust, objection, and action-likelihood feedback.
4. Summarize cross-persona patterns.
5. Rewrite the highest-impact sections.
6. Score the page using the rubric.
7. Create the client-facing report.

## Report Sections

- Executive summary
- Audience panel
- Conversion blockers
- Trust gaps
- Objections
- Copy rewrites
- Priority backlog
- Confidence and caveats

## Boundaries

- Exploratory preflight only.
- No guaranteed revenue predictions.
- No use of private customer data without client permission.
- No automated ad launch or spend.
```

**Step 2: Link it from agency docs**

Add a row to `docs/agency/INDEX.md` for `conversion-lab.md`.

Add Conversion Lab to `docs/agency/prospect-to-client-pipeline.md`:

- Stage 4 demo: optional audit of the prospect's existing page or marketplace profile.
- Stage 6 sell: paid audit as a standalone entry product.
- Stage 9 recurring: ad/promo preflight for Package C.

**Step 3: Verify docs**

Run:

```bash
./scripts/ci/check_doc_paths.sh
```

Expected: PASS.

**Step 4: Commit**

```bash
git add docs/agency/conversion-lab.md docs/agency/INDEX.md docs/agency/prospect-to-client-pipeline.md
git commit -m "docs: add conversion lab agency runbook"
```

## Task 2: Add Persona Pack Templates

**Files:**

- Create: `docs/agency/conversion-lab/persona-pack-template.md`
- Create: `docs/agency/conversion-lab/report-template.md`
- Create: `docs/agency/conversion-lab/sample-med-spa-personas.md`

**Step 1: Create persona pack template**

Create `docs/agency/conversion-lab/persona-pack-template.md` with metadata, evidence sources, dossier sections, fears, objections, trust signals, dealbreakers, decision process, language they use, and a reusable review prompt.

**Step 2: Create report template**

Create `docs/agency/conversion-lab/report-template.md` with these sections:

- Executive Summary
- Audience Panel
- Scorecard
- Top Conversion Blockers
- Top Trust Gaps
- Persona Feedback
- Recommended Copy
- Priority Backlog
- Confidence

The confidence section must say the report is synthetic-audience preflight and does not replace live analytics, ad experiments, or real customer interviews.

**Step 3: Create med spa seed pack**

Create `docs/agency/conversion-lab/sample-med-spa-personas.md` with 7 seed personas:

- nervous first-time Botox buyer
- affluent regular aesthetics buyer
- budget-conscious mom
- bride/event-driven buyer
- executive with limited time
- skeptical research-heavy buyer
- post-weight-loss body contouring buyer

Each should be at least 500 words for the manual proof phase. Do not invent medical claims. Focus on decision behavior, trust, objections, and buying triggers.

**Step 4: Verify docs**

Run:

```bash
./scripts/ci/check_doc_paths.sh
```

Expected: PASS.

**Step 5: Commit**

```bash
git add docs/agency/conversion-lab/
git commit -m "docs: add conversion lab persona templates"
```

## Task 3: Add Catalog Services After Manual Proof

Do this only after at least 3 manual audits produce useful reports.

**Files:**

- Modify: `packages/agency/catalog.yaml`
- Modify: `docs/agency/service-catalog.md`
- Test: `tests/python/unit/test_agency_catalog.py`

**Step 1: Write the failing test**

Add:

```python
def test_conversion_lab_services_exist():
    catalog = load_catalog()
    assert catalog.service("conversion_snapshot").name == "Conversion Snapshot"
    assert catalog.service("conversion_audit").name == "Conversion Audit"
    assert catalog.service("ad_copy_lab").name == "Ad Copy Lab"
```

Run:

```bash
python -m pytest tests/python/unit/test_agency_catalog.py -q
```

Expected: FAIL because the services do not exist.

**Step 2: Add services to catalog**

Add to `packages/agency/catalog.yaml`:

```yaml
  - service_id: conversion_snapshot
    name: Conversion Snapshot
    tier: tier_2
    bill_type: one_time
    setup_fee: 199
    monthly_fee: 0
    includes:
      - Synthetic audience preflight for one page or ad
      - Conversion blocker scorecard
      - Trust gap review
      - Hero and CTA rewrite

  - service_id: conversion_audit
    name: Conversion Audit
    tier: tier_2
    bill_type: one_time
    setup_fee: 750
    monthly_fee: 0
    includes:
      - Synthetic audience report for one website or landing page
      - Persona-by-persona objections
      - Trust and clarity audit
      - Priority implementation backlog
      - Homepage or landing page copy rewrite

  - service_id: ad_copy_lab
    name: Ad Copy Lab
    tier: tier_3
    bill_type: recurring
    setup_fee: 150
    monthly_fee: 200
    includes:
      - Monthly ad copy preflight
      - Persona critiques
      - Three copy variants
      - Ranked recommendation before operator-approved spend
```

Do not add these to Package A. Consider adding `conversion_snapshot` to Package B and `ad_copy_lab` to Package C only after price positioning is decided.

**Step 3: Regenerate service catalog**

Find the existing render command in `packages/agency/catalog.py` or related scripts. If no script exists, update `docs/agency/service-catalog.md` manually from the YAML in the same style as existing rows.

**Step 4: Run tests**

```bash
python -m pytest tests/python/unit/test_agency_catalog.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add packages/agency/catalog.yaml docs/agency/service-catalog.md tests/python/unit/test_agency_catalog.py
git commit -m "feat: add conversion lab services to agency catalog"
```

## Task 4: Add Typed Conversion Lab Schemas

**Files:**

- Create: `packages/schemas/conversion_lab.py`
- Test: `tests/python/unit/test_conversion_lab_schema.py`

**Step 1: Write failing schema tests**

Create tests for `ConversionLabInput`, `Scorecard`, `PersonaReview`, and `ConversionLabReport` round-tripping through `to_dict` and `from_dict`. Include an invalid score test that rejects scores outside `1..10`.

Run:

```bash
python -m pytest tests/python/unit/test_conversion_lab_schema.py -q
```

Expected: FAIL because `packages.schemas.conversion_lab` does not exist.

**Step 2: Implement schema dataclasses**

Create `packages/schemas/conversion_lab.py` using the repo's existing dataclass `to_dict` / `from_dict` pattern. Include:

- `ConversionAction`: `call`, `form`, `booking`, `purchase`, `reply`
- `ConversionLabInput`
- `PersonaReview`
- `Scorecard`
- `ConversionLabReport`

Keep scores as integers from 1 to 10.

**Step 3: Run tests**

```bash
python -m pytest tests/python/unit/test_conversion_lab_schema.py -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add packages/schemas/conversion_lab.py tests/python/unit/test_conversion_lab_schema.py
git commit -m "feat: add conversion lab schemas"
```

## Task 5: Add Report Builder Module

**Files:**

- Create: `packages/agency/conversion_lab.py`
- Create: `scripts/agency/build_conversion_lab_report.py`
- Test: `tests/python/unit/test_agency_conversion_lab.py`

**Step 1: Write failing builder tests**

Create tests that assert:

- report markdown includes executive summary, scorecard, persona feedback, blockers, rewrites, and caveat
- output path defaults to `state/clients/<product_id>/conversion_lab/<run_id>/REPORT.md`
- runtime artifacts are never written into `docs/` by default

Run:

```bash
python -m pytest tests/python/unit/test_agency_conversion_lab.py -q
```

Expected: FAIL because the module does not exist.

**Step 2: Implement report rendering**

Create `packages/agency/conversion_lab.py` with:

- `render_report_markdown(report: ConversionLabReport) -> str`
- `write_report(report: ConversionLabReport, *, root: Path, run_id: str) -> Path`

The renderer should include the caveat that synthetic-audience review is preflight intelligence, not proof of future revenue.

**Step 3: Add CLI**

Create `scripts/agency/build_conversion_lab_report.py` to accept a JSON report payload and `--run-id`, then call `write_report`.

**Step 4: Run tests**

```bash
python -m pytest tests/python/unit/test_agency_conversion_lab.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add packages/agency/conversion_lab.py scripts/agency/build_conversion_lab_report.py tests/python/unit/test_agency_conversion_lab.py
git commit -m "feat: render conversion lab reports"
```

## Task 6: Add Persona Pack Loader

**Files:**

- Create: `packages/agency/conversion_personas.py`
- Create: `packages/agency/conversion_personas/med_spa.yaml`
- Test: `tests/python/unit/test_agency_conversion_personas.py`

**Step 1: Write failing tests**

Test that:

- `load_persona_pack("med_spa")` returns at least 7 personas
- every persona has `persona_id`, `vertical`, `dossier`, `trust_signals`, `objections`, and `review_prompt`
- duplicate persona IDs fail validation
- missing pack fails clearly

Run:

```bash
python -m pytest tests/python/unit/test_agency_conversion_personas.py -q
```

Expected: FAIL.

**Step 2: Implement loader**

Create YAML-backed loader under `packages/agency/conversion_personas.py`. Do not put large dossiers in code. YAML is the source for v1 because these are business assets the operator will revise.

**Step 3: Seed med spa pack**

Create `packages/agency/conversion_personas/med_spa.yaml` from the manual doc pack once the first manual audit is done. Keep each dossier concise enough to review in code, but rich enough to avoid demographic-only roleplay.

**Step 4: Run tests**

```bash
python -m pytest tests/python/unit/test_agency_conversion_personas.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add packages/agency/conversion_personas.py packages/agency/conversion_personas/med_spa.yaml tests/python/unit/test_agency_conversion_personas.py
git commit -m "feat: add conversion lab persona packs"
```

## Task 7: Add Synthetic Review Prompt Builder

**Files:**

- Modify: `packages/agency/conversion_lab.py`
- Test: `tests/python/unit/test_agency_conversion_lab.py`

**Step 1: Write failing prompt tests**

Test that generated persona-review prompts include:

- the page copy
- the target action
- the persona dossier
- required output keys
- the caveat that the persona is a simulation

Run:

```bash
python -m pytest tests/python/unit/test_agency_conversion_lab.py -q
```

Expected: FAIL.

**Step 2: Implement prompt builder**

Add:

```python
def build_persona_review_prompt(*, persona, input_payload) -> str:
    return f"""Embody the following buyer persona for exploratory conversion review.

This is a synthetic simulation, not a real customer interview.

Persona:
{persona.dossier}

Business vertical: {input_payload.vertical}
Target action: {input_payload.target_action.value}

Page copy:
{input_payload.page_copy}

Return JSON with:
- likely_action
- clarity_notes
- objections
- trust_gaps
- useful_rewrites
- confidence
"""
```

Use `embody`, but keep the explicit simulation caveat for ethics and client honesty.

**Step 3: Run tests**

```bash
python -m pytest tests/python/unit/test_agency_conversion_lab.py -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add packages/agency/conversion_lab.py tests/python/unit/test_agency_conversion_lab.py
git commit -m "feat: build conversion lab review prompts"
```

## Task 8: Wire Conversion Lab Into Package C Ad Preflight

**Files:**

- Modify: `docs/agency/operator-ads-playbook.md`
- Modify: `packages/agency/google_ads.py`
- Modify: `packages/agency/meta_ads.py`
- Test: `tests/python/unit/test_agency_google_ads.py`
- Test: `tests/python/unit/test_agency_meta_ads.py`

**Step 1: Write failing tests**

Add tests that ad drafts can carry an optional `conversion_lab_report_path` or `preflight_summary`.

Run:

```bash
python -m pytest tests/python/unit/test_agency_google_ads.py tests/python/unit/test_agency_meta_ads.py -q
```

Expected: FAIL.

**Step 2: Add optional preflight field**

Extend ad draft dataclasses or markdown rendering with:

```markdown
## Conversion Lab Preflight

- Report:
- Main objections:
- Recommended winning angle:
- Copy risks:
```

Do not require this field for all ads. Package C can still draft ads without a preflight report.

**Step 3: Update playbook**

In `docs/agency/operator-ads-playbook.md`, add Conversion Lab as the recommended preflight before go-live for new ad campaigns, while keeping go-live approval and client budget confirmation unchanged.

**Step 4: Run tests**

```bash
python -m pytest tests/python/unit/test_agency_google_ads.py tests/python/unit/test_agency_meta_ads.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add docs/agency/operator-ads-playbook.md packages/agency/google_ads.py packages/agency/meta_ads.py tests/python/unit/test_agency_google_ads.py tests/python/unit/test_agency_meta_ads.py
git commit -m "feat: add conversion lab ad preflight"
```

## Task 9: Add Operator CLI For Manual Runs

**Files:**

- Create: `scripts/agency/run_conversion_lab.py`
- Test: `tests/python/unit/test_agency_conversion_lab_cli.py`

**Step 1: Write failing CLI tests**

Use `tmp_path` to create a sample input JSON, a sample persona pack, and a stubbed synthetic review result. Assert the CLI writes:

- `INPUT.json`
- `PROMPTS.md`
- `REPORT.md`

Run:

```bash
python -m pytest tests/python/unit/test_agency_conversion_lab_cli.py -q
```

Expected: FAIL.

**Step 2: Implement CLI without model calls**

V1 CLI should not call OpenAI or Anthropic directly. It should prepare prompts and accept pasted or JSON review results. This keeps the first version provider-neutral and easy to audit.

Commands:

```bash
python scripts/agency/run_conversion_lab.py prepare \
  --product-id smooth-med-spa-site \
  --vertical med_spa \
  --target-action booking \
  --url https://example.com \
  --page-copy-file page.txt \
  --run-id 2026-06-11-001

python scripts/agency/run_conversion_lab.py render \
  --product-id smooth-med-spa-site \
  --run-id 2026-06-11-001 \
  --reviews-json reviews.json
```

**Step 3: Run tests**

```bash
python -m pytest tests/python/unit/test_agency_conversion_lab_cli.py -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add scripts/agency/run_conversion_lab.py tests/python/unit/test_agency_conversion_lab_cli.py
git commit -m "feat: add conversion lab operator cli"
```

## Task 10: Update Architecture And Agent Model After The Lane Exists

Only do this after Tasks 3-9 land. Before then, this is just an agency runbook.

**Files:**

- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/agent-model.md`
- Modify: `docs/architecture.md`

**Step 1: Update docs**

Document Conversion Lab as an agency capability, not a new autonomous worker:

- Platform owns service state and approvals.
- Operator owns client-facing claims.
- Ads stay draft-only until existing `ad_campaign_go_live` gate.
- Synthetic audience reports are advisory artifacts.

**Step 2: Verify doc path integrity**

Run:

```bash
./scripts/ci/check_doc_paths.sh
```

Expected: PASS.

**Step 3: Commit**

```bash
git add README.md AGENTS.md docs/agent-model.md docs/architecture.md
git commit -m "docs: document conversion lab agency capability"
```

## Milestones

### Milestone 1: Sell Manually

Duration: 2-4 days.

Deliver:

- runbook
- report template
- med spa seed personas
- 1 sample report against a real or demo page

Revenue target:

- first paid audit within 1-3 weeks if attached to active BBW outreach or inbound
- price at `$99-$299` until the report quality is proven

### Milestone 2: Productize

Duration: 1-2 weeks after manual proof.

Deliver:

- catalog services
- schemas
- report builder
- persona loader
- operator CLI

Revenue target:

- include in Package C sales motion
- use as paid diagnostic before website rebuild

### Milestone 3: Automate Carefully

Duration: 2-4 weeks after productized workflow proves repeatable.

Deliver:

- provider-backed model calls
- batch persona reviews
- PDF export if customers ask for it
- dashboard surface only if volume justifies it

Revenue target:

- recurring `Ad Copy Lab` attached to ad management
- higher Package C price or conversion retainer

## Risks And Guardrails

- **Overclaiming:** Never claim "92% accurate" or guaranteed revenue lift in BBW marketing.
- **Thin personas:** Avoid demographic-only prompts. Use reviews, calls, client notes, service details, and real objections.
- **Medical/legal compliance:** Med spa and law firm copy must avoid unverified outcomes and misleading claims.
- **Synthetic bias:** Include confidence labels and caveats in every report.
- **Data consent:** Do not turn private customer conversations into persona dossiers unless the client has permission to use that data.
- **Automation too early:** No SaaS, no dashboard, and no model-provider integration until manual reports sell and repeat.

## Validation

Run after the docs-only phase:

```bash
./scripts/ci/check_doc_paths.sh
make plans-index-check
```

Run after code phases:

```bash
python -m pytest \
  tests/python/unit/test_agency_catalog.py \
  tests/python/unit/test_conversion_lab_schema.py \
  tests/python/unit/test_agency_conversion_lab.py \
  tests/python/unit/test_agency_conversion_personas.py \
  tests/python/unit/test_agency_google_ads.py \
  tests/python/unit/test_agency_meta_ads.py \
  -q
```

Run full Python verification before PR:

```bash
./scripts/test_python.sh
```

## Decisions

Resolved at ship (2026-06-11). Edit here if the go-to-market motion changes.

- **`conversion_snapshot` pricing shape:** Standalone paid offer at **$199** (catalog:
  `conversion_snapshot`). Use as a **proposal sweetener** for warm prospects — not a
  free lead magnet. Deeper work stays on `conversion_audit` ($750).
- **First vertical to sell:** **Med spas.** Higher perceived value, existing seed pack
  (`med_spa.yaml`, sample personas), and strong fit for trust-heavy conversion copy.
  Roofing and HVAC remain strong second-wave verticals once the med-spa motion repeats.
- **Ad Copy Lab vs Package C:** **Optional Package C add-on**, not absorbed into base
  Package C pricing. Catalog lists `ad_copy_lab` at $150 setup + $200/mo so C stays
  entry-priced while ad-heavy clients can upsell preflight + copy iteration.
- **Persona pack home:** **`packages/agency/conversion_personas/`** is the runtime
  source of truth (YAML loaded by `load_persona_pack` / `load_audience_panel`).
  `docs/agency/conversion-lab/` holds operator templates, samples, and human-readable
  docs — not the loader target for mature packs.

## Next Steps (post-ship)

Manual proof before Milestone 3 automation:

1. Run three paid or pilot Conversion Lab audits (med spa first).
2. Capture whether the report changes close rate or rebuild scope.
3. Only then consider provider-backed batch reviews, PDF export, or dashboard surfacing.
