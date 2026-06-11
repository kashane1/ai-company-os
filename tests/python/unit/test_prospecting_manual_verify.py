from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from packages.prospecting.manual_verify import (
    export_contact_worklist,
    export_manual_worklist,
    ingest_manual_contacts,
    ingest_manual_results,
)
from packages.prospecting.storage import ProspectRepository
from packages.schemas.prospect import (
    HttpCheckClass,
    MapsWebsiteClass,
    ProspectRecord,
    WebVerifyVerdict,
)

FIXED = datetime(2026, 6, 10, 12, tzinfo=timezone.utc)


def _source_candidate(place_id: str, *, name: str = "", reviews: int = 0) -> ProspectRecord:
    return ProspectRecord(
        place_id=place_id,
        display_name=name or f"Business {place_id}",
        formatted_address="Austin, TX 78701, USA",
        phone="+1 512-555-0100",
        types=["beauty_salon"],
        city_id="austin",
        genre_id="beauty_salon",
        grid_cell_id="austin:beauty_salon",
        maps_website_class=MapsWebsiteClass.ABSENT,
        user_ratings_total=reviews,
        http_check_class=HttpCheckClass.SKIPPED,
        composite_cohort="S_source_candidate",
        priority_score=30.0,
        source_name="overture",
        web_verify_verdict=WebVerifyVerdict.UNVERIFIED,
    )


def test_export_selects_only_unverified_in_cohort_sorted_by_priority() -> None:
    records = [
        _source_candidate("places/low"),
        _source_candidate("places/high"),
        # Already verified -> excluded.
        ProspectRecord.from_dict(
            {
                **_source_candidate("places/done").to_dict(),
                "web_verify_verdict": WebVerifyVerdict.MARKETPLACE_ONLY.value,
            }
        ),
        # Different cohort -> excluded.
        ProspectRecord.from_dict(
            {**_source_candidate("places/other").to_dict(), "composite_cohort": "A_gold"}
        ),
    ]
    # Make "high" sort first.
    records[1] = ProspectRecord.from_dict(
        {**records[1].to_dict(), "priority_score": 99.0}
    )

    worklist = export_manual_worklist(
        records, cohort="S_source_candidate", limit=10, shard=0, shard_count=1
    )

    assert [row["place_id"] for row in worklist] == ["places/high", "places/low"]
    first = worklist[0]
    # Worklist carries the search query + maps url + blank slots for the agent.
    assert first["search_query"]
    # Source candidates have no Google place id, so the maps link is a plain
    # name+address text search (no unresolvable query_place_id).
    assert "google.com/maps/search" in str(first["maps_url"])
    assert "query_place_id=" not in str(first["maps_url"])
    assert first["results"] == []
    assert first["review_count"] is None
    assert set(first["contacts"]) == {"email", "instagram", "facebook", "booking_url"}


def test_sharding_is_disjoint_and_exhaustive() -> None:
    records = [_source_candidate(f"places/biz-{i}") for i in range(60)]
    shard_count = 4

    seen: list[str] = []
    for shard in range(shard_count):
        worklist = export_manual_worklist(
            records,
            cohort="S_source_candidate",
            limit=1000,
            shard=shard,
            shard_count=shard_count,
        )
        seen.extend(str(row["place_id"]) for row in worklist)

    # Every record appears exactly once across all shards.
    assert sorted(seen) == sorted(r.place_id for r in records)
    assert len(seen) == len(set(seen))


