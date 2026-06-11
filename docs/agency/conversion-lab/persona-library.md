# Conversion Lab Persona Library

The Conversion Lab audience panel uses a two-layer model:

- Core buyer personas in `packages/agency/conversion_personas/core.yaml`
- Vertical modifiers in `packages/agency/conversion_personas/modifiers.yaml`

`load_audience_panel(vertical)` composes the core personas with the matching
modifier. If a full vertical pack exists, such as `med_spa.yaml`, those personas
are appended to the same panel.

## Why This Model

Small businesses share many buyer situations: urgency, skepticism, budget
pressure, safety concerns, comparison shopping, referrals, first-time anxiety,
and repeat maintenance. The modifier supplies the category-specific objections,
trust signals, decision triggers, and compliance notes that keep the review from
feeling generic.

This gives Better Business Web enough coverage to audit most small-business
websites without creating a large bespoke persona pack for every niche.

## Core Personas

The current core panel covers:

- Urgent problem solver
- Skeptical researcher
- Budget-constrained shopper
- Premium convenience buyer
- Safety and trust seeker
- Relationship or referral buyer
- Comparison shopper
- Busy owner/operator buyer
- First-time anxious buyer
- Repeat maintenance buyer
- Family or household decision maker
- Local loyalty buyer

Each persona has a dossier, trust signals, objections, and review instructions.

## Supported Modifiers

| Modifier | Example verticals |
|---|---|
| `home_services` | `plumber`, `roofer`, `hvac`, `electrician`, `landscaper`, `handyman` |
| `personal_care` | `barber_shop`, `hair_salon`, `nail_salon`, `spa`, `tattoo_shop` |
| `health_wellness` | `dentist`, `med_spa`, `chiropractor`, `clinic`, `therapist` |
| `professional_services` | `notary`, `accountant`, `lawyer`, `consultant`, `insurance` |
| `food_hospitality` | `restaurant`, `cafe`, `bakery`, `bar`, `catering` |
| `auto_services` | `auto_repair`, `mechanic`, `tire_shop`, `body_shop`, `towing` |
| `retail` | `boutique`, `furniture_store`, `gift_shop`, `jewelry_store` |
| `classes_activities` | `gym`, `yoga_studio`, `dance_studio`, `music_lessons` |
| `real_estate_property` | `realtor`, `property_manager`, `home_inspector`, `mortgage_broker` |
| `pet_services` | `veterinarian`, `pet_groomer`, `dog_daycare`, `pet_boarding` |

Use the closest modifier for early audits. Add an alias when the business type
is covered by an existing modifier but the CLI should accept a new vertical name.

## Adding An Alias

Edit `packages/agency/conversion_personas/modifiers.yaml` and add the vertical
slug to the relevant modifier's `verticals` list.

Run:

```bash
python -m pytest tests/python/unit/test_agency_conversion_personas.py -q
```

Add an alias test when the new slug is likely to be reused.

## Adding A New Modifier

Create a new entry in `modifiers.yaml` with:

- `modifier_id`
- `verticals`
- `objections`
- `trust_signals`
- `decision_triggers`
- `compliance_notes` when the category has regulated or risky claims

Use a new modifier only when existing modifiers would miss category-specific
buying pressure. For example, `pet_services` needs animal-care trust cues that
do not fit cleanly into personal care or health/wellness.

## Adding A Full Vertical Pack

Create `packages/agency/conversion_personas/<vertical>.yaml` when a vertical is
important enough to need personas beyond the core panel. Keep persona IDs unique
across the composed panel.

Full packs are useful when:

- The vertical has unusually high compliance risk.
- The buying committee is specialized.
- The service mix creates distinct buyer segments.
- The vertical is a priority offer for Better Business Web.

The existing `med_spa.yaml` pack is the reference example.

## Operator Use

Prepare a run with the business vertical:

```bash
python scripts/agency/run_conversion_lab.py prepare \
  --product-id pipe-rescue-site \
  --vertical plumber \
  --target-action call \
  --page-copy-file /path/to/page.txt \
  --run-id 2026-06-11-001
```

The generated `PROMPTS.md` includes every persona plus the matched modifier
context. Reviewers should use that context as pressure, not as a source of
unsupported claims.
