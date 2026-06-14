from __future__ import annotations

from packages.agency.outreach_actions import (
    ActionRow,
    ChannelButton,
    FacetOption,
    OutreachPanelView,
    RowFacts,
)
from packages.dashboard.outreach_panel import render_outreach_html


def _view() -> OutreachPanelView:
    row = ActionRow(
        place_id="p1",
        business_name="Joe's <Auto> Shop",
        city="Los Angeles",
        genre_id="auto_repair",
        status="ready_to_send",
        next_action="Review draft, send manually",
        mockup_url="https://preview.example.test",
        facts=RowFacts(
            tags=[
                "preview",
                "email-not-sent",
                "phone-present",
                "any-contact",
                "any-sent",
            ],
            total_sent_count=2,
        ),
        buttons=[
            ChannelButton(
                channel="email",
                label="Email",
                contact_field="contact_email",
                contact_value="",
                enabled=False,
                url="",
                copy="hello body",
            ),
            ChannelButton(
                channel="sms",
                label="SMS",
                contact_field="phone",
                contact_value="+15035550000",
                enabled=True,
                url="sms:+15035550000&body=hi",
                copy="hi",
                sent_count=2,
                last_sent_at="2026-06-03T00:00:00Z",
            ),
        ],
    )
    return OutreachPanelView(
        rows=[row],
        statuses=["ready_to_send", "sent", "replied"],
        facets=[
            FacetOption(key="preview", label="Preview site", count=1),
            FacetOption(key="email-not-sent", label="Email not sent", count=1),
        ],
        variants=["demo-link", "short", "social-proof"],
        default_variant="demo-link",
    )


def _suppressed_row() -> ActionRow:
    return ActionRow(
        place_id="p9",
        business_name="Closed Co",
        city="Portland",
        genre_id="auto_repair",
        status="do_not_contact",
        next_action="Suppress all outreach",
        mockup_url="",
        buttons=[
            ChannelButton(
                channel="email",
                label="Email",
                contact_field="contact_email",
                contact_value="x@y.com",
                enabled=False,
                url="",
                copy="body",
            )
        ],
        suppressed=True,
        suppression_reason="owner asked to stop",
    )


def _due_row() -> ActionRow:
    return ActionRow(
        place_id="p7",
        business_name="Due Diner",
        city="Portland",
        genre_id="restaurant",
        status="sent",
        next_action="Send manual follow-up",
        mockup_url="",
        next_touch_at="2026-06-05T00:00:00Z",
        due=True,
    )


def test_render_contains_core_elements() -> None:
    html_out = render_outreach_html(_view())
    assert "Outreach action panel" in html_out
    assert "nothing sends automatically" in html_out
    # disabled launch for the email button (no contact value)
    assert "launch disabled" in html_out
    # enabled launch anchor for sms
    assert "sms:+15035550000&amp;body=hi" in html_out
    # touch badge
    assert "sent &times;2" in html_out
    # status dropdown with current value selected
    assert "<option value='ready_to_send' selected>" in html_out


def test_render_contains_filter_and_sort_controls() -> None:
    html_out = render_outreach_html(_view())
    assert "placeholder='Search businesses, cities, or types'" in html_out
    assert "data-status-filter='sent'" in html_out
    assert "data-facet-filter='preview'" in html_out
    assert "data-filter-type='status'" in html_out
    assert "data-filter-type='facet'" in html_out
    assert "draggable='true'" in html_out
    assert "data-sort='recent_touch'" in html_out
    assert 'data-tags="preview email-not-sent phone-present any-contact any-sent"' in html_out


def test_render_contains_include_exclude_filter_builder() -> None:
    html_out = render_outreach_html(_view())
    assert 'id="includeZone"' in html_out
    assert 'id="excludeZone"' in html_out
    assert 'id="includeTokens"' in html_out
    assert 'id="excludeTokens"' in html_out
    assert "include these filters" in html_out
    assert "exclude these filters" in html_out
    assert "const includeFilters = new Map()" in html_out
    assert "const excludeFilters = new Map()" in html_out
    assert "let activeZone = 'include'" in html_out
    assert "function persistState()" in html_out
    assert "function restoreStateFromUrl()" in html_out
    assert "writeStateParams(params)" in html_out


def test_render_filter_tokens_can_drag_out_to_remove() -> None:
    html_out = render_outreach_html(_view())
    assert "token.draggable = true" in html_out
    assert "let draggingTokenId = ''" in html_out
    assert "document.addEventListener('drop'" in html_out
    assert "removeFilter(draggingTokenId)" in html_out


def test_render_escapes_business_name() -> None:
    html_out = render_outreach_html(_view())
    assert "Joe&#x27;s &lt;Auto&gt; Shop" in html_out
    assert "<Auto>" not in html_out


def test_render_empty_view_has_hint() -> None:
    html_out = render_outreach_html(OutreachPanelView(rows=[], statuses=[]))
    assert "No deployed prospects" in html_out


def test_render_includes_variant_selector() -> None:
    html_out = render_outreach_html(_view())
    assert "id='variant'" in html_out
    assert "<option value='social-proof'" in html_out
    assert "<option value='demo-link' selected>" in html_out


def test_render_due_chip_and_badge() -> None:
    view = OutreachPanelView(
        rows=[_due_row()],
        statuses=["sent"],
        variants=["demo-link"],
        due_count=1,
    )
    html_out = render_outreach_html(view)
    assert "data-due-filter='1'" in html_out
    assert "data-sort='due'" in html_out
    assert 'data-due="1"' in html_out
    assert "<b>1</b> follow-up due" in html_out
    assert "due 2026-06-05" in html_out


def test_render_suppressed_card_is_greyed_and_disabled() -> None:
    view = OutreachPanelView(
        rows=[_suppressed_row()], statuses=["do_not_contact"], variants=["demo-link"]
    )
    html_out = render_outreach_html(view)
    assert 'class="card suppressed"' in html_out
    assert 'data-suppressed="1"' in html_out
    assert "Suppressed &mdash; owner asked to stop" in html_out
    # the log button is rendered disabled (not a js-log click target)
    assert "btn log disabled" in html_out
    # no disqualify *button* on an already-suppressed card (CSS rule aside)
    assert "js-disqualify' data-place='p9'" not in html_out
