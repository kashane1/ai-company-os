---
status: pending
priority: p2
issue_id: "040"
tags: [code-review, testing, drift-guard, data-integrity, agency]
dependencies: ["034", "038"]
---

# Problem Statement

The drift-guard tests will go RED by design, and the plan understates the rewrite: it's a units change (dollars→cents) + value change + a new gross/net split, plus a cross-language golden test that must cover BOTH the promo override and the tier paths.

## Findings (data-integrity P2-1/P2-3, pattern P1-2)

1. `test_agency_catalog_json.py:25-30` asserts whole-dollar tuples `(699,49)/(999,99)/(1399,624)` — rewrite (not edit) to cents with gross + after split.
2. `test_agency_service_catalog_render.py` anchor strings change (it builds `f"${quote.setup_total:,.0f} setup…"`).
3. Golden fixture keyed on `service_ids` alone **cannot** distinguish promo vs tier — a custom cart of A's services and preset A share `service_ids` but must produce different `setup_after_cents`. Fixture needs a discriminator (e.g. `{service_ids, setup_promo_cents|null}`) so both paths are asserted byte-identical Py↔JS. Include ≥1 preset row where promo ≠ tier.
4. Half-cent boundary test needs a synthetic fixture (no real half-cent in catalog).

## Proposed Solutions

### Option 1 (recommended): explicit assertions
```
# promo path (cents)
assert (a.setup_gross_cents, a.setup_after_cents, a.monthly_cents) == (69900, 59900, 4900)
assert (b…) == (107400, 89900, 8800)
assert (c…) == (222400, 179900, 55300)
# custom cart of SAME service_ids prices strictly higher; monthly identical
for pkg, after in [("package_a",59900),("package_b",89900),("package_c",179900)]:
    q = quote_services(catalog.bundles[pkg].service_ids)   # tier, no override
    assert q.setup_after_cents > after
    assert q.monthly_cents == <promo monthly>
# savings by subtraction + monthly invariant across tiers
```
Plus a Node golden-vector test asserting JS produces identical integers for promo rows AND tier rows.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected: `tests/python/unit/test_agency_catalog_json.py` (rewrite), `test_agency_service_catalog_render.py` (anchors), new Node golden-vector test + fixture (Python-generated). Confirm whether `meta_ads`/`follow_up_automation`/`crm_setup` (not in any A/B/C bundle) need re-split or only in-bundle services.

## Acceptance Criteria

- [ ] Python tests assert cents, gross+after, custom>promo, monthly-invariant, savings-by-subtraction.
- [ ] Golden fixture discriminates promo vs tier; ≥1 promo≠tier preset row; synthetic half-cent.
- [ ] Node golden test green against the Python-generated fixture.

## Work Log

(to be filled in)

## Resources

- /workflows:review round 2 (2026-06-06): data-integrity P2-1/P2-3, pattern-recognition P1-2
