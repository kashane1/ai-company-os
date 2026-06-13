"""Teardown-teaser lane (Agency layer) — the owned-site flip.

61% of audited prospects were dropped for already having a real website. They are
the majority of the database, easier to contact, and have demonstrably paid for
web work. This lane repositions Conversion Lab as the *lead* product for them:
a light persona-panel pass over their *existing* homepage, distilled to the top-3
conversion blockers, rendered as a one-page teaser that pitches the paid
Conversion Audit (not a rebuild).

This module is the pure core (selection, prompt prep, finding validation, artifact
rendering). The orchestrator ``scripts/agency/build_teardown_teaser.py`` does the
I/O, browser capture, and agent-in-the-loop handoff.

Guardrails baked in here:
- **No invented findings.** Every teaser finding cites a ``persona_id`` and an
  ``evidence_quote`` that must be a *verbatim substring* of that persona's review
  text (:func:`validate_findings`); an unsupported finding raises, it does not ship.
- **Advisory only.** The renderers carry the synthetic-audience methodology
  disclosure and never predict revenue (mirrors the Conversion Lab rule).
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from functools import lru_cache

from packages.agency.catalog import default_catalog
from packages.agency.conversion_lab import build_persona_review_prompt, render_prompts_markdown
from packages.agency.conversion_personas import (
    PersonaPackError,
    load_audience_panel,
    smallest_panel,
)
from packages.agency.outreach import bbw_ref_token
from packages.agency.prospect_site import city_label
from packages.schemas.conversion_lab import ConversionAction, ConversionLabInput, PersonaReview

# Service ids in catalog.yaml the teaser pitches. Snapshot = the $100 quick audit,
# Audit = the $250 full audit. Read from the catalog so copy tracks the price.
SNAPSHOT_SERVICE_ID = "conversion_snapshot"
AUDIT_SERVICE_ID = "conversion_audit"

DEFAULT_PANEL_SIZE = 3
DEFAULT_MIN_REVIEWS = 1


# --------------------------------------------------------------------- cohort
@dataclass(frozen=True)
class TeaserProspect:
    place_id: str
    business_name: str
    genre_id: str
    vertical: str
    city_id: str
    city: str
    site_url: str
    review_count: int
    phone: str = ""
    contact_email: str = ""
    contact_instagram: str = ""
    contact_facebook: str = ""

    def slug(self) -> str:
        """Filesystem-safe id for working dirs (place_ids contain '/' and ':')."""
        return re.sub(r"[^A-Za-z0-9._-]+", "_", self.place_id).strip("_") or "prospect"


def site_url_for(record: dict) -> str:
    """The prospect's own homepage — what we run the teardown against."""
    for key in ("web_verify_url", "contact_owned_website"):
        value = str(record.get(key) or "").strip()
        if value:
            return value
    return ""


def normalize_site_url(url: str) -> str:
    """Canonical key for "same homepage" dedupe: lowercase, no scheme/www, no
    trailing slash. Source records often repeat one site across sibling records
    (chains, dupes), and we only want one teaser per distinct homepage."""
    value = (url or "").strip().lower()
    value = re.sub(r"^[a-z]+://", "", value)
    value = re.sub(r"^www\.", "", value)
    return value.rstrip("/")


@lru_cache(maxsize=256)
def _has_panel(genre_id: str) -> bool:
    """Cached: can Conversion Lab build a panel for this genre? Cohort selection
    scans tens of thousands of records, so this must not re-parse YAML per record."""
    try:
        load_audience_panel(genre_id)
    except PersonaPackError:
        return False
    return True


def resolve_vertical(genre_id: str) -> str | None:
    """Return ``genre_id`` if Conversion Lab can build a panel for it, else None.

    The persona modifiers list genre_ids verbatim, so the genre is usually the
    vertical directly; genres with no modifier (rare) can't be reviewed and are
    skipped rather than guessed.
    """
    genre_id = (genre_id or "").strip()
    if not genre_id:
        return None
    return genre_id if _has_panel(genre_id) else None


def prospect_from_record(record: dict) -> TeaserProspect | None:
    """Build a :class:`TeaserProspect` from a raw record, or None if ineligible.

    Eligible = verdict ``owned_site`` with a known site URL and a genre Conversion
    Lab can panel. Contact fields are carried through for the outreach draft.
    """
    if str(record.get("web_verify_verdict") or "") != "owned_site":
        return None
    site_url = site_url_for(record)
    if not site_url:
        return None
    place_id = str(record.get("place_id") or "").strip()
    if not place_id:
        return None
    vertical = resolve_vertical(str(record.get("genre_id") or ""))
    if vertical is None:
        return None
    city_id = str(record.get("city_id") or "")
    return TeaserProspect(
        place_id=place_id,
        business_name=str(record.get("display_name") or ""),
        genre_id=str(record.get("genre_id") or ""),
        vertical=vertical,
        city_id=city_id,
        city=city_label(city_id),
        site_url=site_url,
        review_count=int(record.get("user_ratings_total") or 0),
        phone=str(record.get("phone") or ""),
        contact_email=str(record.get("contact_email") or ""),
        contact_instagram=str(record.get("contact_instagram") or ""),
        contact_facebook=str(record.get("contact_facebook") or ""),
    )


