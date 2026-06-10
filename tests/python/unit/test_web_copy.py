"""Tests for conversion copy (design engine v3 — Phase 4).

v2 shipped placeholder copy and treated real copy as out of scope, so the judge's
conversion dimensions had nothing real to score. These lock that the generated copy
is grounded (traces to evidence), action-oriented (CTA fits the business goal), and
never fabricates claims.
"""

from __future__ import annotations

from packages.web.copy import generate_conversion_copy, primary_cta
from packages.web.design_studio import WebsiteDesignRequest, build_design_studio_packet


def _packet(goal: str, *, category: str = "plumbing", evidence: list[str] | None = None):
    return build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="TrueLine",
            business_category=category,
            audience="homeowners who want calm, precise service",
            goal=goal,
            evidence=evidence if evidence is not None else ["20 years in business"],
            concept_statement="precision you can see; the calm craftsman",
        )
    )


def test_primary_cta_matches_business_intent() -> None:
    assert primary_cta(_packet("book more appointments")) == "Book your visit"
    assert primary_cta(_packet("get more quote requests")) == "Get a free quote"
    assert primary_cta(_packet("grow brand awareness")) == "Get in touch"  # neutral default


def test_copy_is_grounded_in_evidence() -> None:
    copy = generate_conversion_copy(
        _packet("book appointments", evidence=["ASE-certified techs", "same-day service"])
    )
    assert copy["proof_points"] == ["ASE-certified techs", "same-day service"]
    assert "precision you can see" in str(copy["headline"]).lower()
    # The first proof signal is woven into the subhead.
    assert "ASE-certified techs" in str(copy["subhead"])


def test_copy_never_fabricates_when_evidence_is_missing() -> None:
    copy = generate_conversion_copy(_packet("book appointments", evidence=[]))
    # No invented stats/testimonials — an honest prompt to add real proof instead.
    assert copy["proof_points"] == ["Add proof points from real business evidence."]
    assert "add proof" not in str(copy["subhead"]).lower()  # subhead stays neutral


def test_derive_content_uses_conversion_copy() -> None:
    from packages.web.blocks_composer import derive_content

    content = derive_content(_packet("book more appointments"))
    assert content["hero"]["primaryCta"] == "Book your visit"
    assert content["cta"]["cta"] == "Book your visit"
    assert "homeowners" in content["hero"]["subhead"]


def test_band_headline_is_distinct_from_the_hero_headline() -> None:
    # Guards the duplicate-hero bug at the copy layer: the full-bleed band must never
    # echo the hero headline.
    two_clause = generate_conversion_copy(
        _packet("book appointments")  # concept "precision you can see; the calm craftsman"
    )
    assert two_clause["band_headline"] != two_clause["headline"]
    assert two_clause["band_headline"].lower() != two_clause["headline"].lower()

    # Even a single-clause concept (no ";") gets a distinct band line, not a repeat.
    from packages.web.design_studio import WebsiteDesignRequest, build_design_studio_packet

    single = generate_conversion_copy(
        build_design_studio_packet(
            WebsiteDesignRequest(
                site_name="Acme", business_category="plumbing", audience="homeowners",
                goal="book jobs", concept_statement="one bold idea",
                evidence=["licensed & insured"],
            )
        )
    )
    assert single["band_headline"].lower() != single["headline"].lower()


def test_subhead_never_leaks_the_operator_goal() -> None:
    # The raw goal ("drive walk-in visits…") is internal objective-speak, not customer
    # copy — it must not appear in the hero subhead, which still names the audience + proof.
    copy = generate_conversion_copy(
        _packet("drive walk-in visits and online pickup orders", evidence=["wild-caught fish"])
    )
    assert "walk-in" not in str(copy["subhead"]).lower()
    assert "homeowners" in str(copy["subhead"])
    assert "wild-caught fish" in str(copy["subhead"]).lower()


def test_section_labels_are_genre_aware() -> None:
    from packages.web.copy import section_labels

    assert section_labels(_packet("orders", category="fish taco restaurant")) == {
        "gallery": "On the menu", "secondary_cta": "See the menu",
    }
    assert section_labels(_packet("book", category="nail salon"))["secondary_cta"] == "Take a look"
    assert section_labels(_packet("quote", category="plumbing")) == {
        "gallery": "The work, up close", "secondary_cta": "See the work",
    }


def test_process_steps_are_genre_aware() -> None:
    from packages.web.copy import process_steps

    heading, steps = process_steps(_packet("book consultations", category="med spa"))
    assert heading == "What to expect"
    assert steps[0][0] == "Consultation"  # a calm consult flow, not trades scope-and-do
    d_heading, d_steps = process_steps(_packet("win work", category="plumbing"))
    assert d_heading == "How it goes"
    assert d_steps[0][0] == "Reach out"


def test_derive_content_real_titles_genre_heading_no_goal_leak_live_cta() -> None:
    from packages.web.blocks_composer import derive_content

    content = derive_content(
        _packet(
            "drive walk-in visits and online pickup orders",
            category="fish taco restaurant",
            evidence=["beer-battered wild-caught fish", "hand-pressed tortillas"],
        )
    )
    titles = [it["title"] for it in content["bento"]["items"]]
    assert all(not t.startswith("Detail ") for t in titles)  # real proof, not "Detail N"
    assert titles[0] == "Beer-battered wild-caught fish"
    assert content["bento"]["heading"] == "On the menu"  # genre-aware, not "The work, up close"
    assert "walk-in" not in str(content["split"]["body"]).lower()  # goal not leaked into copy
    assert content["cta"]["href"] == "#get-started"  # a valid anchor, never href="#"