def test_ingest_classifies_marketplace_and_writes_contact(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    repo.save(_source_candidate("places/tonic", name="Tonic Salon"))

    result = ingest_manual_results(
        repo,
        [
            {
                "place_id": "places/tonic",
                "results": [
                    {
                        "title": "Tonic Salon - Yelp",
                        "url": "https://www.yelp.com/biz/tonic-salon-austin",
                        "description": "Book at Tonic Salon",
                    }
                ],
                "review_count": 40,
                "contacts": {"instagram": "@tonicsalon", "email": "hi@tonicsalon.com"},
            }
        ],
        now=lambda: FIXED,
    )

    assert result.checked == 1
    assert result.verdict_counts == {WebVerifyVerdict.MARKETPLACE_ONLY.value: 1}
    saved = repo.get("places/tonic")
    assert saved.web_verify_verdict is WebVerifyVerdict.MARKETPLACE_ONLY
    assert saved.web_verify_method == "manual_browser"
    assert saved.contact_instagram == "@tonicsalon"
    assert saved.contact_email == "hi@tonicsalon.com"
    assert saved.contact_source == "manual_browser"
    assert saved.contact_collected_at == FIXED.isoformat()


def test_ingest_review_count_promotes_source_candidate_to_a_gold(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    repo.save(_source_candidate("places/grow", name="Cactus Barber"))

    result = ingest_manual_results(
        repo,
        [
            {
                "place_id": "places/grow",
                "results": [],  # nothing found -> none_found
                "review_count": 40,
            }
        ],
        now=lambda: FIXED,
    )

    assert result.promoted == ["places/grow"]
    saved = repo.get("places/grow")
    assert saved.user_ratings_total == 40
    assert saved.composite_cohort == "A_gold"
    assert saved.web_verify_verdict is WebVerifyVerdict.NONE_FOUND


def test_owned_site_verdict_lands_in_e_has_site_not_a_gold(tmp_path: Path) -> None:
    # A browsed-and-dropped source candidate (e.g. a closed restaurant with a high
    # review count, or one with a real site) must not recompute into A_gold off its
    # reviews — the owned_site verdict pins it to the deprioritized has-site bucket.
    repo = ProspectRepository(tmp_path / "records")
    repo.save(_source_candidate("places/closed", name="Old Diner"))

    ingest_manual_results(
        repo,
        [
            {
                "place_id": "places/closed",
                "verdict_override": "owned_site",
                "review_count": 899,
                "note": "PERMANENTLY CLOSED; had owned site",
            }
        ],
        now=lambda: FIXED,
    )

    saved = repo.get("places/closed")
    assert saved.web_verify_verdict is WebVerifyVerdict.OWNED_SITE
    assert saved.user_ratings_total == 899
    assert saved.composite_cohort == "E_has_site"


def test_ingest_honors_verdict_override(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    repo.save(_source_candidate("places/franchise", name="Generic Plumbing Co"))

    result = ingest_manual_results(
        repo,
        [
            {
                "place_id": "places/franchise",
                "results": [{"title": "x", "url": "https://example.com", "description": ""}],
                "verdict_override": "owned_site",
                "verdict_url": "https://genericplumbing.com",
                "note": "found owned site classifier missed",
            }
        ],
        now=lambda: FIXED,
    )

    assert result.checked == 1
    saved = repo.get("places/franchise")
    assert saved.web_verify_verdict is WebVerifyVerdict.OWNED_SITE
    assert saved.web_verify_url == "https://genericplumbing.com"
    assert saved.web_verify_note == "found owned site classifier missed"


def test_ingest_reports_missing_and_skipped(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    repo.save(_source_candidate("places/real", name="Real Spa"))

    result = ingest_manual_results(
        repo,
        [
            {"place_id": "", "results": []},  # skipped (no id)
            {"place_id": "places/ghost", "results": []},  # missing
            {"place_id": "places/real", "results": []},
        ],
        now=lambda: FIXED,
    )

    assert result.skipped == 1
    assert result.missing == ["places/ghost"]
    assert result.checked == 1


def _verified_target(
    place_id: str, *, verdict: str, name: str = "", contact: str = ""
) -> ProspectRecord:
    return ProspectRecord.from_dict(
        {
            **_source_candidate(place_id, name=name, reviews=120).to_dict(),
            "web_verify_verdict": verdict,
            "web_verify_url": "https://www.yelp.com/biz/x",
            "composite_cohort": "A2_marketplace_review",
            "contact_instagram": contact,
        }
    )


def test_contact_export_selects_verified_targets_missing_a_digital_contact() -> None:
    records = [
        _verified_target("places/need", verdict="marketplace_only", name="Need Contact"),
        _verified_target("places/have", verdict="marketplace_only", contact="@already"),
        _verified_target("places/owned", verdict="owned_site", name="Has Site"),
        _source_candidate("places/unverified"),  # not verified yet -> excluded
    ]
    rows = export_contact_worklist(records, limit=10)
    ids = [r["place_id"] for r in rows]
    assert ids == ["places/need"]
    row = rows[0]
    assert row["known_url"] == "https://www.yelp.com/biz/x"  # agent's starting point
    assert set(row["contacts"]) == {"email", "instagram", "facebook", "booking_url"}
    assert "web_verify_verdict" in row and "results" not in row


def test_contact_export_can_restrict_to_an_id_set() -> None:
    records = [
        _verified_target("places/a", verdict="marketplace_only"),
        _verified_target("places/b", verdict="social_only"),
    ]
    rows = export_contact_worklist(records, ids={"places/b"}, limit=10)
    assert [r["place_id"] for r in rows] == ["places/b"]


def test_ingest_contacts_only_writes_contacts_and_preserves_verdict(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    repo.save(_verified_target("places/keep", verdict="marketplace_only", name="Keep Verdict"))

    result = ingest_manual_contacts(
        repo,
        [
            {
                "place_id": "places/keep",
                "contacts": {"email": "owner@keep.com", "instagram": "@keep"},
            }
        ],
        now=lambda: FIXED,
    )

    assert result.updated == 1
    saved = repo.get("places/keep")
    assert saved.contact_email == "owner@keep.com"
    assert saved.contact_instagram == "@keep"
    assert saved.contact_source == "manual_browser"
    # Verdict, cohort, and reviews are untouched by the contacts-only path.
    assert saved.web_verify_verdict is WebVerifyVerdict.MARKETPLACE_ONLY
    assert saved.composite_cohort == "A2_marketplace_review"
    assert saved.user_ratings_total == 120


def test_ingest_contacts_only_marks_channel_less_rows_attempted(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    repo.save(_verified_target("places/x", verdict="marketplace_only"))
    result = ingest_manual_contacts(
        repo,
        [
            {"place_id": "places/x", "contacts": {"email": "", "instagram": ""}},  # nothing found
            {"place_id": "places/ghost", "contacts": {"email": "a@b.com"}},  # missing
        ],
        now=lambda: FIXED,
    )
    assert result.updated == 0
    assert result.attempted == 1  # browsed + stamped, even with no channel
    assert result.skipped == 0
    assert result.missing == ["places/ghost"]
    # The attempted row is stamped checked but keeps no digital contact...
    saved = repo.get("places/x")
    assert saved.contact_checked_at == FIXED.isoformat()
    assert not saved.contact_email and not saved.contact_instagram
    # ...so it drops out of the next worklist instead of re-selecting forever.
    assert export_contact_worklist([saved], limit=10) == []


def test_ingest_contacts_only_skips_rows_without_a_place_id(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    result = ingest_manual_contacts(
        repo,
        [{"contacts": {"email": "a@b.com"}}],  # no place_id at all
        now=lambda: FIXED,
    )
    assert result.updated == 0
    assert result.attempted == 0
    assert result.skipped == 1


def test_invalid_verdict_override_is_an_error_not_a_crash(tmp_path: Path) -> None:
    repo = ProspectRepository(tmp_path / "records")
    repo.save(_source_candidate("places/bad", name="Bad Verdict"))

    result = ingest_manual_results(
        repo,
        [{"place_id": "places/bad", "verdict_override": "definitely_a_site"}],
        now=lambda: FIXED,
    )

    assert result.checked == 0
    assert result.errors and "places/bad" in result.errors[0]
