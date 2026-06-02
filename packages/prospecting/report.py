"""Markdown reports for prospect cohorts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.schemas.prospect import ProspectRecord


def default_report_path(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).artifacts_root / "prospecting" / "phase1-cohort-report.md"


def render_cohort_report(records: list[ProspectRecord]) -> str:
    cohort_counts = Counter(record.composite_cohort or "Z_needs_review" for record in records)
    city_counts = Counter(record.city_id for record in records)
    genre_counts = Counter(record.genre_id for record in records)
    cell_a_gold = Counter(
        record.grid_cell_id for record in records if record.composite_cohort == "A_gold"
    )
    lines = [
        "# Prospecting Phase 1 Cohort Report",
        "",
        f"Records: {len(records)}",
        "",
        "## Cohort Counts",
        "",
        "| composite_cohort | count |",
        "|---|---:|",
    ]
    for cohort, count in sorted(cohort_counts.items()):
        lines.append(f"| {cohort} | {count} |")
    lines.extend(["", "## City Counts", "", "| city_id | count |", "|---|---:|"])
    for city, count in sorted(city_counts.items()):
        lines.append(f"| {city} | {count} |")
    lines.extend(["", "## Genre Counts", "", "| genre_id | count |", "|---|---:|"])
    for genre, count in sorted(genre_counts.items()):
        lines.append(f"| {genre} | {count} |")
    lines.extend(
        [
            "",
            "## Top 10 City x Genre Cells By A_gold Count",
            "",
            "| cell | A_gold_count |",
            "|---|---:|",
        ]
    )
    for cell, count in cell_a_gold.most_common(10):
        lines.append(f"| {cell} | {count} |")
    if not cell_a_gold:
        lines.append("| none | 0 |")
    return "\n".join(lines) + "\n"


def write_cohort_report(records: list[ProspectRecord], path: Path | None = None) -> Path:
    target = path or default_report_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_cohort_report(records))
    return target

