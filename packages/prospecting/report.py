"""Markdown reports for prospect cohorts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.schemas.prospect import ProspectRecord


def default_report_path(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).artifacts_root / "prospecting" / "phase1-cohort-report.md"


def default_phase2_report_path(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).artifacts_root / "prospecting" / "phase2-cohort-report.md"


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


def render_phase2_cohort_report(
    records: list[ProspectRecord],
    *,
    before_counts: dict[str, int] | None = None,
    exported_count: int = 0,
) -> str:
    before = before_counts or {}
    after = Counter(record.composite_cohort or "Z_needs_review" for record in records)
    a_gold_by_genre = Counter(
        record.genre_id for record in records if record.composite_cohort == "A_gold"
    )
    score_buckets = _score_buckets(records)
    z_records = [record for record in records if record.composite_cohort == "Z_needs_review"]
    lines = [
        "# Prospecting Phase 2 Cohort Report",
        "",
        f"Records: {len(records)}",
        f"Exported cohort-A rows: {exported_count}",
        f"A_gold target: 50",
        f"A_gold actual: {after.get('A_gold', 0)}",
        f"A_gold target status: {'met' if after.get('A_gold', 0) >= 50 else 'shortfall'}",
        "",
        "## Cohort Counts Before/After Z Reduction",
        "",
        "| stage | composite_cohort | count |",
        "|---|---|---:|",
    ]
    for cohort, count in sorted(before.items()):
        lines.append(f"| before | {cohort} | {count} |")
    for cohort, count in sorted(after.items()):
        lines.append(f"| after | {cohort} | {count} |")

    lines.extend(["", "## Top Genres By A_gold", "", "| genre_id | A_gold_count |", "|---|---:|"])
    for genre, count in a_gold_by_genre.most_common(10):
        lines.append(f"| {genre} | {count} |")
    if not a_gold_by_genre:
        lines.append("| none | 0 |")

    lines.extend(
        ["", "## Priority Score Distribution", "", "| score_bucket | count |", "|---|---:|"]
    )
    for bucket, count in score_buckets.items():
        lines.append(f"| {bucket} | {count} |")

    lines.extend(
        [
            "",
            "## Remaining Z and Why",
            "",
            "| place_id | display_name | maps_website_class | http_check_class | reason |",
            "|---|---|---|---|---|",
        ]
    )
    for record in z_records:
        reason = record.last_error or record.http_skip_reason or "ambiguous website signal"
        lines.append(
            "| "
            + " | ".join(
                [
                    record.place_id,
                    record.display_name,
                    record.maps_website_class.value,
                    record.http_check_class.value,
                    reason.replace("\n", " "),
                ]
            )
            + " |"
        )
    if not z_records:
        lines.append("| none | none | none | none | all records resolved by Phase 2 classifier/backfill |")
    return "\n".join(lines) + "\n"


def write_phase2_cohort_report(
    records: list[ProspectRecord],
    *,
    before_counts: dict[str, int] | None = None,
    exported_count: int = 0,
    path: Path | None = None,
) -> Path:
    target = path or default_phase2_report_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        render_phase2_cohort_report(
            records, before_counts=before_counts, exported_count=exported_count
        )
    )
    return target


def parse_phase1_cohort_counts(path: Path | None = None) -> dict[str, int]:
    source = path or default_report_path()
    if not source.exists():
        return {}
    counts: dict[str, int] = {}
    in_counts = False
    for line in source.read_text().splitlines():
        if line == "## Cohort Counts":
            in_counts = True
            continue
        if in_counts and line.startswith("## "):
            break
        if not in_counts or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2 or cells[0] in {"composite_cohort", "---"}:
            continue
        counts[cells[0]] = int(cells[1])
    return counts


def _score_buckets(records: list[ProspectRecord]) -> dict[str, int]:
    buckets = {
        "0": 0,
        "0.01-25": 0,
        "25.01-50": 0,
        "50.01-75": 0,
        "75.01-100": 0,
    }
    for record in records:
        score = record.priority_score
        if score <= 0:
            buckets["0"] += 1
        elif score <= 25:
            buckets["0.01-25"] += 1
        elif score <= 50:
            buckets["25.01-50"] += 1
        elif score <= 75:
            buckets["50.01-75"] += 1
        else:
            buckets["75.01-100"] += 1
    return buckets
