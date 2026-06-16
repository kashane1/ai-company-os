"""Unit tests for the immigration-paperwork integrity gate."""

from __future__ import annotations

from packages.prospecting.integrity_gates import (
    evaluate_immigration_paperwork,
    evaluate_record,
    evaluate_record_for_exclusion,
)


def test_catches_named_immigration_consultant():
    # The real Rodelas case: "Immigration Consultant" in the name.
    result = evaluate_immigration_paperwork(
        "Rodelas Immigration Consultant", types=["consultant"], genre_id="notary"
    )
    assert result.matched is True
    assert "immigration" in result.terms


def test_catches_spanish_notario():
    result = evaluate_immigration_paperwork("Notario Público 27", genre_id="notary")
    assert result.matched is True
    assert "notario/notaría" in result.terms


def test_catches_accent_stripped_inmigracion():
    result = evaluate_immigration_paperwork(
        "Servicios De Inmigración", genre_id="notary"
    )
    assert result.matched is True
    assert "inmigración" in result.terms


def test_leaves_legitimate_english_notary_alone():
    # The legit El Paso Notary Public (3.9) that WAS built claim-light: English
    # "Notary", not "notario", and no immigration term.
    result = evaluate_immigration_paperwork(
        "El Paso Notary Public", types=["consultant", "finance"], genre_id="notary"
    )
    assert result.matched is False


def test_excludes_attorney_law_firm():
    # A regulated immigration attorney is out of scope for this gate.
    result = evaluate_immigration_paperwork(
        "Garcia Immigration Law Firm", types=["lawyer"], genre_id="lawyer"
    )
    assert result.matched is False
    assert result.is_attorney is True


def test_no_false_positive_on_asylum_food_pod():
    # "Asylum" as a place name on a restaurant must NOT fire.
    result = evaluate_immigration_paperwork(
        "Hawthorne Asylum Food Cart Pod", genre_id="restaurant"
    )
    assert result.matched is False


def test_no_false_positive_on_spanish_sports():
    # "Deportes" (sports) must NOT match the deportation pattern.
    result = evaluate_immigration_paperwork("Deportes Hernandez", genre_id="store")
    assert result.matched is False


def test_evaluate_record_pulls_fields():
    record = {
        "display_name": "Supreme Immigration LLC",
        "types": ["point_of_interest"],
        "genre_id": "notary",
    }
    result = evaluate_record(record)
    assert result.matched is True
    assert "non-attorney immigration-paperwork" in result.reason()


def test_exclusion_requires_sub_4_rating():
    # Rodelas: immigration name + 3.5 rating -> excluded.
    record = {"display_name": "Rodelas Immigration Consultant", "rating": 3.5}
    assert evaluate_record_for_exclusion(record).matched is True


def test_exclusion_spares_high_rated_immigration_name():
    # 4.7/527 passport-photo shop: immigration name but high rating -> spared.
    record = {
        "display_name": "Passport Immigration Photos and Fingerprinting Services",
        "rating": 4.7,
    }
    result = evaluate_record_for_exclusion(record)
    assert result.matched is False
    assert "immigration" in result.terms  # still detected, just not excluded


def test_exclusion_spares_unrated_source_candidate():
    # Unverified Overture notaría with no rating yet -> not auto-excluded.
    record = {"display_name": "Notaría Pública No. 9", "rating": None}
    assert evaluate_record_for_exclusion(record).matched is False


def test_exclusion_at_threshold_boundary():
    # Exactly 4.0 is not "below 4.0" -> spared.
    record = {"display_name": "Servicios De Inmigración", "rating": 4.0}
    assert evaluate_record_for_exclusion(record).matched is False
    record_below = {"display_name": "Servicios De Inmigración", "rating": 3.9}
    assert evaluate_record_for_exclusion(record_below).matched is True
