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
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEDUPE_WINDOW = timedelta(hours=24)
SELF_FAILURE_CODE = "capture_pipeline_self_failure"
POSTMORTEM_EMIT_DISABLED_ENV_VAR = "AI_COMPANY_OS_DISABLE_POSTMORTEM_EMIT"


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


def _postmortem_id(failure_code: str, fixture_path: str, created_at: str) -> str:
    """Stable ID = sha10 of (failure_code, fixture_path, created_at).

    Filesystem-safe; no embedded ISO timestamps; no `__` delimiters.
    """
    digest = hashlib.sha1(f"{failure_code}|{fixture_path}|{created_at}".encode()).hexdigest()
    return digest[:10]


def _emit_postmortem_stub(
    *,
    failure_code: str,
    lane: str,
    redacted_excerpt: str,
    redaction_hits: int,
    fixture_path: Path,
    now_iso: str,
    postmortems_root: Path | None = None,
) -> tuple[bool, str | None]:
    """Best-effort PostMortem stub emission. Returns (success, warning_or_none).

    Failure here MUST NOT change the parent fixture-capture verdict.
    Idempotent within 24h via O_EXCL lockfile under
    ``state/postmortems/.dedup/<failure_code>.lock`` (M2 fix).
    """
    if os.environ.get(POSTMORTEM_EMIT_DISABLED_ENV_VAR) == "1":
        return False, "postmortem_emit_disabled"

    try:
        from packages.config.settings import ensure_runtime_directories
        from packages.db.postmortem_store import PostMortemStore
        from packages.schemas.postmortem import PostMortem

        if postmortems_root is None:
            paths = ensure_runtime_directories()
            postmortems_root = paths.postmortems_root
        else:
            postmortems_root.mkdir(parents=True, exist_ok=True)

        # M2 fix: O_EXCL lockfile dedup, not read-modify-write on index.json.
        dedup_dir = postmortems_root / ".dedup"
        dedup_dir.mkdir(parents=True, exist_ok=True)
        lock_path = dedup_dir / f"{failure_code}.lock"
        try:
            fd = os.open(
                str(lock_path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            try:
                age = (datetime.now(timezone.utc).timestamp() - lock_path.stat().st_mtime)
            except OSError:
                age = 0
            if age < 86400:
                return False, "postmortem_dedup_skip"
            lock_path.unlink(missing_ok=True)
            fd = os.open(
                str(lock_path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        try:
            os.write(fd, now_iso.encode("utf-8"))
        finally:
            os.close(fd)

        pm_id = _postmortem_id(failure_code, str(fixture_path), now_iso)
        record = PostMortem(
            id=pm_id,
            created_at=now_iso,
            updated_at=now_iso,
            failure_code=failure_code,
            lane=lane,
            fixture_path=str(fixture_path),
            excerpt_redacted=redacted_excerpt,
            redaction_hits=redaction_hits,
        )
        store = PostMortemStore(root=postmortems_root)
        store.save(record)
        return True, None
    except Exception as exc:
        return False, f"postmortem_emit_failed:{type(exc).__name__}"


def run(payload: dict) -> dict:
    try:
        code = payload["failure_code"]
        # Path-traversal gate: failure_code is interpolated into the
        # fixture filename, the dedup lockfile, and the PostMortem id.
        # Reject anything outside the safe character class at the entry.
        from packages.schemas.postmortem import is_safe_failure_code

        if not isinstance(code, str) or not is_safe_failure_code(code):
            return {
                "verdict": "fail",
                "failure_code": SELF_FAILURE_CODE,
                "fixture_path": "",
                "reason": f"unsafe_failure_code:{code!r}",
            }
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

        # PostMortem stub emission (Phase 2 of harness learning loop).
        # Best-effort; failures here must NOT change the parent verdict.
        warnings: list[str] = []
        postmortems_root_override = payload.get("postmortems_root")
        emit_root = (
            Path(postmortems_root_override) if postmortems_root_override else None
        )
        ok, warning = _emit_postmortem_stub(
            failure_code=code,
            lane=lane,
            redacted_excerpt=redacted_excerpt,
            redaction_hits=excerpt_hits + payload_hits,
            fixture_path=fixture_path,
            now_iso=now.isoformat(),
            postmortems_root=emit_root,
        )
        if warning:
            warnings.append(warning)

        result: dict[str, Any] = {
            "verdict": "ok",
            "failure_code": code,
            "fixture_path": str(fixture_path),
            "reason": "",
        }
        if warnings:
            result["warnings"] = warnings
        return result
    except Exception as exc:
        # Do NOT recursively self-capture.
        return {
            "verdict": "fail",
            "failure_code": SELF_FAILURE_CODE,
            "fixture_path": "",
            "reason": f"{type(exc).__name__}: {exc}",
        }
