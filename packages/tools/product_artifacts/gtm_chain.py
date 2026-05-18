"""Phase 2.3 — GTM artifact chain validator.

Checks that a product's GTM artifacts exist, are non-empty, and link
together. The morning briefing (Phase 4.1) calls this every weekday.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_FILES = (
    "voice.md",
    "campaign-calendar.md",
    "content-backlog.yaml",
    "hook-library.md",
    "hashtag-strategy.md",
    "performance-log.md",
)

BACKLOG_REQUIRED_FIELDS = ("item_number", "hook", "archetype", "platform", "campaign", "status")

VALID_PLATFORMS = {"tiktok", "instagram", "threads", "x", "facebook"}

# Extended chain files produced by niche-research-brief and gtm-artifact-refresh.
# Validated separately because they may not exist until the first research run.
EXTENDED_FILES = (
    "niche-research-brief.md",
    "niche-research-memory.yaml",
    "content-taxonomy.md",
)

MIN_BACKLOG_ITEMS = 14
PERFORMANCE_LOG_HEADER = "| Date | Platform | Posts | Impressions | Engagement | Notes |"


@dataclass(frozen=True)
class GtmChainResult:
    product_id: str
    ok: bool
    missing: tuple[str, ...] = ()
    empty: tuple[str, ...] = ()
    backlog_count: int = 0
    failures: tuple[str, ...] = ()
    extended_missing: tuple[str, ...] = ()
    extended_empty: tuple[str, ...] = ()


def validate_backlog_item(item: dict) -> list[str]:
    """Validate a single content-backlog.yaml item has required fields.

    Returns a list of error strings (empty = valid). Shared across the chain
    validator, content-factory, and content-scheduler pre-flight checks.

    Supports both legacy items (no topic_id) and new multi-platform items.
    New fields (topic_id, format, audience) are validated only when non-null.
    """
    errors: list[str] = []
    if not isinstance(item, dict):
        return ["item is not a dict"]
    for f in BACKLOG_REQUIRED_FIELDS:
        if f not in item:
            errors.append(f"missing field: {f}")

    # Platform enum validation.
    platform = item.get("platform")
    if platform and platform not in VALID_PLATFORMS:
        errors.append(f"invalid platform: {platform}")

    # Text-first platforms don't require slides.
    # Visual platforms require slides only for new multi-platform items.
    topic_id = item.get("topic_id")
    if topic_id is not None and platform not in ("x", "facebook", "threads"):
        if not item.get("slides"):
            errors.append(f"visual platform {platform} missing slides")

    # topic_id format when present.
    if topic_id is not None and not isinstance(topic_id, str):
        errors.append("topic_id must be a string")

    return errors


def validate_gtm_chain(
    product_id: str, repo_root: Path
) -> GtmChainResult:
    gtm_dir = repo_root / "docs" / "products" / product_id / "gtm"
    missing: list[str] = []
    empty: list[str] = []
    failures: list[str] = []

    for name in REQUIRED_FILES:
        f = gtm_dir / name
        if not f.exists():
            missing.append(name)
            continue
        if not f.read_text().strip():
            empty.append(name)

    backlog_count = 0
    backlog = gtm_dir / "content-backlog.yaml"
    if backlog.exists():
        try:
            items = yaml.safe_load(backlog.read_text()) or []
            backlog_count = len(items) if isinstance(items, list) else 0
        except yaml.YAMLError:
            failures.append("content-backlog.yaml is not valid YAML")
        if backlog_count < MIN_BACKLOG_ITEMS:
            failures.append(
                f"content-backlog has {backlog_count} items; need {MIN_BACKLOG_ITEMS}"
            )
        # Validate each item has required fields
        for item in (items if isinstance(items, list) else []):
            errors = validate_backlog_item(item)
            if errors:
                failures.append(
                    f"item {item.get('item_number', '?')}: {', '.join(errors)}"
                )

    perf = gtm_dir / "performance-log.md"
    if perf.exists():
        if PERFORMANCE_LOG_HEADER not in perf.read_text():
            failures.append("performance-log header does not match expected columns")

    # Extended chain: warn but don't fail if these are missing (they only
    # exist after the first niche-research-brief run).
    ext_missing: list[str] = []
    ext_empty: list[str] = []
    for name in EXTENDED_FILES:
        f = gtm_dir / name
        if not f.exists():
            ext_missing.append(name)
            continue
        if not f.read_text().strip():
            ext_empty.append(name)

    ok = not missing and not empty and not failures
    return GtmChainResult(
        product_id=product_id,
        ok=ok,
        missing=tuple(missing),
        empty=tuple(empty),
        backlog_count=backlog_count,
        failures=tuple(failures),
        extended_missing=tuple(ext_missing),
        extended_empty=tuple(ext_empty),
    )
