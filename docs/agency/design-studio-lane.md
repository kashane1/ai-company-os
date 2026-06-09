# Design Studio Lane

The Design Studio layer is the premium-design contract for Better Business Web.
It does not replace the existing web lane. It sits before and after the build:

1. Evidence and intake
2. Design Studio packet
3. Bespoke or Astro build
4. Desktop and mobile screenshots
5. Design Studio visual review
6. Existing web validation and UX audit
7. Deploy approval

The core code lives in `packages/web/design_studio.py`.

## Why It Exists

The old gates answer technical questions:

- Does the site build?
- Do links and assets resolve?
- Is there a viewport?
- Does baseline accessibility pass?
- Is SEO minimally present?

Those checks are necessary, but they do not catch the expensive failure mode:
a valid page that looks generic. The Design Studio layer checks whether the work
has a visual thesis, a memorable hero, art-directed imagery, strong type, varied
composition, and copy grounded in real evidence.

## Packet Contract

`build_design_studio_packet()` turns a `WebsiteDesignRequest` into a structured
`DesignStudioPacket` with:

- concept statement
- structural archetype
- palette strategy
- typography direction
- imagery plan
- motion plan
- reference translations
- copy constraints
- required build phases
- required screenshots
- visual QA thresholds

Reference translation is explicit: references are inspiration, not copy targets.
The packet preserves the rule that small-business pages must derive from real
business evidence first.

## Visual Review Contract

`review_visual_quality()` takes category scores plus screenshot paths and returns
a `VisualReviewReport` with normal `ValidationCheck` objects. A technically valid
page can still fail this report if it has no visual thesis, weak hero, weak image
system, low category scores, or missing desktop/mobile screenshots.

Minimum defaults:

- overall visual score: 80/100
- category floor: 4/5
- required screenshots: desktop and mobile
- critical categories: visual thesis, hero impact, imagery art direction

## How It Fits The Existing Paths

**Path B, bespoke prospect demos:** Use the Design Studio packet before writing
`dist-v2/index.html`. The packet should guide the human/agent build and the
visual review should run after screenshot capture.

**Path C, paid client Astro sites:** Use the packet before scaffold customization.
The Astro scaffold remains the build surface, but the packet decides the concept,
imagery, type direction, and visual QA bar.

## Example

```python
from packages.web.design_studio import (
    DesignReference,
    WebsiteDesignRequest,
    build_design_studio_packet,
)

packet = build_design_studio_packet(
    WebsiteDesignRequest(
        site_name="TrueLine Plumbing",
        business_category="plumbing",
        audience="homeowners who want calm, precise service",
        goal="sell a high-trust preview site",
        evidence=["reviews praise careful cleanup and clear quotes"],
        visual_assets=["two usable work photos"],
        references=[
            DesignReference(
                title="B2B SaaS Landing Page Design for HackerRank",
                url="https://dribbble.com/shots/26414267-B2B-SaaS-Landing-Page-Design-for-HackerRank",
                source_type="dribbble",
                takeaways=["large device-frame hero", "single strong visual thesis"],
            )
        ],
        imagery_mode="concept-led",
    )
)
```

## Operating Rule

A site is not premium-ready until both layers pass:

- Design Studio visual review
- Existing web validation and UX audit
