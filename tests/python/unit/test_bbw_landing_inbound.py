"""BBW landing form + Netlify function + typed inbound contract (drift guards)."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
# The review form lives on its own /free-review route (multi-page split, 2026-06-07).
REVIEW_FORM_PAGE = REPO / "products" / "better-business-web" / "site" / "src" / "pages" / "free-review.astro"
FUNCTION = REPO / "products" / "better-business-web" / "site" / "netlify" / "functions" / "website-review.mjs"
PULL_SCRIPT = REPO / "scripts" / "web" / "pull-inbound.mjs"
THANKS_PAGE = REPO / "products" / "better-business-web" / "site" / "src" / "pages" / "thanks.astro"

# Fields the function persists and WebsiteReviewRequest round-trips.
INBOUND_FIELDS = frozenset(
    {"submission_id", "name", "contact", "business", "website", "interest", "received_at", "source"}
)


def test_landing_form_posts_to_function() -> None:
    text = REVIEW_FORM_PAGE.read_text(encoding="utf-8")
    assert 'name="website-review"' in text
    assert 'method="POST"' in text
    assert 'action="/.netlify/functions/website-review"' in text
    assert 'name="bot-field"' in text
    for field in ("name", "business", "website", "contact"):
        assert f'name="{field}"' in text
    # The three-audience intent selector (preview / review / both).
    assert 'name="interest"' in text
    for value in ("preview", "review", "both"):
        assert f'value: "{value}"' in text


def test_website_review_function_contract() -> None:
    text = FUNCTION.read_text(encoding="utf-8")
    assert 'getStore("inbound-reviews")' in text
    assert 'field("bot-field")' in text
    assert 'redirect(req, "/thanks/")' in text
    assert "submission_id" in text
    for key in ("name", "contact", "business", "website", "interest", "received_at", "source"):
        assert key in text


def test_inbound_payload_keys_match_typed_model() -> None:
    """Keys written by the Netlify function must match WebsiteReviewRequest."""
    text = FUNCTION.read_text(encoding="utf-8")
    block = re.search(r"const submission = \{([^}]+)\}", text, re.DOTALL)
    assert block is not None
    body = block.group(1)
    for key in INBOUND_FIELDS:
        assert key in body, f"submission object missing {key!r}"
    assert "store.setJSON(submission.submission_id" in text


def test_pull_inbound_script_targets_platform_store() -> None:
    text = PULL_SCRIPT.read_text(encoding="utf-8")
    assert "inbound-reviews" in text
    assert "state/prospects/inbound" in text.replace("\\", "/")


def test_thanks_page_exists() -> None:
    assert THANKS_PAGE.is_file()
