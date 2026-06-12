"""Runtime-supervised reply-sync poller (agency layer, item 5).

Reads the BBW inbox **read-only** (Gmail API, ``gmail.readonly`` scope), matches
each new inbound message back to a prospect by its ``BBW-<6char>`` token (sender
address as fallback), and hands it to ``packages.agency.reply_sync.process_reply``
— which advances the lane row to ``replied``, logs an inbound touch, drops an
operator snippet, and suppresses STOP-intent replies. It never sends, labels,
moves, or marks mail read.

Mirrors ``apps/worker-billing-poller``: a periodic loop run by the
**runtime-supervisor** (launchd runs only the supervisor — no standalone plist).
Idempotent across restarts via a persisted Gmail ``historyId`` cursor plus a
processed-thread set in ``state/prospects/outreach-lane/reply-sync-state.json``.

Setup (one-time, interactive — the only non-headless step):
    python apps/worker-reply-sync/main.py --auth
Single cycle:
    python apps/worker-reply-sync/main.py --once
Env:
    BBW_GMAIL_CREDENTIALS  OAuth client-secret JSON (default state/secrets/gmail-credentials.json)
    BBW_GMAIL_TOKEN        stored user token JSON   (default state/secrets/gmail-token.json)
    BBW_GMAIL_ADDRESS      our own address, to skip self-sent mail (optional)
    AGENCY_REPLY_SYNC_POLL_INTERVAL_SECS   loop interval, default 120
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.agency.outreach_lane import default_outreach_lane_root  # noqa: E402
from packages.agency.reply_sync import ParsedReply, process_reply  # noqa: E402

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
DEFAULT_INTERVAL = 120
INITIAL_QUERY = "in:inbox newer_than:14d"  # first-run backfill window


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[reply-sync {ts}] {msg}", flush=True)


def _creds_path() -> Path:
    default = ROOT / "state" / "secrets" / "gmail-credentials.json"
    return Path(os.environ.get("BBW_GMAIL_CREDENTIALS", default))


def _token_path() -> Path:
    return Path(
        os.environ.get("BBW_GMAIL_TOKEN", ROOT / "state" / "secrets" / "gmail-token.json")
    )


def _state_path() -> Path:
    return default_outreach_lane_root(ROOT) / "reply-sync-state.json"


def _load_state() -> dict:
    path = _state_path()
    if not path.exists():
        return {"history_id": None, "processed_thread_ids": []}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"history_id": None, "processed_thread_ids": []}
    data.setdefault("history_id", None)
    data.setdefault("processed_thread_ids", [])
    return data


def _save_state(state: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the processed-thread set bounded; the history cursor is the primary
    # idempotency guard, this is belt-and-suspenders for the backfill window.
    state["processed_thread_ids"] = list(state.get("processed_thread_ids", []))[-2000:]
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


# ------------------------------------------------------------------- Gmail I/O
def _import_gmail():
    """Lazy import so the worker module loads (and registers) without the
    optional reply-sync deps installed. Returns the two callables we need."""
    try:
        from google.oauth2.credentials import Credentials  # noqa: F401
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - depends on optional extras
        raise RuntimeError(
            f"cannot import Gmail client ({exc}); install with: "
            "pip install -e '.[reply-sync]' (into the env running this script)"
        ) from exc
    return Credentials, build


def _build_service():
    Credentials, build = _import_gmail()
    token_path = _token_path()
    if not token_path.exists():
        raise RuntimeError(
            f"no Gmail token at {token_path}; run: python apps/worker-reply-sync/main.py --auth"
        )
    creds = Credentials.from_authorized_user_file(str(token_path), [GMAIL_READONLY_SCOPE])
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def authorize() -> int:
    """One-time interactive OAuth to mint a readonly token. Headless thereafter."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        _log(f"cannot import google-auth-oauthlib ({exc}).")
        _log("install with: pip install -e '.[reply-sync]' (into the env running this script)")
        return 1
    creds_path = _creds_path()
    if not creds_path.exists():
        _log(f"missing OAuth client secret at {creds_path}; download it from Google Cloud Console")
        return 1
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), [GMAIL_READONLY_SCOPE])
    creds = flow.run_local_server(port=0)
    token_path = _token_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    _log(f"readonly Gmail token written to {token_path}")
    return 0


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode_body(payload: dict) -> str:
    """Best-effort plain-text body from a Gmail message payload."""
    def walk(part: dict) -> str:
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if mime == "text/plain" and data:
            return base64.urlsafe_b64decode(data.encode("ascii")).decode("utf-8", "replace")
        for sub in part.get("parts", []) or []:
            text = walk(sub)
            if text:
                return text
        return ""

    return walk(payload or {})