def has_digital_channel(prospect: TeaserProspect) -> bool:
    """True if the prospect already carries a sendable *digital* channel — an
    email or a social handle. Phone is excluded: it is not a channel the teaser
    email/DM pitch can launch from, and SMS infra isn't wired."""
    return bool(
        prospect.contact_email.strip()
        or prospect.contact_instagram.strip()
        or prospect.contact_facebook.strip()
    )


def select_cohort(
    records: list[dict],
    *,
    limit: int | None = None,
    min_reviews: int = DEFAULT_MIN_REVIEWS,
    prefer_contactable: bool = False,
    allow_phone_only: bool = True,
) -> list[TeaserProspect]:
    """Owned-site prospects prioritized by review count (the eval-doc ordering).

    Deduped by normalized homepage so sibling/duplicate records that share one
    site (chains, dupes) don't each consume a teaser slot — the highest-review
    record for a given homepage wins.

    ``prefer_contactable`` (additive; default off keeps the original ordering)
    sorts prospects that already have a sendable digital channel (email / social)
    ahead of the rest, with review count as the tiebreak.

    ``allow_phone_only`` (default True, the historical behavior) keeps
    phone-only-or-nothing prospects in the cohort. Set it False to *exclude* any
    prospect with no digital channel — the harvester's "worth fetching" worklist
    wants only the ones a harvested email/social could make launchable, but by
    default nothing is dropped so existing callers are unaffected.
    """
    prospects: list[TeaserProspect] = []
    for record in records:
        prospect = prospect_from_record(record)
        if prospect is None or prospect.review_count < min_reviews:
            continue
        if not allow_phone_only and not has_digital_channel(prospect):
            continue
        prospects.append(prospect)
    if prefer_contactable:
        prospects.sort(
            key=lambda p: (not has_digital_channel(p), -p.review_count, p.business_name.lower())
        )
    else:
        prospects.sort(key=lambda p: (-p.review_count, p.business_name.lower()))
    deduped: list[TeaserProspect] = []
    seen_sites: set[str] = set()
    for prospect in prospects:  # already sorted, so first seen per site is the top one
        key = normalize_site_url(prospect.site_url)
        if key in seen_sites:
            continue
        seen_sites.add(key)
        deduped.append(prospect)
    return deduped[:limit] if limit else deduped


# ------------------------------------------------------------------- offer
@dataclass(frozen=True)
class TeaserOffer:
    snapshot_name: str
    snapshot_fee: int
    audit_name: str
    audit_fee: int

    def to_dict(self) -> dict[str, object]:
        return {
            "snapshot_name": self.snapshot_name,
            "snapshot_fee": self.snapshot_fee,
            "audit_name": self.audit_name,
            "audit_fee": self.audit_fee,
        }


def load_offer(catalog=None) -> TeaserOffer:
    """Pull the snapshot/audit names + prices from the service catalog."""
    catalog = catalog or default_catalog()
    snapshot = catalog.services[SNAPSHOT_SERVICE_ID]
    audit = catalog.services[AUDIT_SERVICE_ID]
    return TeaserOffer(
        snapshot_name=snapshot.name,
        snapshot_fee=int(round(snapshot.setup_fee)),
        audit_name=audit.name,
        audit_fee=int(round(audit.setup_fee)),
    )


# ----------------------------------------------------------------- prompts
def build_input(prospect: TeaserProspect, page_copy: str) -> ConversionLabInput:
    """The Conversion Lab input for a homepage teardown.

    ``target_action`` is CALL: an owned-site local business's homepage conversion
    is overwhelmingly "get the customer to call/contact", which is what the panel
    pressure-tests.
    """
    return ConversionLabInput(
        product_id=prospect.slug(),
        vertical=prospect.vertical,
        target_action=ConversionAction.CALL,
        url=prospect.site_url,
        page_copy=page_copy,
        known_objections=[],
    )


def prepare_prompts(
    prospect: TeaserProspect,
    page_copy: str,
    *,
    panel_size: int = DEFAULT_PANEL_SIZE,
) -> tuple[ConversionLabInput, str, list[str]]:
    """Return ``(input, prompts_markdown, persona_ids)`` for the light panel pass."""
    panel = smallest_panel(load_audience_panel(prospect.vertical), n=panel_size)
    payload = build_input(prospect, page_copy)
    prompts = [
        build_persona_review_prompt(persona=persona, input_payload=payload, modifier=panel.modifier)
        for persona in panel.personas
    ]
    persona_ids = [p.persona_id for p in panel.personas]
    return payload, render_prompts_markdown(payload, prompts), persona_ids


