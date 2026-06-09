"""Tests for the Design Studio layer of the web lane.

The existing web gate proves a site builds, links resolve, and baseline UX is
sound. These tests lock the missing premium-design contract: art direction,
reference translation, imagery planning, screenshot-backed visual review, and a
rubric that can reject "valid but generic" pages.
"""

from __future__ import annotations

from packages.web.design_studio import (
    DesignReference,
    VisualScore,
    WebsiteDesignRequest,
    build_design_studio_packet,
    review_visual_quality,
)

RAMOTION = DesignReference(
    title="B2B SaaS Landing Page Design for HackerRank",
    url="https://dribbble.com/shots/26414267-B2B-SaaS-Landing-Page-Design-for-HackerRank",
    source_type="dribbble",
    takeaways=[
        "large device-frame hero",
        "black canvas with precise green accent",
        "single strong visual thesis",
    ],
)

HALO = DesignReference(
    title="Landing Page for Construction Company",
    url="https://dribbble.com/shots/24175820-Landing-Page-for-Construction-Company",
    source_type="dribbble",
    takeaways=[
        "editorial typography",
        "architectural scene as the hero",
        "layered supporting cards",
    ],
)


def test_build_design_studio_packet_turns_business_context_into_art_direction() -> None:
    packet = build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="TrueLine Plumbing",
            business_category="plumbing",
            audience="homeowners who want calm, precise service",
            goal="sell a high-trust preview site",
            evidence=[
                "reviews praise careful cleanup and clear quotes",
                "existing photos are weak and mostly dark sink shots",
            ],
            visual_assets=["owner logo", "two usable work photos"],
            references=[RAMOTION, HALO],
            imagery_mode="concept-led",
        )
    )

    assert packet.concept_statement
    assert "plumbing" in packet.concept_statement.lower()
    assert packet.archetype == "service-area-cinematic"
    assert packet.palette_strategy.startswith("derive from evidence")
    assert "distinctive display" in packet.type_direction
    assert any("hero" in item.lower() for item in packet.imagery_plan)
    assert any("reduced-motion" in item.lower() for item in packet.motion_plan)
    assert packet.required_build_phases == [
        "evidence",
        "reference-translation",
        "creative-direction",
        "imagery",
        "build",
        "screenshot-review",
        "technical-gates",
    ]
    assert {"desktop", "mobile"}.issubset(set(packet.required_screenshots))
    assert "copy only from evidence" in " ".join(packet.copy_constraints).lower()


def test_supplied_concept_statement_overrides_the_derived_one() -> None:
    concept = "precision you can see; the calm craftsman, not the panicked emergency"
    packet = build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="TrueLine Plumbing",
            business_category="plumbing",
            audience="homeowners",
            goal="sell a high-trust preview site",
            evidence=["reviews praise careful cleanup"],
            concept_statement=concept,
        )
    )
    # The human/agent line wins verbatim; the evidence-derived template is not used.
    assert packet.concept_statement == concept
    assert "should feel like" not in packet.concept_statement


def test_absent_concept_statement_falls_back_to_derived_line() -> None:
    packet = build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="TrueLine Plumbing",
            business_category="plumbing",
            audience="homeowners",
            goal="sell a high-trust preview site",
            evidence=["reviews praise careful cleanup"],
        )
    )
    assert "should feel like" in packet.concept_statement


def test_reference_translation_keeps_inspiration_from_becoming_copying() -> None:
    packet = build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="Northside Coffee",
            business_category="coffee shop",
            audience="regulars who linger",
            goal="make the room feel memorable before a visit",
            evidence=["warm wood interior", "reviews mention slow mornings"],
            visual_assets=["hero cafe photo"],
            references=[RAMOTION, HALO],
        )
    )

    assert [item.reference_title for item in packet.reference_translations] == [
        RAMOTION.title,
        HALO.title,
    ]
    assert all(
        item.rule.startswith("Translate, do not copy")
        for item in packet.reference_translations
    )
    assert any(
        "large device-frame hero" in item.observed_pattern
        for item in packet.reference_translations
    )
    assert all("copy" not in item.application.lower() for item in packet.reference_translations)


def test_visual_review_rejects_technically_valid_but_generic_page() -> None:
    report = review_visual_quality(
        scores=[
            VisualScore("visual_thesis", 2, "Looks like a neutral template"),
            VisualScore("hero_impact", 3, "Readable but forgettable"),
            VisualScore("imagery_art_direction", 2, "No cohesive image system"),
            VisualScore("typography", 3, "Safe sans stack"),
            VisualScore("layout_composition", 3, "Uniform cards and centered sections"),
            VisualScore("copy_specificity", 4, "Grounded enough"),
        ],
        screenshots={"desktop": "/tmp/site-desktop.png", "mobile": "/tmp/site-mobile.png"},
    )

    assert report.passed is False
    assert report.overall < 80
    assert "design_studio_no_visual_thesis" in report.failure_codes
    assert "design_studio_weak_imagery" in report.failure_codes
    assert any(check.name == "design-studio-visual-quality" for check in report.checks)


def _strong_scores() -> list[VisualScore]:
    """A full v3 (12-dimension) passing score set."""
    values = {
        "visual_thesis": 5, "hero_impact": 5, "imagery_art_direction": 4,
        "typography": 4, "color_system": 4, "layout_composition": 4,
        "whitespace_depth": 4, "motion_quality": 4, "signature_moment": 4,
        "conversion_strength": 4, "copy_specificity": 5, "ai_house_style": 5,
    }
    return [VisualScore(cat, score, "strong") for cat, score in values.items()]


def test_visual_review_requires_desktop_and_mobile_screenshots() -> None:
    report = review_visual_quality(
        scores=_strong_scores(),
        screenshots={"desktop": "/tmp/site-desktop.png"},
    )

    assert report.passed is False
    assert "design_studio_missing_mobile_screenshot" in report.failure_codes


def test_visual_review_passes_with_strong_scores_and_required_screenshots() -> None:
    report = review_visual_quality(
        scores=_strong_scores(),
        screenshots={"desktop": "/tmp/site-desktop.png", "mobile": "/tmp/site-mobile.png"},
    )

    assert report.passed is True
    assert report.failure_codes == []
    assert report.overall >= 80


def test_visual_review_fails_on_ai_house_style_even_if_rest_is_strong() -> None:
    # ai_house_style is critical in v3: a page full of the cheap/AI tells fails even
    # when every other dimension scores well.
    scores = [s for s in _strong_scores() if s.category != "ai_house_style"]
    scores.append(VisualScore("ai_house_style", 3, "purple aurora + 3-icon grid + default sans"))
    report = review_visual_quality(
        scores=scores,
        screenshots={"desktop": "/tmp/d.png", "mobile": "/tmp/m.png"},
    )
    assert report.passed is False
    assert "design_studio_ai_house_style" in report.failure_codes


def test_design_studio_packet_serializes_as_structured_contract() -> None:
    packet = build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="Lumiere Nail Lounge",
            business_category="nail salon",
            audience="clients choosing by visual proof",
            goal="show artistry and calm",
            evidence=["reviews praise chrome sets", "photos show pink and silver work"],
            visual_assets=["chrome nails hero", "gallery set"],
            references=[HALO],
        )
    )

    payload = packet.to_dict()

    assert payload["site_name"] == "Lumiere Nail Lounge"
    assert payload["archetype"] == "gallery-led"
    assert payload["references"][0]["title"] == HALO.title
    assert payload["reference_translations"][0]["reference_title"] == HALO.title
    assert payload["visual_qa"]["minimum_overall"] == 80
