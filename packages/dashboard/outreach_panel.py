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
    return f"<span class='btn launch disabled' title='Add a contact value to enable'>{_e(button.label)}</span>"


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


def _row_block(row: ActionRow, statuses: list[str]) -> str:
    site = (
        f"<a href='{_e(row.mockup_url)}' target='_blank' rel='noopener'>preview site</a>"
        if row.mockup_url
        else ""
    )
    channels = "".join(_channel_row(row, b) for b in row.buttons)
    return f"""
  <div class="card">
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
  .card {{ background: white; border: 1px solid #dde1e6; border-radius: 8px;
          padding: 12px 14px; margin-bottom: 12px; }}
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
</style>
</head>
<body>
<header>
  <h1>Outreach action panel</h1>
  <div class="meta">Human-gated &middot; every button opens a prefilled draft, nothing sends automatically</div>
</header>
<main>
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
  location.reload();
}}
document.querySelectorAll('.js-log').forEach(function (el) {{
  el.addEventListener('click', function () {{
    post('/dashboard/outreach/touch', {{ place_id: el.dataset.place, channel: el.dataset.channel }});
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
</script>
</body>
</html>
"""


__all__ = ["render_outreach_html"]