# ----------------------------------------------------------------- findings
@dataclass(frozen=True)
class TeaserFinding:
    title: str
    evidence_quote: str
    persona_id: str
    recommendation: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "evidence_quote": self.evidence_quote,
            "persona_id": self.persona_id,
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "TeaserFinding":
        return cls(
            title=str(payload["title"]).strip(),
            evidence_quote=str(payload["evidence_quote"]).strip(),
            persona_id=str(payload["persona_id"]).strip(),
            recommendation=str(payload.get("recommendation", "")).strip(),
        )


class FindingValidationError(ValueError):
    """Raised when a finding's evidence quote isn't grounded in persona output."""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def persona_evidence_index(reviews: list[PersonaReview]) -> dict[str, str]:
    """``{persona_id: normalized concatenated review text}`` for substring checks."""
    index: dict[str, str] = {}
    for review in reviews:
        parts = [
            review.likely_action,
            *review.clarity_notes,
            *review.objections,
            *review.trust_gaps,
            *review.useful_rewrites,
        ]
        index[review.persona_id] = _normalize(" \n ".join(parts))
    return index


def validate_findings(findings: list[TeaserFinding], reviews: list[PersonaReview]) -> None:
    """Enforce the no-invented-findings guardrail.

    Each finding must (a) name a persona that's actually in ``reviews`` and (b)
    quote text that appears verbatim (whitespace-normalized) in that persona's
    review. Raises :class:`FindingValidationError` on the first violation so the
    teaser never ships an unsupported claim.
    """
    if not findings:
        raise FindingValidationError("no findings provided")
    index = persona_evidence_index(reviews)
    for finding in findings:
        if not finding.evidence_quote:
            raise FindingValidationError(f"finding {finding.title!r}: empty evidence_quote")
        if finding.persona_id not in index:
            raise FindingValidationError(
                f"finding {finding.title!r}: persona_id {finding.persona_id!r} not in reviews "
                f"(have: {', '.join(sorted(index)) or 'none'})"
            )
        if _normalize(finding.evidence_quote) not in index[finding.persona_id]:
            raise FindingValidationError(
                f"finding {finding.title!r}: evidence_quote not found verbatim in "
                f"{finding.persona_id!r}'s review (invented or paraphrased)"
            )


# ----------------------------------------------------------------- artifacts
METHODOLOGY_NOTE = (
    "These findings come from a structured heuristic review using a synthetic "
    "audience (a panel of buyer personas reasoning over your live homepage). It is "
    "a preflight signal, not live analytics or real customer interviews."
)


def build_teaser_data(
    prospect: TeaserProspect,
    findings: list[TeaserFinding],
    offer: TeaserOffer,
    *,
    persona_ids: list[str] | None = None,
) -> dict:
    """The ``teaser.json`` sidecar — canonical findings + offer + provenance.

    Read at dashboard render time to rebuild the outreach copy without re-running
    the panel, and kept as the audit trail that ties each claim to a persona.
    """
    return {
        "place_id": prospect.place_id,
        "business_name": prospect.business_name,
        "genre_id": prospect.genre_id,
        "vertical": prospect.vertical,
        "city": prospect.city,
        "site_url": prospect.site_url,
        "review_count": prospect.review_count,
        "persona_ids": list(persona_ids or sorted({f.persona_id for f in findings})),
        "findings": [f.to_dict() for f in findings],
        "offer": offer.to_dict(),
        "methodology": METHODOLOGY_NOTE,
    }


def render_teaser_markdown(
    prospect: TeaserProspect, findings: list[TeaserFinding], offer: TeaserOffer
) -> str:
    """One-page teaser: the 3 findings with evidence, methodology, audit CTA."""
    lines = [
        f"# Conversion teardown: {prospect.business_name}",
        "",
        f"A {len(findings)}-point read of **{prospect.site_url}** from a synthetic "
        f"buyer panel for {prospect.genre_id.replace('_', ' ')} customers"
        + (f" in {prospect.city}" if prospect.city else "")
        + ".",
        "",
        "## What we noticed",
        "",
    ]
    for i, finding in enumerate(findings, start=1):
        lines.append(f"### {i}. {finding.title}")
        lines.append("")
        lines.append(f"> {finding.evidence_quote}")
        lines.append("")
        lines.append(f"_— {finding.persona_id.replace('-', ' ')} (synthetic persona)_")
        if finding.recommendation:
            lines.append("")
            lines.append(f"**Worth trying:** {finding.recommendation}")
        lines.append("")
    lines.extend(
        [
            "## Want the full read?",
            "",
            f"This is a free teaser. The **{offer.audit_name}** (${offer.audit_fee}) is a "
            f"persona-by-persona teardown of your whole site with prioritized copy "
            f"rewrites; the **{offer.snapshot_name}** (${offer.snapshot_fee}) is a faster "
            "single-page version. No rebuild required — these are advisory audits of "
            "the site you already have.",
            "",
            "---",
            "",
            f"_{METHODOLOGY_NOTE}_",
            "",
        ]
    )
    return "\n".join(lines)