def _parse_message(service, msg_id: str) -> tuple[ParsedReply, list[str]]:
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = msg.get("payload", {}).get("headers", [])
    from_raw = _header(headers, "From")
    # "Name <addr@x>" → addr; bare "addr@x" → addr.
    email = from_raw.split("<")[-1].rstrip(">").strip() if "<" in from_raw else from_raw.strip()
    name = from_raw.split("<")[0].strip().strip('"') if "<" in from_raw else ""
    reply = ParsedReply(
        thread_id=msg.get("threadId", msg_id),
        from_email=email,
        from_name=name,
        subject=_header(headers, "Subject"),
        body=_decode_body(msg.get("payload", {})),
        received_at=_header(headers, "Date"),
    )
    return reply, list(msg.get("labelIds", []))


def _new_message_ids(service, state: dict) -> tuple[list[str], str | None]:
    """New inbound message ids since the cursor, and the latest historyId.

    First run (no cursor): backfill recent inbox via messages.list. Subsequent
    runs: incremental via history.list(messageAdded).
    """
    history_id = state.get("history_id")
    if not history_id:
        resp = (
            service.users()
            .messages()
            .list(userId="me", q=INITIAL_QUERY, maxResults=100)
            .execute()
        )
        ids = [m["id"] for m in resp.get("messages", [])]
        profile = service.users().getProfile(userId="me").execute()
        return ids, str(profile.get("historyId") or "")
    ids: list[str] = []
    latest = str(history_id)
    page_token = None
    while True:
        resp = (
            service.users()
            .history()
            .list(
                userId="me",
                startHistoryId=str(history_id),
                historyTypes=["messageAdded"],
                pageToken=page_token,
            )
            .execute()
        )
        for record in resp.get("history", []):
            latest = str(record.get("id", latest))
            for added in record.get("messagesAdded", []):
                mid = added.get("message", {}).get("id")
                if mid:
                    ids.append(mid)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    # Dedup preserving order.
    seen: set[str] = set()
    deduped = [i for i in ids if not (i in seen or seen.add(i))]
    return deduped, latest


def poll_once() -> None:
    state = _load_state()
    try:
        service = _build_service()
    except RuntimeError as exc:
        _log(str(exc))
        return
    try:
        msg_ids, new_history_id = _new_message_ids(service, state)
    except Exception as exc:  # network/API hiccup — try again next cycle
        _log(f"history fetch failed (continuing): {exc!r}")
        return

    self_addr = (os.environ.get("BBW_GMAIL_ADDRESS", "") or "").strip().lower()
    processed = set(state.get("processed_thread_ids", []))
    matched = unmatched = 0
    for msg_id in msg_ids:
        try:
            reply, labels = _parse_message(service, msg_id)
        except Exception as exc:
            _log(f"parse failed for {msg_id} (skipping): {exc!r}")
            continue
        # Only inbound inbox mail; never our own sent copies.
        if "SENT" in labels or "INBOX" not in labels:
            continue
        if self_addr and reply.from_email.strip().lower() == self_addr:
            continue
        if reply.thread_id in processed:
            continue
        outcome = process_reply(reply)
        processed.add(reply.thread_id)
        if outcome.matched:
            matched += 1
            flag = " STOP" if outcome.suppressed else ""
            _log(f"matched {outcome.place_id} via {outcome.matched_by} -> {outcome.status}{flag}")
        else:
            unmatched += 1
            _log(f"unmatched thread {reply.thread_id} from {reply.from_email}: {outcome.reason}")

    state["history_id"] = new_history_id or state.get("history_id")
    state["processed_thread_ids"] = list(processed)
    _save_state(state)
    if matched or unmatched:
        _log(f"cycle done: {matched} matched, {unmatched} unmatched")


def main() -> int:
    if "--auth" in sys.argv:
        return authorize()
    once = "--once" in sys.argv
    interval = int(os.environ.get("AGENCY_REPLY_SYNC_POLL_INTERVAL_SECS", DEFAULT_INTERVAL))
    if once:
        poll_once()
        return 0
    _log(f"starting; interval={interval}s")
    while True:
        try:
            poll_once()
        except Exception as exc:  # never let one bad cycle kill the loop
            _log(f"cycle error (continuing): {exc!r}")
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
