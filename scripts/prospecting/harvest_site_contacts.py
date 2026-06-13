#!/usr/bin/env python3
"""Owned-site contact harvester (fix F1) — the CLI + the real (polite) fetcher.

Owned-site teaser prospects are drafts-to-nowhere: only ~9 of 582 teaser rows
carry a digital contact, so a validated teaser + audit pitch has nowhere to land.
These businesses publish their contact details on their own sites; this CLI walks
those sites (or the homepages we already captured) and writes any hit as a
dashboard contact *override* via :meth:`OutreachStore.set_override` — never a
source-record mutation. A teaser row whose ``contact_email`` becomes set is then
launchable in the dashboard (the override overlay enables its email button).

    # Extract from the 580+ homepages we already captured — ZERO network:
    python scripts/prospecting/harvest_site_contacts.py --from-captured --limit 600

    # Live-fetch (polite: robots-aware, 8s timeout, 1.5s delay, <=3 pages/site):
    python scripts/prospecting/harvest_site_contacts.py --limit 50

Guardrails: same-domain only, <=3 pages/site, one polite delay between requests,
at most one retry, robots.txt respected, no JS, no third-party enrichment APIs.
Suppressed prospects are skipped. Nothing is sent.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.outreach_store import (  # noqa: E402
    ALLOWED_OVERRIDE_FIELDS,
    OutreachStore,
)
from packages.agency.teardown_teaser import (  # noqa: E402
    TeaserProspect,
    prospect_from_record,
    select_cohort,
)
from packages.config.settings import load_runtime_paths  # noqa: E402
from packages.prospecting.site_contact_harvest import HarvestResult, harvest_site  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) BetterBusinessWeb-ContactHarvester/1.0 (+contact-discovery)"
)
REQUEST_TIMEOUT_S = 8.0
POLITE_DELAY_S = 1.5
MAX_RETRIES = 1
MAX_BYTES = 1_500_000  # don't slurp giant pages


# ---------------------------------------------------------------- live fetcher
class PoliteFetcher:
    """A same-domain, robots-aware, rate-limited HTTP GET. One instance per run.

    - Fetches ``/robots.txt`` once per host and skips disallowed paths.
    - One ``POLITE_DELAY_S`` sleep *between* requests (not before the first).
    - ``REQUEST_TIMEOUT_S`` per request, at most ``MAX_RETRIES`` retry.
    - Returns decoded text, or ``None`` on any failure / disallow / non-HTML.
    """

    def __init__(self) -> None:
        self._robots: dict[str, RobotFileParser | None] = {}
        self._made_request = False

    def _robots_for(self, url: str) -> RobotFileParser | None:
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        if host in self._robots:
            return self._robots[host]
        parser = RobotFileParser()
        robots_url = urljoin(host + "/", "robots.txt")
        try:
            raw = self._raw_get(robots_url)
            if raw is None:
                parser = None  # couldn't read robots -> don't block on it
            else:
                parser.parse(raw.splitlines())
        except Exception:
            parser = None
        self._robots[host] = parser
        return parser

    def _allowed(self, url: str) -> bool:
        parser = self._robots_for(url)
        if parser is None:
            return True
        try:
            return parser.can_fetch(USER_AGENT, url)
        except Exception:
            return True

    def _raw_get(self, url: str) -> str | None:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        for attempt in range(MAX_RETRIES + 1):
            try:
                with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as resp:
                    ctype = resp.headers.get("Content-Type", "")
                    if ctype and "html" not in ctype and "text" not in ctype:
                        return None
                    data = resp.read(MAX_BYTES)
                charset = "utf-8"
                return data.decode(charset, errors="replace")
            except (urllib.error.URLError, TimeoutError, ValueError, OSError):
                if attempt >= MAX_RETRIES:
                    return None
                time.sleep(POLITE_DELAY_S)
        return None

    def __call__(self, url: str) -> str | None:
        if not url:
            return None
        if not self._allowed(url):
            return None
        if self._made_request:
            time.sleep(POLITE_DELAY_S)  # one polite delay between requests
        self._made_request = True
        return self._raw_get(url)


# ---------------------------------------------------------------- worklist
def _records_root() -> Path:
    return load_runtime_paths(REPO).state_root / "prospects" / "records"


def _sites_root() -> Path:
    return load_runtime_paths(REPO).state_root / "prospects" / "sites"


def _lane_status_path() -> Path:
    return (
        load_runtime_paths(REPO).state_root
        / "prospects"
        / "outreach-lane"
        / "client-status.json"
    )


def _harvest_log_path() -> Path:
    return load_runtime_paths(REPO).state_root / "prospects" / "contact-harvest-log.jsonl"


def _load_records() -> list[dict]:
    out: list[dict] = []
    root = _records_root()
    for path in sorted(root.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict):
            out.append(payload)
    return out


def _teaser_place_ids() -> list[str]:
    """Teaser-lane place_ids from the materialized ledger, in ledger order."""
    path = _lane_status_path()
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    return [
        str(row.get("place_id"))
        for row in payload.get("rows", [])
        if row.get("place_id") and str(row.get("lane")) == "teaser"
    ]


def build_worklist(records: list[dict], *, limit: int | None) -> list[TeaserProspect]:
    """Teaser-lane prospects first (ledger order), then top owned_site by reviews.

    Both halves are :class:`TeaserProspect` instances (carrying ``site_url`` for
    the live fetch and the existing contacts for skip-if-already-set decisions).
    Deduped by place_id; capped at ``limit``.
    """
    by_place: dict[str, dict] = {
        str(r.get("place_id")): r for r in records if r.get("place_id")
    }
    ordered: list[TeaserProspect] = []
    seen: set[str] = set()

    for place_id in _teaser_place_ids():
        record = by_place.get(place_id)
        if not record:
            continue
        prospect = prospect_from_record(record)
        if prospect is None or prospect.place_id in seen:
            continue
        seen.add(prospect.place_id)
        ordered.append(prospect)

    # Then the rest of the owned-site cohort, contactable-last so harvest effort
    # goes to the prospects a hit would actually make launchable.
    for prospect in select_cohort(records, prefer_contactable=True):
        if prospect.place_id in seen:
            continue
        seen.add(prospect.place_id)
        ordered.append(prospect)

    return ordered[:limit] if limit else ordered


def _captured_home_for(place_id: str) -> str | None:
    path = _sites_root() / place_id / "teaser" / "homepage.txt"
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


# ---------------------------------------------------------------- run
def _apply_overrides(
    store: OutreachStore, prospect: TeaserProspect, result: HarvestResult
) -> dict[str, str]:
    """Write harvested digital hits as overrides, skipping channels the prospect
    already has. Returns the fields actually written."""
    existing = {
        "contact_email": prospect.contact_email.strip(),
        "contact_instagram": prospect.contact_instagram.strip(),
        "contact_facebook": prospect.contact_facebook.strip(),
    }
    written: dict[str, str] = {}
    for field_name, value in result.best_overrides().items():
        if field_name not in ALLOWED_OVERRIDE_FIELDS:
            continue
        if existing.get(field_name):
            continue  # don't clobber a contact the prospect already has
        store.set_override(prospect.place_id, field_name, value)
        written[field_name] = value
    return written


def run(
    *,
    from_captured: bool,
    limit: int | None,
    dry_run: bool,
) -> dict[str, int]:
    records = _load_records()
    worklist = build_worklist(records, limit=limit)
    store = OutreachStore()
    suppressed = store.suppressed_keys()

    fetcher = None if from_captured else PoliteFetcher()
    stats = {
        "processed": 0,
        "skipped_suppressed": 0,
        "emails": 0,
        "instagram": 0,
        "facebook": 0,
        "form_only": 0,
        "nothing": 0,
        "overrides_written": 0,
    }

    for prospect in worklist:
        if f"place:{prospect.place_id}" in suppressed:
            stats["skipped_suppressed"] += 1
            continue

        captured = _captured_home_for(prospect.place_id) if from_captured else None
        if from_captured and captured is None:
            # --from-captured runs purely offline: no homepage.txt -> nothing to do.
            continue

        result = harvest_site(
            prospect,
            fetcher=fetcher if fetcher is not None else (lambda _url: None),
            captured_home=captured,
        )
        stats["processed"] += 1

        wrote = {} if dry_run else _apply_overrides(store, prospect, result)
        stats["overrides_written"] += len(wrote)

        if result.best_email:
            stats["emails"] += 1
        if result.instagram:
            stats["instagram"] += 1
        if result.facebook:
            stats["facebook"] += 1
        if not result.best_email and not result.instagram and not result.facebook:
            if result.has_form:
                stats["form_only"] += 1
            else:
                stats["nothing"] += 1

    if not dry_run:
        _append_log(stats, from_captured=from_captured, limit=limit)
    return stats


def _append_log(stats: dict[str, int], *, from_captured: bool, limit: int | None) -> None:
    from datetime import UTC, datetime

    entry = {
        "ran_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "mode": "captured" if from_captured else "live",
        "limit": limit,
        **stats,
    }
    path = _harvest_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-captured",
        action="store_true",
        help="extract from already-captured teaser/homepage.txt (no network)",
    )
    parser.add_argument("--limit", type=int, default=None, help="cap prospects processed")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="harvest + print the summary but write no overrides / log line",
    )
    args = parser.parse_args(argv)

    stats = run(from_captured=args.from_captured, limit=args.limit, dry_run=args.dry_run)
    print(
        "Contact harvest "
        + ("(captured, no network)" if args.from_captured else "(live)")
        + (" [dry-run]" if args.dry_run else "")
    )
    print(f"  processed:        {stats['processed']}")
    print(f"  with email:       {stats['emails']}")
    print(f"  with instagram:   {stats['instagram']}")
    print(f"  with facebook:    {stats['facebook']}")
    print(f"  form-only:        {stats['form_only']}")
    print(f"  nothing:          {stats['nothing']}")
    print(f"  suppressed (skip):{stats['skipped_suppressed']}")
    print(f"  overrides written:{stats['overrides_written']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
