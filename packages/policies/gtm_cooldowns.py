"""Phase 2.0/2.4 — per-platform cooldown and per-day quota caps.

The GTM worker honors this table before calling Postiz or Gemini. Cooldowns
prevent account-warming violations; Gemini quotas prevent runaway spend.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class PlatformCooldown:
    platform: str
    min_gap: timedelta
    max_posts_per_day: int


PLATFORM_COOLDOWNS: dict[str, PlatformCooldown] = {
    "tiktok": PlatformCooldown("tiktok", timedelta(hours=4), 3),
    "instagram": PlatformCooldown("instagram", timedelta(hours=3), 4),
    "threads": PlatformCooldown("threads", timedelta(hours=2), 6),
    "x": PlatformCooldown("x", timedelta(minutes=45), 10),
}


# Gemini image-gen daily budget (requests).
GEMINI_DAILY_IMAGE_BUDGET = 60


def cooldown_for(platform: str) -> PlatformCooldown:
    try:
        return PLATFORM_COOLDOWNS[platform]
    except KeyError as exc:
        raise ValueError(f"unknown platform {platform!r}") from exc
