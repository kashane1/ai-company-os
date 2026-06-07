"""Ad-platform vertical eligibility gate."""

from __future__ import annotations

import pytest

from packages.agency.ad_policy import (
    AdPolicyError,
    assert_ad_vertical_allowed,
    check_ad_vertical,
)


def test_firearms_banned_on_both_platforms() -> None:
    for platform in ("google", "meta"):
        level, reason = check_ad_vertical("gun store", platform)
        assert level == "banned"
        assert "firearm" in reason.lower()
    with pytest.raises(AdPolicyError, match="cannot advertise"):
        assert_ad_vertical_allowed("Gun Store & Range", "meta")


def test_alcohol_is_restricted_not_banned() -> None:
    level, reason = check_ad_vertical("liquor store", "google")
    assert level == "restricted"
    assert reason
    # Restricted verticals are runnable with certification → no raise.
    assert_ad_vertical_allowed("liquor store", "google")


def test_ordinary_local_business_is_unrestricted() -> None:
    for cat in ("plumbing", "barber", "med spa", "auto repair", "dog grooming", "bakery"):
        assert check_ad_vertical(cat, "google") == (None, "")
        assert check_ad_vertical(cat, "meta") == (None, "")


def test_barber_is_not_caught_by_bar_keyword() -> None:
    # Guard against the classic false positive: "bar" must not match "barber".
    assert check_ad_vertical("barber shop", "meta") == (None, "")


def test_cannabis_and_vape_banned() -> None:
    assert check_ad_vertical("cannabis dispensary", "meta")[0] == "banned"
    assert check_ad_vertical("vape shop", "google")[0] == "banned"


def test_unknown_platform_raises() -> None:
    with pytest.raises(ValueError, match="unknown ad platform"):
        check_ad_vertical("plumbing", "tiktok")
