from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from packages.agency import outreach_messages as msg


def _record() -> dict:
    return {
        "display_name": "Joe's Auto",
        "genre_id": "auto_repair",
        "city_id": "los_angeles",
        "mockup_url": "https://preview.example.test",
        "user_ratings_total": 40,
    }


def test_messages_mention_business_and_url_without_em_dash() -> None:
    m = msg.build_messages(_record())
    for text in (m.email_body, m.sms_body, m.dm_body, m.call_script):
        assert "—" not in text  # GTM lane: no machine-written tell
        assert "https://preview.example.test" in text
    assert "Joe's Auto" in m.email_subject


def test_email_body_carries_opt_out_line() -> None:
    m = msg.build_messages(_record())
    assert 'Reply "no thanks" and I won\'t email again.' in m.email_body


def test_ref_token_appears_below_signature_email_only() -> None:
    from packages.agency.outreach import bbw_ref_token

    record = {**_record(), "place_id": "ChIJ_msg_test"}
    token = bbw_ref_token("ChIJ_msg_test")
    m = msg.build_messages(record)
    # Quiet ref line, last thing in the email, after the website signature.
    assert m.email_body.rstrip().endswith(f"ref: {token}")
    # Email only — SMS/DM/call stay clean (those replies are logged manually).
    assert token not in m.sms_body
    assert token not in m.dm_body
    assert token not in m.call_script
    # Survives the no-em-dash sanitizer untouched.
    assert "—" not in m.email_body


def test_no_ref_token_without_place_id() -> None:
    m = msg.build_messages(_record())  # _record() has no place_id
    assert "ref: BBW-" not in m.email_body


def test_gmail_compose_url_encodes_fields() -> None:
    url = msg.gmail_compose_url(to="a@b.com", subject="Hi there", body="line one\nline two")
    parsed = urlparse(url)
    assert parsed.netloc == "mail.google.com"
    qs = parse_qs(parsed.query)
    assert qs["view"] == ["cm"]
    assert qs["to"] == ["a@b.com"]
    assert qs["su"] == ["Hi there"]
    assert "line one\nline two" == qs["body"][0]


def test_sms_and_tel_normalize_phone() -> None:
    assert msg.sms_url("(503) 555-1234", "hey").startswith("sms:5035551234&body=")
    assert msg.tel_url("+1 (503) 555-1234") == "tel:+15035551234"


def test_social_urls_handle_and_full_url() -> None:
    assert msg.facebook_url("JoesAuto") == "https://www.facebook.com/JoesAuto"
    assert msg.facebook_url("https://fb.com/JoesAuto") == "https://fb.com/JoesAuto"
    assert msg.instagram_url("@joes.auto") == "https://instagram.com/joes.auto"
    assert msg.instagram_url("") == ""