def render_teaser_card_html(
    prospect: TeaserProspect,
    findings: list[TeaserFinding],
    *,
    homepage_image: str,
) -> str:
    """A shareable annotated card: their homepage screenshot + finding callouts.

    ``homepage_image`` is the path the card's ``<img>`` references — pass a path
    relative to the card file so :file:`card_to_png.mjs` can serve it locally.
    Self-contained (inline CSS, system fonts) so it renders deterministically.
    """
    def esc(value: str) -> str:
        return html.escape(value or "", quote=True)

    callouts = []
    for i, finding in enumerate(findings, start=1):
        callouts.append(
            f"""
        <li class="finding">
          <span class="num">{i}</span>
          <div>
            <div class="ftitle">{esc(finding.title)}</div>
            <div class="fquote">&ldquo;{esc(finding.evidence_quote)}&rdquo;</div>
          </div>
        </li>"""
        )
    subtitle = esc(prospect.genre_id.replace("_", " "))
    if prospect.city:
        subtitle += f" &middot; {esc(prospect.city)}"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         color: #16191d; background: #fff; width: 1200px; }}
  .card {{ display: grid; grid-template-columns: 620px 1fr; }}
  .shot {{ background: #eef0f3; border-right: 1px solid #e2e5ea; overflow: hidden;
          max-height: 760px; }}
  .shot img {{ width: 100%; display: block; }}
  .panel {{ padding: 36px 34px; }}
  .kicker {{ font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase;
            color: #8a6d2b; font-weight: 700; }}
  h1 {{ font-size: 27px; line-height: 1.18; margin: 6px 0 2px; }}
  .sub {{ color: #6b727b; font-size: 13px; margin-bottom: 24px; }}
  ul {{ list-style: none; }}
  .finding {{ display: flex; gap: 14px; padding: 16px 0; border-top: 1px solid #edf0f3; }}
  .num {{ flex: none; width: 30px; height: 30px; border-radius: 999px; background: #16191d;
         color: #fff; font-weight: 700; display: flex; align-items: center;
         justify-content: center; font-size: 14px; }}
  .ftitle {{ font-weight: 650; font-size: 16px; }}
  .fquote {{ color: #545b64; font-size: 13.5px; font-style: italic; margin-top: 3px; }}
  .foot {{ margin-top: 26px; padding-top: 16px; border-top: 2px solid #16191d;
          font-size: 12px; color: #6b727b; }}
</style></head>
<body>
  <div class="card">
    <div class="shot"><img src="{esc(homepage_image)}" alt="homepage"></div>
    <div class="panel">
      <div class="kicker">Conversion teardown</div>
      <h1>{esc(prospect.business_name)}</h1>
      <div class="sub">{subtitle}</div>
      <ul>{''.join(callouts)}</ul>
      <div class="foot">Synthetic-audience heuristic review &middot; advisory preflight.</div>
    </div>
  </div>
</body></html>
"""


def render_teaser_outreach_markdown(
    prospect: TeaserProspect, findings: list[TeaserFinding], offer: TeaserOffer
) -> str:
    """The on-disk outreach draft (all channels) for the teaser variant.

    Reuses :func:`packages.agency.outreach_messages.build_teaser_messages` so the
    dashboard copy and the saved draft never drift.
    """
    from packages.agency import outreach_messages as msg

    messages = msg.build_teaser_messages(
        business_name=prospect.business_name,
        city=prospect.city,
        site_url=prospect.site_url,
        findings=[f.to_dict() for f in findings],
        offer=offer.to_dict(),
        ref_token=bbw_ref_token(prospect.place_id),
    )
    return "\n".join(
        [
            f"# Outreach draft (teaser): {prospect.business_name}",
            "",
            f"Variant: teaser &middot; place_id: `{prospect.place_id}`",
            "",
            "## Email",
            "",
            f"**Subject:** {messages.email_subject}",
            "",
            messages.email_body,
            "",
            "## SMS",
            "",
            messages.sms_body,
            "",
            "## DM (Instagram / Facebook)",
            "",
            messages.dm_body,
            "",
            "## Call script",
            "",
            messages.call_script,
            "",
        ]
    )
