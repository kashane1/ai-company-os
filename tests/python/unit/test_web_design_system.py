"""Tests for the design-system synthesizer (Phase 1 of the design engine).

The synthesizer turns a packet into a role-based token set — the deterministic,
testable craft layer. We can't assert "the tokens look good" (that's the visual
rubric's job), but we CAN assert the contract a five-figure build depends on:
deterministic output, AA-valid color roles, a zoom-safe monotonic type scale, and
a valid W3C DTCG token document.
"""

from __future__ import annotations

import re

from packages.web.design_studio import WebsiteDesignRequest, build_design_studio_packet
from packages.web.design_system import synthesize_design_system
from packages.web.palette import passes_aa

CINEMATIC = build_design_studio_packet(
    WebsiteDesignRequest(
        site_name="TrueLine Plumbing",
        business_category="plumbing",
        audience="homeowners",
        goal="sell a high-trust preview site",
        evidence=["reviews praise careful cleanup"],
        concept_statement="precision you can see; the calm craftsman",
    )
)
GALLERY = build_design_studio_packet(
    WebsiteDesignRequest(
        site_name="Lumiere Nail Lounge",
        business_category="nail salon",
        audience="clients choosing by visual proof",
        goal="show artistry",
    )
)


def test_synthesis_is_deterministic() -> None:
    a = synthesize_design_system(CINEMATIC)
    b = synthesize_design_system(CINEMATIC)
    assert a.to_dtcg() == b.to_dtcg()
    assert a.to_css() == b.to_css()


def test_color_roles_pass_wcag_aa() -> None:
    ds = synthesize_design_system(CINEMATIC)
    # Body text on the dominant canvas must clear AA 4.5:1.
    assert passes_aa(ds.roles["ink"], ds.roles["canvas"])
    # CTA label on the accent must clear AA (large/UI threshold at minimum).
    assert passes_aa(ds.roles["on-accent"], ds.roles["accent"], large=True)


def test_cinematic_archetype_is_dark_gallery_is_light() -> None:
    from packages.web.palette import relative_luminance

    dark = synthesize_design_system(CINEMATIC)
    light = synthesize_design_system(GALLERY)
    assert relative_luminance(dark.roles["canvas"]) < 0.2
    assert relative_luminance(light.roles["canvas"]) > 0.6


def test_type_scale_is_monotonic_and_body_is_at_least_1rem() -> None:
    ds = synthesize_design_system(CINEMATIC)
    sizes = [step.max_rem for step in ds.type_scale]
    assert sizes == sorted(sizes)  # monotonic increasing by step
    body = next(s for s in ds.type_scale if s.step == 0)
    assert body.max_rem >= 1.0  # WCAG body floor


def test_fluid_type_is_zoom_safe_rem_plus_vw() -> None:
    # WCAG 1.4.4: a vw-only preferred term freezes text against zoom. Every fluid
    # step's clamp() preferred value must contain a rem term, and min/max must be
    # rem (never px).
    ds = synthesize_design_system(CINEMATIC)
    for step in ds.type_scale:
        css = step.to_css_clamp()
        assert "px" not in css
        if "clamp(" in css:  # fluid steps only
            preferred = css.split(",")[1]
            assert "rem" in preferred and "vw" in preferred


def test_dtcg_document_is_valid_two_tier() -> None:
    doc = synthesize_design_system(CINEMATIC).to_dtcg()
    # Semantic color roles exist and every leaf token has $value + $type.
    assert "color" in doc and "canvas" in doc["color"]

    def _check(node: dict) -> int:
        leaves = 0
        for key, val in node.items():
            if key.startswith("$"):
                continue
            assert isinstance(val, dict), f"{key} must be a group or token"
            if "$value" in val:
                assert "$type" in val
                leaves += 1
            else:
                leaves += _check(val)
        return leaves

    assert _check(doc) > 0
    # Two-tier: at least one semantic role aliases a primitive via {ref} syntax.
    flat = str(doc)
    assert re.search(r"\{[a-z0-9.-]+\}", flat), "expected DTCG aliases for tiering"


def test_motion_preset_is_archetype_driven_and_exposed() -> None:
    dark = synthesize_design_system(CINEMATIC)
    light = synthesize_design_system(GALLERY)
    assert dark.motion_preset == "cinematic"
    assert light.motion_preset == "gallery"
    assert '--motion-preset: "cinematic"' in dark.to_css()


def test_css_exposes_role_custom_properties() -> None:
    css = synthesize_design_system(CINEMATIC).to_css()
    for role in ("--canvas", "--ink", "--accent", "--on-accent", "--display-font", "--body-font"):
        assert role in css
    assert ":root" in css
    assert "--step-0" in css  # body type step


def test_supplied_concept_palette_seeds_the_system() -> None:
    packet = build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="Acme",
            business_category="plumbing",
            audience="homeowners",
            goal="x",
            concept_palette="#7c3aed",  # explicit brand hex cue
        )
    )
    ds = synthesize_design_system(packet)
    # Accent should derive from the supplied seed, not the genre default.
    assert ds.roles["accent"].startswith("#")
    assert passes_aa(ds.roles["on-accent"], ds.roles["accent"], large=True)
