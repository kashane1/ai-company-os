"""Cold-outreach follow-up sequencer (draft-only) — item 6.

Pure step/cadence + observation logic shared by the dashboard
(``outreach_actions``) and the CLI/lane (``outreach_lane``). Nothing here sends:
it decides *when* a prospect is due for the next touch and *what* a shorter
follow-up draft should say.

Not to be confused with ``packages/agency/follow_up.py`` — that is the
client-retainer automation (HubSpot/SMS for paying clients), a different concern.

Cadence is keyed by how many outbound touches the prospect has already received
(the just-logged touch is already counted when scheduling runs):

    after touch 1  -> due again in 4 days  (touch 2)
    after touch 2  -> due again in 8 days  (touch 3)
    after touch 3  -> sequence complete; ``next_touch_at`` cleared (max 3 by code)

The "one new concrete observation" for a follow-up is sourced honestly: a verified
line from the prospect's content brief when one is available (rotated per step),
otherwise a shorter re-pitch of the same already-verified gap. Never fabricated.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from packages.agency.outreach import OutreachContext, sanitize_outreach_copy
from packages.agency.outreach_store import OutreachStore

# outbound-touches-so-far -> days until the next touch is due. A count not in this
# map and below MAX_TOUCHES falls back to the last defined step; at/above
# MAX_TOUCHES the sequence is complete and no next touch is scheduled.
STEP_CADENCE_DAYS = {1: 4, 2: 8}
MAX_TOUCHES = 3

# The content-brief section whose bullet lines are verified facts safe to quote.
_BRIEF_SECTION_RE = re.compile(r"true about the work", re.IGNORECASE)
# Cut a brief bullet at its evidence citation (em dash + *source*, or "(source").
_CITATION_SPLIT_RE = re.compile(r"—|–|\*source|\(source", re.IGNORECASE)


def next_step_for(outbound_count: int) -> int:
    """The touch number a *new* send would be, given prior outbound touches.

    0 prior -> 1 (first touch), 1 prior -> 2, 2 prior -> 3. Capped at
    ``MAX_TOUCHES`` so a finished sequence still resolves to step-3 copy rather
    than running off the end.
    """
    return min(max(outbound_count, 0) + 1, MAX_TOUCHES)


def schedule_next_touch(outbound_count: int, occurred_at: str) -> str:
    """ISO ``next_touch_at`` for the next touch, or ``""`` when the sequence is done.

    ``outbound_count`` includes the touch just logged, so a value of 1 means
    "touch 1 was just sent, schedule touch 2 (+4 days)". At/above ``MAX_TOUCHES``
    the prospect drops out of the due-queue.
    """
    if outbound_count >= MAX_TOUCHES:
        return ""
    days = STEP_CADENCE_DAYS.get(outbound_count)
    if days is None:  # below the first defined step (count <= 0): use the first cadence.
        days = STEP_CADENCE_DAYS[min(STEP_CADENCE_DAYS)]
    base = _parse_iso(occurred_at) or datetime.now(UTC)
    nxt = base + timedelta(days=days)
    return nxt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def outbound_touch_count(store: OutreachStore, place_id: str) -> int:
    """Total outbound (sent) touches for a prospect across all channels.

    Reads the store's outbound-only ``touch_summary`` so inbound replies never
    inflate the count (and never advance the sequence)."""
    channels = store.touch_summary().get(place_id, {})
    return sum(int(stats.get("count", 0) or 0) for stats in channels.values())


# ----------------------------------------------------------------- observation
def default_sites_root(lane_root: Path) -> Path:
    """``…/state/prospects/sites`` derived from the outreach-lane root."""
    return lane_root.parent / "sites"


def _brief_path(place_id: str, sites_root: Path) -> Path:
    return sites_root / place_id / "02-content-brief.md"


def brief_observations(place_id: str, *, sites_root: Path) -> list[str]:
    """Verified work facts from the prospect's content brief, citation stripped.

    Returns the cleaned bullet fragments under the "What's true about the work"
    section, in order. Template placeholders (``<service/specialty>``) and empty
    lines are skipped, so a thin/unfilled brief yields ``[]`` and the caller
    falls back to the safe gap re-pitch.
    """
    path = _brief_path(place_id, sites_root)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    facts: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = bool(_BRIEF_SECTION_RE.search(line))
            continue
        if not in_section:
            continue
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        body = stripped[2:]
        fragment = _CITATION_SPLIT_RE.split(body, maxsplit=1)[0]
        fragment = fragment.strip().strip("*").strip().rstrip(".")
        if not fragment or ("<" in fragment and ">" in fragment) or len(fragment) < 3:
            continue
        facts.append(fragment)
    return facts


def observation_for_step(
    place_id: str,
    step: int,
    ctx: OutreachContext,
    *,
    sites_root: Path,
) -> str:
    """A ready-to-drop observation sentence for a follow-up touch, or ``""``.

    Touch 1 needs no extra observation (it carries its own hook). For touch 2/3,
    rotate in one unused verified brief fact (touch 2 -> fact 1, touch 3 -> fact
    2); when none remain, re-pitch the same already-verified gap, shorter. Never
    invents a new claim. Output is sanitized to the outreach copy rules.
    """
    if step <= 1:
        return ""
    business = ctx.business_name or "your business"
    facts = brief_observations(place_id, sites_root=sites_root)
    idx = step - 2  # touch 2 -> facts[0], touch 3 -> facts[1]
    if 0 <= idx < len(facts):
        return sanitize_outreach_copy(f"One thing I noticed about {business}: {facts[idx]}.")
    gap = (ctx.observed_gap_short or ctx.observed_gap or "").strip().rstrip(".")
    if not gap:
        return ""
    return sanitize_outreach_copy(f"The main thing I noticed is that {gap}.")


def _parse_iso(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


__all__ = [
    "STEP_CADENCE_DAYS",
    "MAX_TOUCHES",
    "next_step_for",
    "schedule_next_touch",
    "outbound_touch_count",
    "default_sites_root",
    "brief_observations",
    "observation_for_step",
]
