"""Phase 2.0/2.4 — tests for packages/policies/gtm_cooldowns.py."""

from datetime import timedelta

import pytest

from packages.policies.gtm_cooldowns import (
    GEMINI_DAILY_IMAGE_BUDGET,
    PLATFORM_COOLDOWNS,
    cooldown_for,
)


def test_all_platforms_have_positive_caps():
    assert PLATFORM_COOLDOWNS
    for p, cd in PLATFORM_COOLDOWNS.items():
        assert cd.platform == p
        assert cd.min_gap > timedelta(0)
        assert cd.max_posts_per_day > 0


def test_cooldown_for_unknown_platform_raises():
    with pytest.raises(ValueError):
        cooldown_for("bluesky")


def test_gemini_budget_is_bounded():
    assert 0 < GEMINI_DAILY_IMAGE_BUDGET < 1000
