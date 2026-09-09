"""Phase 3.1 — magic-link approval token integration tests.

Covers TTL, single-use, second-factor (P0), tampered-signature rejection,
device-fingerprint mismatch, and the FastAPI confirm endpoint.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from apps.api.approval_endpoint import APPROVAL_SECRET_ENV_VAR
from apps.api.control_plane import ControlPlaneService
from apps.api.main import app
from packages.db.approval_token_store import ApprovalTokenStore
from packages.policies.approval_tokens import (
    DEFAULT_TTL,
    P0_SECOND_FACTOR_WINDOW,
    P0_TTL,
    DeviceMismatch,
    SecondFactorOutOfWindow,
    TokenAlreadyBurned,
    TokenExpired,
    TokenSignatureInvalid,
    issue_token,
    record_second_factor,
    verify_and_burn_token,
)
from packages.schemas.approval import ApprovalStatus

SECRET = b"\x11" * 32


@pytest.fixture(autouse=True)
def _approval_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    # The endpoint shares the approval primitive's hex-encoded signing-key
    # contract. This is a deterministic test-only value; no credential source
    # is read by the suite.
    monkeypatch.setenv(APPROVAL_SECRET_ENV_VAR, SECRET.hex())


def _mk_store(isolated_repo_root) -> ApprovalTokenStore:
    return ApprovalTokenStore()


def _issue(
    store,
    *,
    action: str = "review_task",
    approval_id: str = "approval-test-1",
    subject_id: str = "task-test-1",
    now: datetime | None = None,
    expected_device: str | None = None,
):
    return issue_token(
        approval_id=approval_id,
        subject_id=subject_id,
        action=action,
        secret=SECRET,
        store=store,
        expected_device_fingerprint=expected_device,
        now=now,
    )


def test_happy_path_default_ttl_burns_once(isolated_repo_root) -> None:
    store = _mk_store(isolated_repo_root)
    token = _issue(store)

    burned = verify_and_burn_token(
        token_id=token.token_id,
        provided_signature=token.signature,
        device_fingerprint="mac-local",
        secret=SECRET,
        store=store,
    )
    assert burned.burn_count == 1
    assert burned.approved_at is not None
    assert "approved" in burned.transitions

    with pytest.raises(TokenAlreadyBurned):
        verify_and_burn_token(
            token_id=token.token_id,
            provided_signature=token.signature,
            device_fingerprint="mac-local",
            secret=SECRET,
            store=store,
        )


def test_concurrent_burns_allow_exactly_one_success(isolated_repo_root, monkeypatch) -> None:
    """A single token may be consumed once even when confirmations overlap."""
    store = _mk_store(isolated_repo_root)
    token = _issue(store)
    original_load = store.load
    both_attempts_loaded = threading.Barrier(2)

    def synchronized_load(token_id: str):
        record = original_load(token_id)
        both_attempts_loaded.wait(timeout=2)
        return record

    monkeypatch.setattr(store, "load", synchronized_load)
    outcomes: list[object] = []

    def burn() -> None:
        try:
            outcomes.append(
                verify_and_burn_token(
                    token_id=token.token_id,
                    provided_signature=token.signature,
                    device_fingerprint="mac-local",
                    secret=SECRET,
                    store=store,
                )
            )
        except Exception as exc:  # asserted below
            outcomes.append(exc)

    attempts = [threading.Thread(target=burn) for _ in range(2)]
    for attempt in attempts:
        attempt.start()
    for attempt in attempts:
        attempt.join(timeout=3)

    assert not any(attempt.is_alive() for attempt in attempts)
    assert sum(not isinstance(outcome, Exception) for outcome in outcomes) == 1
    assert sum(isinstance(outcome, TokenAlreadyBurned) for outcome in outcomes) == 1


def test_expired_token_rejected(isolated_repo_root) -> None:
    store = _mk_store(isolated_repo_root)
    issued = datetime.now(timezone.utc) - DEFAULT_TTL - timedelta(seconds=10)
    token = _issue(store, now=issued)

    with pytest.raises(TokenExpired):
        verify_and_burn_token(
            token_id=token.token_id,
            provided_signature=token.signature,
            device_fingerprint="mac-local",
            secret=SECRET,
            store=store,
        )


def test_tampered_signature_rejected(isolated_repo_root) -> None:
    store = _mk_store(isolated_repo_root)
    token = _issue(store)
    with pytest.raises(TokenSignatureInvalid):
        verify_and_burn_token(
            token_id=token.token_id,
            provided_signature=token.signature + "tamper",
            device_fingerprint="mac-local",
            secret=SECRET,
            store=store,
        )


def test_device_fingerprint_mismatch(isolated_repo_root) -> None:
    store = _mk_store(isolated_repo_root)
    token = _issue(store, expected_device="mac-home")
    with pytest.raises(DeviceMismatch):
        verify_and_burn_token(
            token_id=token.token_id,
            provided_signature=token.signature,
            device_fingerprint="mac-other",
            secret=SECRET,
            store=store,
        )


def test_p0_token_has_short_ttl_and_second_factor(isolated_repo_root) -> None:
    store = _mk_store(isolated_repo_root)
    token = _issue(store, action="submit_appstore")
    assert token.action_class == "p0"
    assert token.ttl_seconds == int(P0_TTL.total_seconds())

    burned = verify_and_burn_token(
        token_id=token.token_id,
        provided_signature=token.signature,
        device_fingerprint="mac-local",
        secret=SECRET,
        store=store,
    )
    # second factor within window
    sf = record_second_factor(
        token_id=token.token_id,
        provided_signature=token.signature,
        device_fingerprint="mac-local",
        secret=SECRET,
        store=store,
        now=datetime.fromisoformat(burned.approved_at) + timedelta(seconds=10),
    )
    assert sf.second_factor_at is not None
    assert "second_factor" in sf.transitions


def test_p0_second_factor_out_of_window(isolated_repo_root) -> None:
    store = _mk_store(isolated_repo_root)
    token = _issue(store, action="submit_appstore")
    burned = verify_and_burn_token(
        token_id=token.token_id,
        provided_signature=token.signature,
        device_fingerprint="mac-local",
        secret=SECRET,
        store=store,
    )
    too_late = datetime.fromisoformat(burned.approved_at) + P0_SECOND_FACTOR_WINDOW + timedelta(seconds=5)
    with pytest.raises(SecondFactorOutOfWindow):
        record_second_factor(
            token_id=token.token_id,
            provided_signature=token.signature,
            device_fingerprint="mac-local",
            secret=SECRET,
            store=store,
            now=too_late,
        )


# ── FastAPI endpoint ─────────────────────────────────────────────


def test_magic_link_confirm_endpoint_flips_approval(isolated_repo_root) -> None:
    client = TestClient(app)
    service = ControlPlaneService()
    goal = service.create_goal(title="g", summary="s")
    approval = service.request_approval(
        summary="approve the thing",
        subject_type="task",
        subject_id="task-abc",
        action="review_task",
        approval_type="review_task",
    )
    store = ApprovalTokenStore()
    token = _issue(
        store,
        action="review_task",
        approval_id=approval.id,
        subject_id="task-abc",
    )

    page = client.get(f"/magic/approvals/{token.token_id}")
    assert page.status_code == 200
    assert token.signature in page.text

    confirm = client.post(
        f"/magic/approvals/{token.token_id}/confirm",
        data={"signature": token.signature, "device_fingerprint": "mac-local"},
    )
    assert confirm.status_code == 200, confirm.text
    body = confirm.json()
    assert body["status"] == "approved"
    reloaded = service.approvals.load(approval.id)
    assert reloaded.status is ApprovalStatus.APPROVED


def test_magic_link_page_escapes_token_fields_as_html(isolated_repo_root) -> None:
    client = TestClient(app)
    store = ApprovalTokenStore()
    token = _issue(
        store,
        action='review <img src=x onerror="alert(1)">',
        subject_id='task"><script>alert(1)</script>',
    )

    page = client.get(f"/magic/approvals/{token.token_id}")

    assert page.status_code == 200
    assert '<script>alert(1)</script>' not in page.text
    assert '<img src=x onerror="alert(1)">' not in page.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page.text
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in page.text


def test_magic_link_p0_requires_two_clicks(isolated_repo_root) -> None:
    client = TestClient(app)
    service = ControlPlaneService()
    approval = service.request_approval(
        summary="submit catchbook",
        subject_type="release",
        subject_id="release-catchbook-v0.1.0",
        action="submit_appstore",
        approval_type="app_store_submission",
    )
    store = ApprovalTokenStore()
    token = _issue(
        store,
        action="submit_appstore",
        approval_id=approval.id,
        subject_id="release-catchbook-v0.1.0",
    )

    first = client.post(
        f"/magic/approvals/{token.token_id}/confirm",
        data={"signature": token.signature, "device_fingerprint": "mac-local"},
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "awaiting_second_factor"
    # Approval still PENDING after first click — P0 requires second factor
    assert service.approvals.load(approval.id).status is ApprovalStatus.PENDING

    second = client.post(
        f"/magic/approvals/{token.token_id}/second-factor",
        data={"signature": token.signature, "device_fingerprint": "mac-local"},
    )
    assert second.status_code == 200, second.text
    assert service.approvals.load(approval.id).status is ApprovalStatus.APPROVED


def test_second_confirmation_cannot_be_replayed(isolated_repo_root):
    store = _mk_store(isolated_repo_root)
    token = _issue(store, action="submit_appstore")
    args = dict(token_id=token.token_id, provided_signature=token.signature,
                device_fingerprint="local-device", secret=SECRET, store=store)
    verify_and_burn_token(**args)
    record_second_factor(**args)
    with pytest.raises(TokenAlreadyBurned):
        record_second_factor(**args)


def test_second_confirmation_uses_the_first_confirmed_device(isolated_repo_root):
    store = _mk_store(isolated_repo_root)
    token = _issue(store, action="submit_appstore")
    args = dict(token_id=token.token_id, provided_signature=token.signature,
                secret=SECRET, store=store)
    verify_and_burn_token(**args, device_fingerprint="first-device")
    with pytest.raises(DeviceMismatch):
        record_second_factor(**args, device_fingerprint="different-device")


class _ApprovalForm(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.action = ""
        self.fields = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.action = attrs["action"]
        if tag == "input" and "name" in attrs:
            self.fields[attrs["name"]] = attrs.get("value", "")


def test_browser_can_follow_both_rendered_p0_forms(isolated_repo_root):
    client = TestClient(app)
    service = ControlPlaneService()
    approval = service.request_approval(
        summary="Review staged skill change", subject_type="skill_evolution_proposal",
        subject_id="test-skill", action="skill_evolution_apply",
        approval_type="skill_evolution_apply",
    )
    token = _issue(ApprovalTokenStore(), action=approval.action,
                   approval_id=approval.id, subject_id=approval.subject_id,
                   expected_device="review-device")
    page_url = f"/magic/approvals/{token.token_id}"
    first_form = _ApprovalForm(client.get(page_url).text)
    first = client.post(first_form.action, data=first_form.fields,
                        headers={"accept": "text/html"})
    assert first.status_code == 200
    assert service.approvals.load(approval.id).status is ApprovalStatus.PENDING
    second_form = _ApprovalForm(first.text)
    assert second_form.action.endswith("/second-factor")
    second = client.post(second_form.action, data=second_form.fields)
    assert second.status_code == 200
    assert service.approvals.load(approval.id).status is ApprovalStatus.APPROVED
