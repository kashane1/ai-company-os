"""Manual (browser-based) web-presence verification round-trip.

This is the no-API replacement for the paid Brave/DataForSEO ``verify-web`` path.
The browsing itself is done by an agent driving Chrome; this module only handles
the deterministic, unit-testable halves:

* :func:`export_manual_worklist` — pick a shard of unverified prospects and emit a
  JSON worklist the agent browses.
* :func:`ingest_manual_results` — read the agent-collected observations back and
  persist verdict + demand + contact channels onto each record.

Verdict logic is **reused unchanged** from the API path
(:func:`packages.prospecting.web_presence.classify_web_presence`): the agent only
supplies the raw search results, exactly as a ``SearchVerifier`` would.

Sharding is deterministic (``sha1(place_id) % shard_count``), so N agent chats can
each take ``--shard 0..N-1`` and never touch the same record file. To keep that
guarantee, ingest recomputes cohort/priority **only for the records it just
wrote** — it never does a full-warehouse pass (which would rewrite records owned
by other shards).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlencode

from packages.prospecting.cohorts import derive_composite_cohort, priority_score
from packages.prospecting.storage import ProspectRepository
from packages.prospecting.verification import maps_url
from packages.prospecting.web_presence import (
    SearchResult,
    build_search_query,
    classify_web_presence,
)
from packages.schemas.prospect import ProspectRecord, WebVerifyVerdict, replace_record

MANUAL_METHOD = "manual_browser"

# Verdicts that mark a business as a keep-able target worth reaching out to. Only
# these benefit from a contacts-only pass (owned_site is a drop; ambiguous needs a
# verdict first).
TARGET_VERDICTS = (
    WebVerifyVerdict.SOCIAL_ONLY,
    WebVerifyVerdict.MARKETPLACE_ONLY,
    WebVerifyVerdict.NONE_FOUND,
)
_CONTACT_KEYS = ("email", "instagram", "facebook", "booking_url")


@dataclass(frozen=True)
class ManualIngestResult:
    checked: int = 0
    verdict_counts: dict[str, int] = field(default_factory=dict)
    promoted: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ContactIngestResult:
    updated: int = 0
    missing: list[str] = field(default_factory=list)
    skipped: int = 0


def _has_digital_contact(record: ProspectRecord) -> bool:
    return any(
        [
            record.contact_email,
            record.contact_instagram,
            record.contact_facebook,
            record.contact_booking_url,
        ]
    )


def _shard_of(place_id: str, shard_count: int) -> int:
    digest = hashlib.sha1(place_id.encode("utf-8")).hexdigest()
    return int(digest, 16) % shard_count


def export_manual_worklist(
    records: list[ProspectRecord],
    *,
    cohort: str,
    limit: int,
    shard: int = 0,
    shard_count: int = 1,
) -> list[dict[str, object]]:
    """Return up to ``limit`` worklist rows for one shard of an unverified cohort.

    Selection: records in ``cohort`` whose ``web_verify_verdict`` is still
    ``UNVERIFIED`` and whose deterministic shard equals ``shard``. Sorted by
    descending priority then name so the highest-signal prospects browse first.
    """
    if shard_count < 1:
        raise ValueError("shard_count must be >= 1")
    if not 0 <= shard < shard_count:
        raise ValueError(f"shard must be in [0, {shard_count}); got {shard}")

    candidates = [
        record
        for record in records
        if record.composite_cohort == cohort
        and record.web_verify_verdict is WebVerifyVerdict.UNVERIFIED
        and _shard_of(record.place_id, shard_count) == shard
    ]
    candidates.sort(key=lambda record: (-record.priority_score, record.display_name.lower()))
    selected = candidates[: max(limit, 0)]
    return [_worklist_row(record) for record in selected]


def ingest_manual_results(
    repo: ProspectRepository,
    results: list[dict[str, object]],
    *,
    now: Callable[[], datetime] | None = None,
) -> ManualIngestResult:
    """Persist agent-collected observations onto each record.

    Each input row carries ``place_id`` plus any of: ``results`` (a list of
    ``{title, url, description}`` search hits), ``review_count`` (observed Google
    review count), ``contacts`` (``{email, instagram, facebook, booking_url}``),
    ``verdict_override`` (a :class:`WebVerifyVerdict` value when the agent judges
    presence directly), and ``note``.
    """
    clock = now or (lambda: datetime.now(timezone.utc))
    checked = 0
    skipped = 0
    verdict_counts: dict[str, int] = {}
    promoted: list[str] = []
    missing: list[str] = []
    errors: list[str] = []

    for row in results:
        place_id = str(row.get("place_id", "")).strip()
        if not place_id:
            skipped += 1
            continue
        if not repo.exists(place_id):
            missing.append(place_id)
            continue
        try:
            updated, was_promoted = _apply_row(repo.get(place_id), row, clock())
        except Exception as exc:  # noqa: BLE001 - keep batch output operator-readable
            errors.append(f"{place_id}: {exc}")
            continue
        repo.save(updated)
        checked += 1
        verdict_value = updated.web_verify_verdict.value
        verdict_counts[verdict_value] = verdict_counts.get(verdict_value, 0) + 1
        if was_promoted:
            promoted.append(place_id)

    return ManualIngestResult(
        checked=checked,
        verdict_counts=verdict_counts,
        promoted=promoted,
        missing=missing,
        skipped=skipped,
        errors=errors,
    )


def _apply_row(
    record: ProspectRecord, row: dict[str, object], moment: datetime
) -> tuple[ProspectRecord, bool]:
    timestamp = moment.isoformat()
    search_results = _search_results(row.get("results"))
    override = _verdict_override(row.get("verdict_override"))
    note = str(row.get("note", "")).strip()

    if override is not None:
        verdict = override
        url = str(row.get("verdict_url", "")) or (search_results[0].url if search_results else "")
        confidence = 0.95
        verdict_note = note or "agent verdict override"
    else:
        classified = classify_web_presence(record, search_results)
        verdict = classified.verdict
        url = classified.url
        confidence = classified.confidence
        verdict_note = note or classified.note

    updates: dict[str, object] = {
        "web_verify_class": "web_search",
        "web_verify_verdict": verdict.value,
        "web_verify_url": url,
        "web_verify_confidence": confidence,
        "web_verify_note": verdict_note,
        "web_verified_at": timestamp,
        "web_verify_method": MANUAL_METHOD,
        "updated_at": timestamp,
    }

    review_count = _opt_int(row.get("review_count"))
    if review_count is not None:
        updates["user_ratings_total"] = review_count

    contacts = row.get("contacts")
    if isinstance(contacts, dict) and any(str(value).strip() for value in contacts.values()):
        updates["contact_email"] = str(contacts.get("email", "")).strip()
        updates["contact_instagram"] = str(contacts.get("instagram", "")).strip()
        updates["contact_facebook"] = str(contacts.get("facebook", "")).strip()
        updates["contact_booking_url"] = str(contacts.get("booking_url", "")).strip()
        updates["contact_source"] = MANUAL_METHOD
        updates["contact_collected_at"] = timestamp

    updated = replace_record(record, **updates)
    # Recompute cohort/score for THIS record only (a fresh review_count can promote
    # an S_source_candidate into A_gold/C/D). Staying record-local keeps writes
    # inside this shard so parallel chats never collide.
    cohort = derive_composite_cohort(updated)
    score = priority_score(updated, cohort)
    updated = replace_record(updated, composite_cohort=cohort, priority_score=score)
    return updated, cohort != record.composite_cohort


def export_contact_worklist(
    records: list[ProspectRecord],
    *,
    ids: set[str] | None = None,
    limit: int,
    shard: int = 0,
    shard_count: int = 1,
) -> list[dict[str, object]]:
    """Worklist for the lighter CONTACTS-ONLY pass (verdict already settled).

    Selects already-verified TARGET records (social/marketplace/none_found) that
    still lack a digital contact channel. Pass ``ids`` to restrict to a specific set
    (e.g. the sample-site businesses). Each row carries the business's known
    ``web_verify_url`` (their Yelp/social page) and phone as the agent's starting
    point — no verdict work needed, just grab the best email/IG/FB/booking.
    """
    if shard_count < 1:
        raise ValueError("shard_count must be >= 1")
    if not 0 <= shard < shard_count:
        raise ValueError(f"shard must be in [0, {shard_count}); got {shard}")

    candidates = [
        record
        for record in records
        if (ids is None or record.place_id in ids)
        and record.web_verify_verdict in TARGET_VERDICTS
        and not _has_digital_contact(record)
        and _shard_of(record.place_id, shard_count) == shard
    ]
    candidates.sort(key=lambda record: (-record.priority_score, record.display_name.lower()))
    selected = candidates[: max(limit, 0)]
    return [_contact_worklist_row(record) for record in selected]


def ingest_manual_contacts(
    repo: ProspectRepository,
    results: list[dict[str, object]],
    *,
    now: Callable[[], datetime] | None = None,
) -> ContactIngestResult:
    """Write ONLY the contact channels onto each record; leave the verdict alone.

    Unlike :func:`ingest_manual_results`, this never reclassifies web presence or
    recomputes the cohort — it is the safe path for businesses whose verdict is
    already settled. A row needs ``place_id`` and a ``contacts`` mapping with at
    least one non-empty channel.
    """
    clock = now or (lambda: datetime.now(timezone.utc))
    updated = 0
    skipped = 0
    missing: list[str] = []

    for row in results:
        place_id = str(row.get("place_id", "")).strip()
        contacts = row.get("contacts")
        provided = (
            {k: str(contacts.get(k, "")).strip() for k in _CONTACT_KEYS}
            if isinstance(contacts, dict)
            else {}
        )
        if not place_id or not any(provided.values()):
            skipped += 1
            continue
        if not repo.exists(place_id):
            missing.append(place_id)
            continue
        timestamp = clock().isoformat()
        record = repo.get(place_id)
        updates: dict[str, object] = {
            "contact_source": MANUAL_METHOD,
            "contact_collected_at": timestamp,
            "updated_at": timestamp,
        }
        # Only overwrite a channel when the agent found one (don't blank existing).
        if provided["email"]:
            updates["contact_email"] = provided["email"]
        if provided["instagram"]:
            updates["contact_instagram"] = provided["instagram"]
        if provided["facebook"]:
            updates["contact_facebook"] = provided["facebook"]
        if provided["booking_url"]:
            updates["contact_booking_url"] = provided["booking_url"]
        repo.save(replace_record(record, **updates))
        updated += 1

    return ContactIngestResult(updated=updated, missing=missing, skipped=skipped)


def _contact_worklist_row(record: ProspectRecord) -> dict[str, object]:
    return {
        "place_id": record.place_id,
        "display_name": record.display_name,
        "formatted_address": record.formatted_address,
        "phone": record.phone,
        "city_id": record.city_id,
        "genre_id": record.genre_id,
        "web_verify_verdict": record.web_verify_verdict.value,
        "known_url": record.web_verify_url,  # their Yelp/social page — start here
        "maps_url": _worklist_maps_url(record),
        # Agent fills these, then ingest writes only the contact channels:
        "contacts": {"email": "", "instagram": "", "facebook": "", "booking_url": ""},
    }


def _worklist_row(record: ProspectRecord) -> dict[str, object]:
    return {
        "place_id": record.place_id,
        "display_name": record.display_name,
        "formatted_address": record.formatted_address,
        "phone": record.phone,
        "city_id": record.city_id,
        "genre_id": record.genre_id,
        "composite_cohort": record.composite_cohort,
        "search_query": build_search_query(record),
        "maps_url": _worklist_maps_url(record),
        # Agent fills these in place, then ingest reads them back:
        "results": [],
        "review_count": None,
        "contacts": {"email": "", "instagram": "", "facebook": "", "booking_url": ""},
        "verdict_override": "",
        "note": "",
    }


def _worklist_maps_url(record: ProspectRecord) -> str:
    # Source-imported candidates (Overture/FSQ) carry a source id, not a Google
    # place id, so ``query_place_id`` can't resolve them. Fall back to a plain
    # name+address text search the agent can open directly. Records with a real
    # Google place id keep the precise place-pinned link.
    if record.place_id.startswith("places/") and not record.source_name:
        return maps_url(record)
    query = " ".join(part for part in [record.display_name, record.formatted_address] if part)
    return "https://www.google.com/maps/search/?" + urlencode({"api": "1", "query": query})


def _search_results(value: object) -> list[SearchResult]:
    if not isinstance(value, list):
        return []
    parsed: list[SearchResult] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        parsed.append(
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                description=str(item.get("description", item.get("snippet", "")) or ""),
            )
        )
    return parsed


def _verdict_override(value: object) -> WebVerifyVerdict | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    try:
        return WebVerifyVerdict(text)
    except ValueError as exc:
        valid = ", ".join(item.value for item in WebVerifyVerdict)
        raise ValueError(f"invalid verdict_override {text!r}; expected one of: {valid}") from exc


def _opt_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)  # type: ignore[arg-type]
