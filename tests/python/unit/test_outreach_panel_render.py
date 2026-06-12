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
    assert "data-sort='recent_touch'" in html_out
    assert 'data-tags="preview email-not-sent phone-present any-contact any-sent"' in html_out


def test_render_escapes_business_name() -> None:
    html_out = render_outreach_html(_view())
    assert "Joe&#x27;s &lt;Auto&gt; Shop" in html_out
    assert "<Auto>" not in html_out


def test_render_empty_view_has_hint() -> None:
    html_out = render_outreach_html(OutreachPanelView(rows=[], statuses=[]))
    assert "No deployed prospects" in html_out
