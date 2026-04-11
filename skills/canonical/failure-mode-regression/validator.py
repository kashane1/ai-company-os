"""failure-mode-regression — pure-Python capture pipeline.

Deduped, redaction-aware fixture writer. Called from the observability
rollup and from the control plane's ``task_result_rejected`` path.

The skill is kind=validator because it returns a structured verdict
dict; the 'work' it does (writing a fixture) is a deterministic side
effect, not an agentic step.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEDUPE_WINDOW = timedelta(hours=24)
SELF_FAILURE_CODE = "capture_pipeline_self_failure"


def _parse(ts: str) -> datetime:
    # Tolerate trailing Z.
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _redact_text(text: str) -> tuple[str, int]:
    try:
        from packages.tools.observability.redaction import redact

        result = redact(text)
        return result.text, len(result.hits)
    except Exception:
        return text, 0


def _redact_payload(payload: dict) -> tuple[dict, int]:
    try:
        from packages.tools.observability.redaction import redact
    except Exception:
        return payload, 0

    hits = 0
    out: dict = {}
    for k, v in payload.items():
        if isinstance(v, str):
            r = redact(v)
            out[k] = r.text
            hits += len(r.hits)
        else:
            out[k] = v
    return out, hits


def _load_index(root: Path) -> dict:
    idx = root / "index.json"
    if not idx.exists():
        return {}
    try:
        return json.loads(idx.read_text())
    except Exception:
        return {}


def _save_index(root: Path, data: dict) -> None:
    idx = root / "index.json"
    tmp = idx.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(idx)


def run(payload: dict) -> dict:
    try:
        code = payload["failure_code"]
        lane = payload.get("lane", "unknown")
        excerpt = payload.get("excerpt", "") or ""
        inner_payload = payload.get("payload") or {}
        fixtures_root = Path(payload.get("fixtures_root") or "state/artifacts/failure-fixtures")
        now = _parse(payload.get("now") or datetime.now(timezone.utc).isoformat())

        fixtures_root.mkdir(parents=True, exist_ok=True)
        index = _load_index(fixtures_root)

        last = index.get(code, {}).get("last_captured_at")
        if last:
            try:
                if now - _parse(last) < DEDUPE_WINDOW:
                    return {
                        "verdict": "skipped",
                        "failure_code": code,
                        "fixture_path": "",
                        "reason": f"within {DEDUPE_WINDOW} of last capture",
                    }
            except Exception:
                pass  # bad index entry → overwrite below

        redacted_excerpt, excerpt_hits = _redact_text(excerpt)
        redacted_payload, payload_hits = _redact_payload(inner_payload)

        stem = hashlib.sha1(f"{code}:{now.isoformat()}".encode()).hexdigest()[:10]
        fixture_path = fixtures_root / f"{code}__{now.strftime('%Y%m%dT%H%M%S')}__{stem}.json"
        fixture_body = {
            "failure_code": code,
            "lane": lane,
            "captured_at": now.isoformat(),
            "excerpt": redacted_excerpt,
            "payload": redacted_payload,
            "redaction_hits": excerpt_hits + payload_hits,
        }
        tmp = fixture_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(fixture_body, indent=2, sort_keys=True))
        tmp.replace(fixture_path)

        index[code] = {
            "last_captured_at": now.isoformat(),
            "last_fixture_path": str(fixture_path),
            "count": int(index.get(code, {}).get("count", 0)) + 1,
        }
        _save_index(fixtures_root, index)

        return {
            "verdict": "ok",
            "failure_code": code,
            "fixture_path": str(fixture_path),
            "reason": "",
        }
    except Exception as exc:
        # Do NOT recursively self-capture.
        return {
            "verdict": "fail",
            "failure_code": SELF_FAILURE_CODE,
            "fixture_path": "",
            "reason": f"{type(exc).__name__}: {exc}",
        }
