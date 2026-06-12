"""Server-rendered HTML for the outreach action panel.

Deliberately *not* the 5s auto-refreshing ops dashboard — this page is
interactive (inline edits, button clicks) and a periodic refresh would wipe a
half-typed contact field. Actions POST to the endpoint and the page reloads on
success, so the server stays the single source of truth and the JS stays tiny.
"""

from __future__ import annotations

import html

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
    return f"""
    <div class="chan">
      {_launch(button)}
      <button class="btn log js-log" data-place="{_e(row.place_id)}"
              data-channel="{_e(button.channel)}">&#10003; Log sent</button>
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
        f"<button class='chip active' data-status-filter='all'>All <b>{len(view.rows)}</b></button>"
    ]
    buttons.extend(
        f"<button class='chip' data-status-filter='{_e(status)}'>"
        f"{_e(_label(status))} <b>{counts.get(status, 0)}</b></button>"
        for status in view.statuses
    )
    return "".join(buttons)


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
        <option value="recent_touch" data-sort='recent_touch'>Recently touched</option>
        <option value="business" data-sort='business'>Business A-Z</option>
        <option value="city" data-sort='city'>City</option>
        <option value="sends" data-sort='sends'>Most sends</option>
      </select>
      <button class="btn ghost" id="clearFilters">clear</button>
      <span class="visible" id="visibleCount">{len(view.rows)} shown</span>
    </div>
    <div class="chips statuschips">{_status_controls(view)}</div>
    <div class="chips facetchips">{_facet_controls(view)}</div>
  </section>"""


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
    return f"""
  <div class="card" data-place="{_e(row.place_id)}" data-status="{_e(row.status)}"
       data-tags="{_e(tags)}" data-search="{_e(search)}"
       data-business="{_e(row.business_name.lower())}" data-city="{_e(row.city.lower())}"
       data-sends="{row.facts.total_sent_count}" data-last-touch="{_e(row.facts.last_sent_at)}"
       data-priority="{priority}">
    <div class="cardhead">
      <div>
        <b>{_e(row.business_name)}</b>
        <span class="muted small">{_e(row.genre_id)} &middot; {_e(row.city)}</span>
      </div>
      <div class="headright">
        {site}
        {_status_select(row, statuses)}
      </div>
    </div>
    <div class="muted small nextaction">{_e(row.next_action)}</div>
    {channels}
  </div>"""


def render_outreach_html(view: OutreachPanelView) -> str:
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
  .controls {{ position: sticky; top: 0; z-index: 2; background: #f6f7f9;
              border-bottom: 1px solid #dde1e6; padding: 10px 0 12px; margin-bottom: 12px; }}
  .controltop {{ display: grid; grid-template-columns: minmax(220px, 1fr) 160px auto auto;
                gap: 8px; align-items: center; margin-bottom: 8px; }}
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
  .card {{ background: white; border: 1px solid #dde1e6; border-radius: 8px;
          padding: 12px 14px; margin-bottom: 12px; }}
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
  </div>
</header>
<main>
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
const visibleCount = document.getElementById('visibleCount');
const clearFilters = document.getElementById('clearFilters');
let statusFilter = 'all';
const facetFilters = new Set();
function numberValue(value) {{
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) ? parsed : 0;
}}
function sortCards() {{
  const mode = sort.value;
  const sorted = cards.slice().sort(function (a, b) {{
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
    const visible = matchesSearch && matchesStatus && matchesFacets;
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
applyFilters();
</script>
</body>
</html>
"""


__all__ = ["render_outreach_html"]
