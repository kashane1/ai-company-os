"""Server-rendered HTML for the outreach action panel.

Deliberately *not* the 5s auto-refreshing ops dashboard — this page is
interactive (inline edits, button clicks) and a periodic refresh would wipe a
half-typed contact field. Actions POST to the endpoint and the page reloads on
success, so the server stays the single source of truth and the JS stays tiny.
"""

from __future__ import annotations

import html

from packages.agency.funnel import FUNNEL_REFRESH_COOLDOWN_SECONDS
from packages.agency.outreach_actions import ActionRow, ChannelButton, OutreachPanelView


def _e(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _badge(button: ChannelButton) -> str:
    if button.sent_count <= 0:
        return "<span class='badge muted small'>not sent</span>"
    last = button.last_sent_at.split("T")[0] if button.last_sent_at else ""
    suffix = f", last {_e(last)}" if last else ""
    return f"<span class='badge sent small'>sent &times;{button.sent_count}{suffix}</span>"


def _launch(button: ChannelButton) -> str:
    if button.enabled and button.url:
        return (
            f"<a class='btn launch' href='{_e(button.url)}' target='_blank' "
            f"rel='noopener'>{_e(button.label)}</a>"
        )
    return (
        "<span class='btn launch disabled' title='Add a contact value to enable'>"
        f"{_e(button.label)}</span>"
    )


def _channel_row(row: ActionRow, button: ChannelButton) -> str:
    # A suppressed prospect can't be logged as sent — disable the log button to
    # match the disabled launch link (the endpoint refuses it regardless).
    log_attr = " disabled title='Prospect is suppressed'" if row.suppressed else ""
    log_cls = "btn log disabled" if row.suppressed else "btn log js-log"
    return f"""
    <div class="chan">
      {_launch(button)}
      <button class="{log_cls}" data-place="{_e(row.place_id)}"
              data-channel="{_e(button.channel)}"{log_attr}>&#10003; Log sent</button>
      <button class="btn ghost js-copy" data-copy="{_e(button.copy)}">copy</button>
      <input class="contact" type="text" value="{_e(button.contact_value)}"
             placeholder="{_e(button.contact_field)}"
             id="c-{_e(row.place_id)}-{_e(button.channel)}">
      <button class="btn ghost js-save" data-place="{_e(row.place_id)}"
              data-field="{_e(button.contact_field)}"
              data-target="c-{_e(row.place_id)}-{_e(button.channel)}">save</button>
      {_badge(button)}
    </div>"""


def _status_select(row: ActionRow, statuses: list[str]) -> str:
    options = "".join(
        f"<option value='{_e(s)}'{' selected' if s == row.status else ''}>{_e(s)}</option>"
        for s in statuses
    )
    return (
        f"<select class='js-status' data-place='{_e(row.place_id)}'>{options}</select>"
    )


def _label(value: str) -> str:
    return value.replace("_", " ")


def _status_controls(view: OutreachPanelView) -> str:
    counts = {status: 0 for status in view.statuses}
    for row in view.rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    buttons = [
        f"<button class='chip active' data-status-filter='all'>"
        f"All <b>{len(view.rows)}</b></button>",
        f"<button class='chip due' data-due-filter='1'>Due now <b>{view.due_count}</b></button>",
    ]
    buttons.extend(
        f"<button class='chip' data-status-filter='{_e(status)}'>"
        f"{_e(_label(status))} <b>{counts.get(status, 0)}</b></button>"
        for status in view.statuses
    )
    return "".join(buttons)


def _variant_select(view: OutreachPanelView) -> str:
    options = "".join(
        f"<option value='{_e(v)}'{' selected' if v == view.default_variant else ''}>"
        f"{_e(v)}</option>"
        for v in view.variants
    )
    return (
        "<label class='variantlabel' title='A/B arm tagged on every logged send'>"
        f"variant <select id='variant' class='sort'>{options}</select></label>"
    )


def _facet_controls(view: OutreachPanelView) -> str:
    return "".join(
        f"<button class='chip facet' data-facet-filter='{_e(facet.key)}'>"
        f"{_e(facet.label)} <b>{facet.count}</b></button>"
        for facet in view.facets
    )


def _controls(view: OutreachPanelView) -> str:
    return f"""
  <section class="controls" aria-label="Outreach filters">
    <div class="controltop">
      <input class="search" id="search" type="search"
             placeholder='Search businesses, cities, or types'>
      <select id="sort" class="sort">
        <option value="priority" data-sort='priority'>Priority</option>
        <option value="due" data-sort='due'>Due first</option>
        <option value="recent_touch" data-sort='recent_touch'>Recently touched</option>
        <option value="business" data-sort='business'>Business A-Z</option>
        <option value="city" data-sort='city'>City</option>
        <option value="sends" data-sort='sends'>Most sends</option>
      </select>
      {_variant_select(view)}
      <button class="btn ghost" id="clearFilters">clear</button>
      <span class="visible" id="visibleCount">{len(view.rows)} shown</span>
    </div>
    <div class="chips statuschips">{_status_controls(view)}</div>
    <div class="chips facetchips">{_facet_controls(view)}</div>
  </section>"""


def _due_label(row: ActionRow) -> str:
    if row.suppressed:
        return ""
    if row.due:
        day = row.next_touch_at.split("T")[0] if row.next_touch_at else ""
        return f"<span class='badge due small' title='Follow-up due'>due {_e(day)}</span>"
    if row.next_touch_at:
        day = row.next_touch_at.split("T")[0]
        return f"<span class='badge muted small'>next {_e(day)}</span>"
    return ""


def _row_block(row: ActionRow, statuses: list[str]) -> str:
    site = (
        f"<a href='{_e(row.mockup_url)}' target='_blank' rel='noopener'>preview site</a>"
        if row.mockup_url
        else ""
    )
    channels = "".join(_channel_row(row, b) for b in row.buttons)
    tags = " ".join(row.facts.tags)
    search = " ".join([row.business_name, row.city, row.genre_id, row.status]).lower()
    priority = statuses.index(row.status) if row.status in statuses else 999
    card_cls = "card suppressed" if row.suppressed else "card"
    banner = (
        f"<div class='suppbanner small' title='{_e(row.suppression_reason)}'>"
        f"&#128683; Suppressed &mdash; {_e(row.suppression_reason or 'do not contact')}</div>"
        if row.suppressed
        else ""
    )
    disqualify = (
        ""
        if row.suppressed
        else (
            f"<button class='btn ghost js-disqualify' "
            f"data-place='{_e(row.place_id)}'>disqualify</button>"
        )
    )
    return f"""
  <div class="{card_cls}" data-place="{_e(row.place_id)}" data-status="{_e(row.status)}"
       data-tags="{_e(tags)}" data-search="{_e(search)}"
       data-business="{_e(row.business_name.lower())}" data-city="{_e(row.city.lower())}"
       data-sends="{row.facts.total_sent_count}" data-last-touch="{_e(row.facts.last_sent_at)}"
       data-priority="{priority}" data-due="{1 if row.due else 0}"
       data-next-touch="{_e(row.next_touch_at)}" data-suppressed="{1 if row.suppressed else 0}">
    {banner}
    <div class="cardhead">
      <div>
        <b>{_e(row.business_name)}</b>
        <span class="muted small">{_e(row.genre_id)} &middot; {_e(row.city)}</span>
      </div>
      <div class="headright">
        {_due_label(row)}
        {site}
        {_status_select(row, statuses)}
        {disqualify}
      </div>
    </div>
    <div class="muted small nextaction">{_e(row.next_action)}</div>
    {channels}
  </div>"""


def _delta_chip(delta: int) -> str:
    if delta > 0:
        return f"<span class='fdelta up'>&#9650;{delta}</span>"
    if delta < 0:
        return f"<span class='fdelta down'>&#9660;{abs(delta)}</span>"
    return ""


def _funnel_refresh(updated: str) -> str:
    """Refresh button + status, on a client+server cooldown anchored to the
    snapshot's ``updated_at`` (the JS reads ``data-updated`` to start disabled
    and count down; the server is authoritative and returns 429 if jumped)."""
    return (
        "<span class='funnelctl'>"
        f"<button id='funnelRefresh' class='btn fbtn' data-updated='{_e(updated)}' "
        f"data-cooldown='{FUNNEL_REFRESH_COOLDOWN_SECONDS}'>&#8635; Refresh</button>"
        "<span id='funnelStatus' class='muted small'></span>"
        "</span>"
    )


def _funnel_scoreboard(funnel: dict | None) -> str:
    """The honest scoreboard strip pinned to the top of the dashboard.

    Reads the committed ``funnel-report.json`` snapshot (computed by
    ``scripts/agency/funnel_report.py``) — a fast, timestamped view, not a live
    recompute. Renders a placeholder when no report exists yet rather than
    inventing numbers.
    """
    if not funnel:
        return (
            "<section class='scoreboard empty'>"
            "<div class='scorehead'>"
            "<span class='muted small'>No funnel report yet &mdash; "
            "click Refresh (or run <code>scripts/agency/funnel_report.py</code>).</span>"
            f"{_funnel_refresh('')}"
            "</div>"
            "</section>"
        )
    stages = funnel.get("stages", []) if isinstance(funnel, dict) else []
    mrr = funnel.get("mrr", {}) if isinstance(funnel, dict) else {}
    updated = str(funnel.get("updated_at", ""))
    zero = funnel.get("zero_data", []) or []

    tiles = []
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        conv = stage.get("conversion_pct")
        conv_cell = (
            f"<span class='fconv'>{conv:g}% of prev</span>"
            if isinstance(conv, (int, float))
            else "<span class='fconv muted'>&mdash;</span>"
        )
        avail = "" if stage.get("available", True) else "<span class='fno'>no source</span>"
        tiles.append(
            "<div class='ftile'>"
            f"<div class='flabel'>{_e(stage.get('label', ''))}</div>"
            f"<div class='fcount'>{_e(stage.get('count', 0))} "
            f"{_delta_chip(int(stage.get('delta', 0) or 0))}</div>"
            f"<div class='fsub'>{conv_cell}{avail}</div>"
            "</div>"
        )
    mrr_usd = mrr.get("mrr_usd", 0) if isinstance(mrr, dict) else 0
    clients = mrr.get("active_clients", 0) if isinstance(mrr, dict) else 0
    tiles.append(
        "<div class='ftile money'>"
        "<div class='flabel'>MRR</div>"
        f"<div class='fcount'>${_e(f'{float(mrr_usd):,.0f}')}</div>"
        f"<div class='fsub'>{_e(clients)} active</div>"
        "</div>"
    )
    zero_text = ", ".join(str(z).split(" (")[0] for z in zero)
    zero_note = (
        f"<div class='fzero small'>Zero data: {_e(zero_text)}</div>" if zero else ""
    )
    return f"""
  <section class="scoreboard" aria-label="Funnel scoreboard">
    <div class="scorehead">
      <b>Funnel</b>
      <span class="muted small">snapshot {_e(updated.split('T')[0])} &middot; \
from funnel-report.json</span>
      {_funnel_refresh(updated)}
    </div>
    <div class="ftiles">{''.join(tiles)}</div>
    {zero_note}
  </section>"""


def render_outreach_html(view: OutreachPanelView, *, funnel: dict | None = None) -> str:
    cards = "".join(_row_block(row, view.statuses) for row in view.rows) or (
        "<p class='muted'>No deployed prospects in the ledger yet. "
        "Run <code>scripts/agency/outreach_lane.py refresh</code>.</p>"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>outreach action panel</title>
<style>
  body {{ font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         color: #202124; margin: 0; background: #f6f7f9; }}
  header {{ background: #121417; color: white; padding: 16px 24px; }}
  h1 {{ font-size: 18px; margin: 0; }}
  .meta {{ color: #c7ccd1; font-size: 12px; margin-top: 3px; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 18px 24px 56px; }}
  .scoreboard {{ background: #121417; color: #e9edf1; border-radius: 10px;
                padding: 12px 16px 14px; margin-bottom: 16px; }}
  .scoreboard.empty {{ background: #f0f2f4; color: #5f6368; padding: 10px 14px; }}
  .scoreboard code {{ background: #2a2e33; color: #e9edf1; }}
  .scorehead {{ display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; }}
  .scorehead b {{ font-size: 13px; letter-spacing: 0.04em; text-transform: uppercase; }}
  .scorehead .muted {{ color: #9aa3ab; }}
  .funnelctl {{ margin-left: auto; display: flex; align-items: center; gap: 8px; }}
  .funnelctl .muted {{ color: #9aa3ab; }}
  .btn.fbtn {{ background: #1f242b; color: #e9edf1; border-color: #39404a;
              font-size: 12px; padding: 4px 10px; }}
  .btn.fbtn:hover:not(:disabled) {{ background: #262c34; }}
  .btn.fbtn:disabled {{ color: #6b7178; border-color: #2a2f36; cursor: not-allowed; }}
  .ftiles {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .ftile {{ flex: 1 1 0; min-width: 92px; background: #1b1f24; border: 1px solid #2a2f36;
           border-radius: 8px; padding: 8px 10px; }}
  .ftile.money {{ background: #0f2a1c; border-color: #1e5639; }}
  .flabel {{ font-size: 11px; color: #9aa3ab; text-transform: uppercase; letter-spacing: 0.03em; }}
  .fcount {{ font-size: 22px; font-weight: 650; margin: 2px 0 1px; }}
  .fsub {{ font-size: 11px; color: #9aa3ab; display: flex; gap: 6px; align-items: center; }}
  .fconv {{ color: #9aa3ab; }}
  .fno {{ color: #d99b2b; }}
  .fdelta {{ font-size: 12px; font-weight: 600; }}
  .fdelta.up {{ color: #5bd18f; }}
  .fdelta.down {{ color: #f08a8a; }}
  .fzero {{ color: #d99b2b; margin-top: 9px; }}
  .controls {{ position: sticky; top: 0; z-index: 2; background: #f6f7f9;
              border-bottom: 1px solid #dde1e6; padding: 10px 0 12px; margin-bottom: 12px; }}
  .controltop {{ display: grid;
                grid-template-columns: minmax(200px, 1fr) 150px auto auto auto;
                gap: 8px; align-items: center; margin-bottom: 8px; }}
  .variantlabel {{ font-size: 12px; color: #495057; white-space: nowrap;
                  display: flex; align-items: center; gap: 5px; }}
  .search, .sort {{ font: inherit; border: 1px solid #c4cad0; border-radius: 6px;
                   background: white; color: #202124; padding: 7px 9px; min-width: 0; }}
  .visible {{ color: #495057; font-size: 12px; text-align: right; white-space: nowrap; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .statuschips {{ margin-bottom: 7px; }}
  .chip {{ font: inherit; font-size: 12px; border: 1px solid #c9d0d7; border-radius: 999px;
          background: white; color: #2f353b; padding: 4px 9px; cursor: pointer; }}
  .chip b {{ font-weight: 650; color: #697077; margin-left: 3px; }}
  .chip.active {{ background: #12343b; color: white; border-color: #12343b; }}
  .chip.active b {{ color: #d7f3ee; }}
  .chip.facet.active {{ background: #7a4d12; border-color: #7a4d12; }}
  .chip.due {{ border-color: #d99b2b; color: #8a5a00; }}
  .chip.due.active {{ background: #d99b2b; color: white; border-color: #d99b2b; }}
  .chip.due.active b {{ color: #fff3da; }}
  .badge.due {{ color: #8a5a00; background: #fdf0d5; border-radius: 999px;
               padding: 2px 8px; }}
  .card {{ background: white; border: 1px solid #dde1e6; border-radius: 8px;
          padding: 12px 14px; margin-bottom: 12px; }}
  .card.suppressed {{ background: #f4f5f6; border-color: #d6d9dd; opacity: 0.72; }}
  .card.suppressed .btn.log {{ border-color: #c4cad0; color: #9aa3ab;
                              cursor: not-allowed; }}
  .suppbanner {{ color: #8a1c1c; background: #fdeaea; border: 1px solid #f3c2c2;
                border-radius: 6px; padding: 4px 8px; margin-bottom: 8px; }}
  .btn.js-disqualify {{ color: #8a1c1c; border-color: #e3b6b6; }}
  .card.flash {{ animation: flashrow 2.2s ease-out; border-color: #d99b2b; }}
  .cardhead {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }}
  .headright {{ display: flex; gap: 10px; align-items: center; }}
  .nextaction {{ margin: 2px 0 10px; }}
  .chan {{ display: flex; align-items: center; gap: 8px; padding: 5px 0;
          border-top: 1px solid #f0f2f4; flex-wrap: wrap; }}
  .badge {{ margin-left: auto; white-space: nowrap; padding-left: 6px; }}
  .btn {{ font: inherit; font-size: 12.5px; padding: 5px 10px; border-radius: 6px;
         border: 1px solid #c4cad0; background: #fff; cursor: pointer; text-decoration: none;
         color: #202124; display: inline-block; }}
  .btn.launch {{ background: #1a73e8; color: white; border-color: #1a73e8; min-width: 64px;
                text-align: center; }}
  .btn.launch.disabled {{ background: #eceff1; color: #9aa3ab; border-color: #dde1e6;
                         cursor: not-allowed; }}
  .btn.log {{ border-color: #1e8e3e; color: #1e8e3e; }}
  .btn.ghost {{ color: #5f6368; }}
  .btn:hover {{ filter: brightness(0.97); }}
  .contact {{ font: inherit; font-size: 12.5px; padding: 4px 7px; border: 1px solid #d4d8dd;
             border-radius: 6px; width: 190px; }}
  select.js-status {{ font: inherit; font-size: 12.5px; padding: 4px 6px; border-radius: 6px;
             border: 1px solid #c4cad0; }}
  .muted {{ color: #697077; }}
  .small {{ font-size: 12px; }}
  .sent {{ color: #1e8e3e; }}
  code {{ background: #eceff1; padding: 1px 5px; border-radius: 4px; }}
  @keyframes flashrow {{
    0% {{ background: #fff7df; }}
    100% {{ background: white; }}
  }}
  @media (max-width: 760px) {{
    main {{ padding: 12px 12px 44px; }}
    .controltop {{ grid-template-columns: 1fr 1fr; }}
    .search {{ grid-column: 1 / -1; }}
    .visible {{ text-align: left; }}
    .cardhead {{ display: block; }}
    .headright {{ margin-top: 6px; flex-wrap: wrap; }}
    .badge {{ margin-left: 0; }}
  }}
</style>
</head>
<body>
<header>
  <h1>Outreach action panel</h1>
  <div class="meta">
    Human-gated &middot; every button opens a prefilled draft, nothing sends automatically
    &middot; <b>{view.due_count}</b> follow-up{'' if view.due_count == 1 else 's'} due
  </div>
</header>
<main>
{_funnel_scoreboard(funnel)}
{_controls(view)}
{cards}
</main>
<script>
async function post(url, body) {{
  const res = await fetch(url, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(body),
  }});
  if (!res.ok) {{ alert('Action failed: ' + res.status); return; }}
  const place = body.place_id ? '?updated=' + encodeURIComponent(body.place_id) : '';
  location.href = location.pathname + place;
}}
const cards = Array.from(document.querySelectorAll('.card'));
const search = document.getElementById('search');
const sort = document.getElementById('sort');
const variantSelect = document.getElementById('variant');
const visibleCount = document.getElementById('visibleCount');
const clearFilters = document.getElementById('clearFilters');
let statusFilter = 'all';
let dueOnly = false;
let activeVariant = variantSelect ? variantSelect.value : 'demo-link';
const facetFilters = new Set();
if (variantSelect) {{
  variantSelect.addEventListener('change', function () {{ activeVariant = variantSelect.value; }});
}}
function numberValue(value) {{
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) ? parsed : 0;
}}
function sortCards() {{
  const mode = sort.value;
  const sorted = cards.slice().sort(function (a, b) {{
    if (mode === 'due') {{
      return (numberValue(b.dataset.due) - numberValue(a.dataset.due))
        || (a.dataset.nextTouch || '~').localeCompare(b.dataset.nextTouch || '~')
        || (a.dataset.business || '').localeCompare(b.dataset.business || '');
    }}
    if (mode === 'recent_touch') {{
      return (b.dataset.lastTouch || '').localeCompare(a.dataset.lastTouch || '');
    }}
    if (mode === 'business') {{
      return (a.dataset.business || '').localeCompare(b.dataset.business || '');
    }}
    if (mode === 'city') {{
      return (a.dataset.city || '').localeCompare(b.dataset.city || '')
        || (a.dataset.business || '').localeCompare(b.dataset.business || '');
    }}
    if (mode === 'sends') {{
      return numberValue(b.dataset.sends) - numberValue(a.dataset.sends)
        || (a.dataset.business || '').localeCompare(b.dataset.business || '');
    }}
    return numberValue(a.dataset.priority) - numberValue(b.dataset.priority)
      || (a.dataset.city || '').localeCompare(b.dataset.city || '')
      || (a.dataset.business || '').localeCompare(b.dataset.business || '');
  }});
  const main = document.querySelector('main');
  sorted.forEach(function (card) {{ main.appendChild(card); }});
}}
function applyFilters() {{
  const needle = (search.value || '').trim().toLowerCase();
  let shown = 0;
  cards.forEach(function (card) {{
    const tags = new Set((card.dataset.tags || '').split(/\\s+/).filter(Boolean));
    const matchesSearch = !needle || (card.dataset.search || '').includes(needle);
    const matchesStatus = statusFilter === 'all' || card.dataset.status === statusFilter;
    const matchesFacets = Array.from(facetFilters).every(function (facet) {{
      return tags.has(facet);
    }});
    const matchesDue = !dueOnly || card.dataset.due === '1';
    const visible = matchesSearch && matchesStatus && matchesFacets && matchesDue;
    card.hidden = !visible;
    if (visible) {{ shown += 1; }}
  }});
  visibleCount.textContent = shown + ' shown';
  sortCards();
}}
document.querySelectorAll('[data-status-filter]').forEach(function (el) {{
  el.addEventListener('click', function () {{
    document.querySelectorAll('[data-status-filter]').forEach(function (button) {{
      button.classList.remove('active');
    }});
    el.classList.add('active');
    statusFilter = el.dataset.statusFilter;
    applyFilters();
  }});
}});
const dueChip = document.querySelector('[data-due-filter]');
if (dueChip) {{
  dueChip.addEventListener('click', function () {{
    dueOnly = !dueOnly;
    dueChip.classList.toggle('active', dueOnly);
    if (dueOnly) {{ sort.value = 'due'; }}
    applyFilters();
  }});
}}
document.querySelectorAll('[data-facet-filter]').forEach(function (el) {{
  el.addEventListener('click', function () {{
    const facet = el.dataset.facetFilter;
    if (facetFilters.has(facet)) {{
      facetFilters.delete(facet);
      el.classList.remove('active');
    }} else {{
      facetFilters.add(facet);
      el.classList.add('active');
    }}
    applyFilters();
  }});
}});
search.addEventListener('input', applyFilters);
sort.addEventListener('change', applyFilters);
clearFilters.addEventListener('click', function () {{
  search.value = '';
  statusFilter = 'all';
  dueOnly = false;
  facetFilters.clear();
  document.querySelectorAll('.chip').forEach(function (el) {{ el.classList.remove('active'); }});
  document.querySelector('[data-status-filter="all"]').classList.add('active');
  sort.value = 'priority';
  applyFilters();
}});
document.querySelectorAll('.js-log').forEach(function (el) {{
  el.addEventListener('click', function () {{
    post('/dashboard/outreach/touch', {{
      place_id: el.dataset.place,
      channel: el.dataset.channel,
      variant: activeVariant,
    }});
  }});
}});
document.querySelectorAll('.js-disqualify').forEach(function (el) {{
  el.addEventListener('click', function () {{
    const reason = prompt('Disqualify & suppress this prospect. Reason?');
    if (reason === null) {{ return; }}
    post('/dashboard/outreach/disqualify', {{
      place_id: el.dataset.place, reason: reason,
    }});
  }});
}});
document.querySelectorAll('.js-save').forEach(function (el) {{
  el.addEventListener('click', function () {{
    const input = document.getElementById(el.dataset.target);
    post('/dashboard/outreach/contact', {{
      place_id: el.dataset.place, field: el.dataset.field, value: input.value,
    }});
  }});
}});
document.querySelectorAll('.js-status').forEach(function (el) {{
  el.addEventListener('change', function () {{
    post('/dashboard/outreach/status', {{ place_id: el.dataset.place, status: el.value }});
  }});
}});
document.querySelectorAll('.js-copy').forEach(function (el) {{
  el.addEventListener('click', function () {{
    navigator.clipboard.writeText(el.dataset.copy || '');
    el.textContent = 'copied';
    setTimeout(function () {{ el.textContent = 'copy'; }}, 1200);
  }});
}});
const updated = new URLSearchParams(location.search).get('updated');
if (updated) {{
  const card = document.querySelector('[data-place="' + CSS.escape(updated) + '"]');
  if (card) {{
    card.classList.add('flash');
    card.scrollIntoView({{ block: 'center' }});
  }}
}}
(function () {{
  const btn = document.getElementById('funnelRefresh');
  if (!btn) {{ return; }}
  const status = document.getElementById('funnelStatus');
  const cooldownMs = (Number(btn.dataset.cooldown) || 0) * 1000;
  const stamped = btn.dataset.updated ? Date.parse(btn.dataset.updated) : 0;
  let readyAt = stamped ? stamped + cooldownMs : 0;
  function render() {{
    const remaining = readyAt - Date.now();
    if (remaining > 0) {{
      btn.disabled = true;
      status.textContent = 'cooldown ' + Math.ceil(remaining / 1000) + 's';
      setTimeout(render, 1000);
    }} else {{
      btn.disabled = false;
      if ((status.textContent || '').indexOf('cooldown') === 0) {{ status.textContent = ''; }}
    }}
  }}
  btn.addEventListener('click', async function () {{
    btn.disabled = true;
    status.textContent = 'computing\\u2026';
    try {{
      const res = await fetch('/dashboard/outreach/funnel/refresh', {{
        method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: '{{}}',
      }});
      if (res.status === 429) {{
        const data = await res.json().catch(function () {{ return {{}}; }});
        const secs = (data.detail && data.detail.remaining_seconds)
          || Math.ceil(cooldownMs / 1000);
        readyAt = Date.now() + secs * 1000;
        render();
        return;
      }}
      if (!res.ok) {{ status.textContent = 'failed'; btn.disabled = false; return; }}
      status.textContent = 'updated';
      location.reload();
    }} catch (err) {{
      status.textContent = 'failed';
      btn.disabled = false;
    }}
  }});
  render();
}})();
applyFilters();
</script>
</body>
</html>
"""


__all__ = ["render_outreach_html"]
