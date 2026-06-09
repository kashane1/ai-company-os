"""Tests for the Design Studio orchestration entrypoint.

`packages/web/design_studio.py` is the pure contract. This entrypoint is the
plumbing that makes it usable on a real build: it turns a spec into a persisted
packet, captures desktop/mobile screenshots, ingests rubric scores, and writes a
visual-review report under the build's own hub. These tests lock that plumbing
without shelling out to a browser.
"""

from __future__ import annotations

import json

from scripts.agency.design_studio import (
    load_packet,
    premium_ready,
    request_from_spec,
    run_review,
    scores_from_payload,
    shoot_commands,
    studio_dir,
    studio_status,
    write_packet,
)

SPEC = {
    "site_name": "TrueLine Plumbing",
    "business_category": "plumbing",
    "audience": "homeowners who want calm, precise service",
    "goal": "sell a high-trust preview site",
    "evidence": ["reviews praise careful cleanup and clear quotes"],
    "visual_assets": ["owner logo", "two usable work photos"],
    "imagery_mode": "concept-led",
    "references": [
        {
            "title": "B2B SaaS Landing Page Design for HackerRank",
            "url": "https://dribbble.com/shots/26414267",
            "source_type": "dribbble",
            "takeaways": ["large device-frame hero", "single strong visual thesis"],
        }
    ],
}

STRONG_SCORES = [
    {"category": "visual_thesis", "score": 5, "note": "concept carries the page"},
    {"category": "hero_impact", "score": 5, "note": "presentation-worthy hero"},
    {"category": "imagery_art_direction", "score": 4, "note": "cohesive set"},
    {"category": "typography", "score": 4, "note": "distinctive display"},
    {"category": "color_system", "score": 4, "note": "dominant + sharp accent"},
    {"category": "layout_composition", "score": 4, "note": "varied rhythm"},
    {"category": "whitespace_depth", "score": 4, "note": "breathes, real depth"},
    {"category": "motion_quality", "score": 4, "note": "cohesive scroll choreography"},
    {"category": "signature_moment", "score": 4, "note": "memorable hero moment"},
    {"category": "conversion_strength", "score": 4, "note": "clear offer + CTA"},
    {"category": "copy_specificity", "score": 5, "note": "evidence-grounded"},
    {"category": "ai_house_style", "score": 5, "note": "no AI tells"},
]

WEAK_SCORES = [
    {"category": "visual_thesis", "score": 2, "note": "neutral template"},
    {"category": "hero_impact", "score": 3, "note": "forgettable"},
    {"category": "imagery_art_direction", "score": 2, "note": "no system"},
    {"category": "typography", "score": 3, "note": "safe sans"},
    {"category": "color_system", "score": 3, "note": "timid palette"},
    {"category": "layout_composition", "score": 3, "note": "uniform cards"},
    {"category": "whitespace_depth", "score": 2, "note": "flat, coplanar"},
    {"category": "motion_quality", "score": 2, "note": "no real motion"},
    {"category": "signature_moment", "score": 2, "note": "nothing memorable"},
    {"category": "conversion_strength", "score": 3, "note": "buried CTA"},
    {"category": "copy_specificity", "score": 4, "note": "grounded enough"},
    {"category": "ai_house_style", "score": 2, "note": "aurora + 3-icon grid"},
]


def test_request_from_spec_builds_request_with_references() -> None:
    request = request_from_spec(SPEC)

    assert request.site_name == "TrueLine Plumbing"
    assert request.imagery_mode == "concept-led"
    assert len(request.references) == 1
    assert request.references[0].title.startswith("B2B SaaS")
    assert request.references[0].takeaways[0] == "large device-frame hero"


def test_write_and_load_packet_round_trips(tmp_path) -> None:
    path = write_packet(tmp_path, request_from_spec(SPEC))

    assert path == studio_dir(tmp_path) / "packet.json"
    assert path.exists()
    assert (studio_dir(tmp_path) / "packet.md").exists()

    packet = load_packet(tmp_path)
    assert packet.site_name == "TrueLine Plumbing"
    assert packet.archetype == "service-area-cinematic"


