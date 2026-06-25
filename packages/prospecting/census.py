"""Prospect census: a one-shot audit of every prospect grouped by state.

Unlike the per-run cohort report (``report.py``), this summarizes the WHOLE
warehouse at once — by source, by cohort (with a verified/unverified split), by
verification method and verdict, and a "ready to build" rollup of verified
no-website targets with their contactability. Pure functions so it is testable
and reusable from the CLI or a skill.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from packages.schemas.prospect import ProspectRecord, WebVerifyVerdict

# Verdicts that make a record a buildable WaaS target (no real owned site).
TARGET_VERDICTS = {
    WebVerifyVerdict.NONE_FOUND,
    WebVerifyVerdict.SOCIAL_ONLY,
    WebVerifyVerdict.MARKETPLACE_ONLY,
}


def _source_of(record: ProspectRecord) -> str:
    return record.source_name or "google_places"


def _is_verified(record: ProspectRecord) -> bool:
    return bool(record.web_verify_method)


def _has_digital_contact(record: ProspectRecord) -> bool:
    return bool(
        record.contact_email
        or record.contact_instagram
        or record.contact_facebook
        or record.contact_booking_url
    )


@dataclass(frozen=True)
class CohortState:
    cohort: str
    total: int = 0
    verified: int = 0
    unverified: int = 0


@dataclass(frozen=True)
class TargetRollup:
    cohort: str
    source: str
    targets: int = 0
    with_phone: int = 0
    with_digital_contact: int = 0


@dataclass(frozen=True)
class Census:
    total: int
    by_source: dict[str, int] = field(default_factory=dict)
    by_cohort: list[CohortState] = field(default_factory=list)
    by_method: dict[str, int] = field(default_factory=dict)
    verified_verdicts: dict[str, int] = field(default_factory=dict)
    ready_to_build: list[TargetRollup] = field(default_factory=list)


def build_census(records: list[ProspectRecord]) -> Census:
    by_source = Counter(_source_of(r) for r in records)
    by_method = Counter(r.web_verify_method or "(unverified)" for r in records)
    verified_verdicts = Counter(
        r.web_verify_verdict.value for r in records if _is_verified(r)
    )

    cohort_total: Counter[str] = Counter()
    cohort_verified: Counter[str] = Counter()
    for r in records:
        cohort = r.composite_cohort or "(none)"
        cohort_total[cohort] += 1
        if _is_verified(r):
            cohort_verified[cohort] += 1
    by_cohort = [
        CohortState(
            cohort=cohort,
            total=cohort_total[cohort],
            verified=cohort_verified[cohort],
            unverified=cohort_total[cohort] - cohort_verified[cohort],
        )
        for cohort, _ in cohort_total.most_common()
    ]

    rollup: dict[tuple[str, str], dict[str, int]] = {}
    for r in records:
        if not _is_verified(r) or r.web_verify_verdict not in TARGET_VERDICTS:
            continue
        key = (r.composite_cohort or "(none)", _source_of(r))
        bucket = rollup.setdefault(key, {"targets": 0, "phone": 0, "contact": 0})
        bucket["targets"] += 1
        if r.phone:
            bucket["phone"] += 1
        if _has_digital_contact(r):
            bucket["contact"] += 1
    ready_to_build = [
        TargetRollup(
            cohort=cohort,
            source=source,
            targets=b["targets"],
            with_phone=b["phone"],
            with_digital_contact=b["contact"],
        )
        for (cohort, source), b in sorted(rollup.items(), key=lambda kv: -kv[1]["targets"])
    ]

    return Census(
        total=len(records),
        by_source=dict(by_source.most_common()),
        by_cohort=by_cohort,
        by_method=dict(by_method.most_common()),
        verified_verdicts=dict(verified_verdicts.most_common()),
        ready_to_build=ready_to_build,
    )


def render_census(census: Census) -> str:
    lines = [
        "# Prospect Census",
        "",
        f"Total prospects: {census.total}",
        "",
        "## By source",
        "",
        "| source | count |",
        "|---|---:|",
    ]
    lines += [f"| {k} | {v} |" for k, v in census.by_source.items()]

    lines += [
        "",
        "## By cohort (verified / unverified)",
        "",
        "| cohort | total | verified | unverified |",
        "|---|---:|---:|---:|",
    ]
    lines += [
        f"| {c.cohort} | {c.total} | {c.verified} | {c.unverified} |" for c in census.by_cohort
    ]

    lines += ["", "## By verification method", "", "| method | count |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in census.by_method.items()]

    lines += ["", "## Verified verdicts", "", "| verdict | count |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in census.verified_verdicts.items()]

    lines += [
        "",
        "## Ready to build (verified no-website targets)",
        "",
        "| cohort | source | targets | w/ phone | w/ digital contact |",
        "|---|---|---:|---:|---:|",
    ]
    if census.ready_to_build:
        lines += [
            f"| {t.cohort} | {t.source} | {t.targets} | {t.with_phone} | {t.with_digital_contact} |"
            for t in census.ready_to_build
        ]
    else:
        lines.append("| none | none | 0 | 0 | 0 |")

    return "\n".join(lines) + "\n"
