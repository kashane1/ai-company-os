"""Phase 2.3 — GTM artifact chain validator.

Checks that a product's GTM artifacts exist, are non-empty, and link
together. The morning briefing (Phase 4.1) calls this every weekday.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_FILES = (
    "voice.md",
    "campaign-calendar.md",
    "content-backlog.md",
    "hook-library.md",
    "hashtag-strategy.md",
    "performance-log.md",
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
    backlog = gtm_dir / "content-backlog.md"
    if backlog.exists():
        for line in backlog.read_text().splitlines():
            if line.strip().startswith(tuple(f"{i}." for i in range(1, 100))):
                backlog_count += 1
        if backlog_count < MIN_BACKLOG_ITEMS:
            failures.append(
                f"content-backlog has {backlog_count} items; need {MIN_BACKLOG_ITEMS}"
            )

    perf = gtm_dir / "performance-log.md"
    if perf.exists():
        if PERFORMANCE_LOG_HEADER not in perf.read_text():
            failures.append("performance-log header does not match expected columns")

    ok = not missing and not empty and not failures
    return GtmChainResult(
        product_id=product_id,
        ok=ok,
        missing=tuple(missing),
        empty=tuple(empty),
        backlog_count=backlog_count,
        failures=tuple(failures),
    )