def test_status_reports_missing_screenshots_before_capture(tmp_path) -> None:
    write_packet(tmp_path, request_from_spec(SPEC))

    status = studio_status(tmp_path)

    assert status["has_packet"] is True
    assert status["screenshots"] == {"desktop": False, "mobile": False}
    assert status["reviewed"] is False
    assert status["passed"] is False


def test_run_review_passes_with_strong_scores_and_both_screenshots(tmp_path) -> None:
    write_packet(tmp_path, request_from_spec(SPEC))
    shots = studio_dir(tmp_path) / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    (shots / "desktop.png").write_bytes(b"x")
    (shots / "mobile.png").write_bytes(b"x")

    report = run_review(tmp_path, scores_from_payload(STRONG_SCORES))

    assert report.passed is True
    assert report.overall >= 80
    review_json = json.loads((studio_dir(tmp_path) / "visual-review.json").read_text())
    assert review_json["passed"] is True
    assert (studio_dir(tmp_path) / "review.md").exists()
    assert studio_status(tmp_path)["passed"] is True


def test_run_review_fails_weak_page_even_with_screenshots(tmp_path) -> None:
    write_packet(tmp_path, request_from_spec(SPEC))
    shots = studio_dir(tmp_path) / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    (shots / "desktop.png").write_bytes(b"x")
    (shots / "mobile.png").write_bytes(b"x")

    report = run_review(tmp_path, scores_from_payload(WEAK_SCORES))

    assert report.passed is False
    assert "design_studio_no_visual_thesis" in report.failure_codes


def test_run_review_flags_missing_mobile_when_only_desktop_present(tmp_path) -> None:
    write_packet(tmp_path, request_from_spec(SPEC))
    shots = studio_dir(tmp_path) / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    (shots / "desktop.png").write_bytes(b"x")

    report = run_review(tmp_path, scores_from_payload(STRONG_SCORES))

    assert report.passed is False
    assert "design_studio_missing_mobile_screenshot" in report.failure_codes


def test_premium_ready_guard_ignores_non_premium_builds(tmp_path) -> None:
    # No packet → never elected the premium track → never blocked.
    assert premium_ready(tmp_path) is True


def test_premium_ready_guard_blocks_unreviewed_premium_build(tmp_path) -> None:
    write_packet(tmp_path, request_from_spec(SPEC))  # joins the premium track
    assert premium_ready(tmp_path) is False  # but no passing review yet

    shots = studio_dir(tmp_path) / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    (shots / "desktop.png").write_bytes(b"x")
    (shots / "mobile.png").write_bytes(b"x")
    run_review(tmp_path, scores_from_payload(STRONG_SCORES))
    assert premium_ready(tmp_path) is True


def test_premium_ready_blocks_on_uncleared_generated_imagery(tmp_path) -> None:
    from packages.web.imagery import ImageAsset, ImageryManifest

    # A passing premium build...
    write_packet(tmp_path, request_from_spec(SPEC))
    shots = studio_dir(tmp_path) / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    (shots / "desktop.png").write_bytes(b"x")
    (shots / "mobile.png").write_bytes(b"x")
    run_review(tmp_path, scores_from_payload(STRONG_SCORES))
    assert premium_ready(tmp_path) is True

    # ...is blocked once it carries an uncleared generated image.
    manifest = studio_dir(tmp_path) / "imagery" / "manifest.json"
    ImageryManifest(
        assets=[ImageAsset(id="hero", role="hero", path="a", provenance="generated")]
    ).save(manifest)
    assert premium_ready(tmp_path) is False

    # ...and ready again once the founder clears it.
    ImageryManifest(
        assets=[
            ImageAsset(id="hero", role="hero", path="a", provenance="generated",
                       production_clearance=True, cleared_by="founder")
        ]
    ).save(manifest)
    assert premium_ready(tmp_path) is True


def test_shoot_commands_cover_desktop_and_mobile_widths(tmp_path) -> None:
    commands = shoot_commands("/some/dist", tmp_path)

    widths = [cmd["width"] for cmd in commands]
    names = sorted(cmd["name"] for cmd in commands)
    assert names == ["desktop", "mobile"]
    assert 1440 in widths and 390 in widths
    # every command targets the studio screenshots dir
    for cmd in commands:
        assert str(studio_dir(tmp_path) / "screenshots") in cmd["argv"]
        assert "--width" in cmd["argv"]
