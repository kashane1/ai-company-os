---
status: done
change_id: bbw-persona-library-design
owner: kashane
last_reviewed: 2026-06-11
---

# BBW Persona Library Design

**Status:** done (shipped 2026-06-11)

## Decision

Better Business Web should cover small-business audits with reusable
buyer-situation personas plus vertical modifiers, not one giant bespoke persona
pack per category.

## Why

Most local-service websites face the same conversion questions:

- Is this business trustworthy?
- Do I understand what happens next?
- Is this worth the price or time?
- Can I get help quickly?
- Will I be embarrassed, pressured, delayed, or ignored?

Those questions repeat across plumbers, roofers, med spas, dentists, notaries,
restaurants, barbers, landscapers, and repair shops. A universal buyer panel can
catch those patterns without maintaining hundreds of brittle vertical packs.
Vertical modifiers add category-specific objections, trust signals, and compliance
notes where they matter.

## Architecture

The persona library has two layers:

1. **Core personas:** reusable buyer situations that apply across local SMBs.
2. **Vertical modifiers:** overlays for category-specific objections, trust
   signals, decision triggers, and compliance cautions.

The loader should keep existing `load_persona_pack("med_spa")` behavior working,
then add `load_audience_panel(vertical)` to compose:

- the universal core pack
- a vertical modifier
- any full vertical pack that already exists

The CLI should continue to prepare prompts for an operator. It should use the
composed audience panel by default so a new vertical can be audited without
authoring a full new persona pack first.

## Coverage Target

Core personas should cover the recurring small-business buyer situations:

- urgent problem solver
- skeptical researcher
- budget-constrained shopper
- premium convenience buyer
- safety and trust seeker
- relationship/referral buyer
- comparison shopper
- busy owner/operator buyer
- first-time anxious buyer
- repeat maintenance buyer
- family/household decision maker
- local loyalty buyer

Vertical modifiers should cover the first BBW-relevant categories:

- home services
- personal care
- health and wellness
- professional services
- food and hospitality
- auto services
- retail
- classes and activities
- real estate and property
- pet services

## Boundaries

- This is advisory conversion preflight, not revenue prediction.
- Persona packs remain editable YAML business assets.
- Private customer data does not enter packs without client permission.
- Regulated categories use cautious copy and no unsubstantiated claims.
- No ad spend, outbound sending, DNS, billing, or live campaign action changes.

## Acceptance

- A generic local business can produce a valid audience panel.
- Important BBW categories resolve through aliases such as `plumber`, `dentist`,
  `barber_shop`, `restaurant`, and `auto_repair`.
- Existing `med_spa` pack still loads.
- Prompt preparation uses the composed audience panel by default.
