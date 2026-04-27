"""PostMortemStore — durable evidence layer for the harness learning loop.

Per-record JSON files under ``state/postmortems/`` (one file per id). The
on-disk ``index.json``, if present, is a *derived* read-time cache only —
deleting it does not affect correctness (M3 fix from review).

``update_status`` is the only mutator and writes an append-only audit log
to ``state/logs/postmortems/audit.jsonl`` (H1 fix). All non-resolved
status changes that lack a matching audit record are surfaced as ``warn``
by the runtime sub-check.
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

from packages.schemas.postmortem import PostMortem, PostMortemStatus


def _resolve_default_root() -> Path:
    """Resolve the postmortems root inside __init__, never at module load."""
    from packages.config.settings import ensure_runtime_directories

    paths = ensure_runtime_directories()
    return paths.postmortems_root


def _resolve_default_audit_log() -> Path:
    from packages.config.settings import ensure_runtime_directories

    paths = ensure_runtime_directories()
    return paths.postmortem_audit_log_path


class PostMortemStore:
    def __init__(
        self,
        root: Path | None = None,
        *,
        audit_log_path: Path | None = None,
    ) -> None:
        self._root = root or _resolve_default_root()
        self._root.mkdir(parents=True, exist_ok=True)
        self._audit_log_path = audit_log_path or _resolve_default_audit_log()
        self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    @property
    def audit_log_path(self) -> Path:
        return self._audit_log_path

    def path_for(self, postmortem_id: str) -> Path:
        return self._root / f"{postmortem_id}.json"

    def save(self, record: PostMortem) -> Path:
        path = self.path_for(record.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
        try:
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(record.to_dict(), handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(tmp, path)
        except Exception:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise
        return path

    def load(self, postmortem_id: str) -> PostMortem | None:
        path = self.path_for(postmortem_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
        except Exception:
            return None
        try:
            return PostMortem.from_dict(payload)
        except Exception:
            return None

    def _iter_records(self) -> list[PostMortem]:
        records: list[PostMortem] = []
        for child in self._root.glob("*.json"):
            if child.name == "index.json":
                continue
            try:
                payload = json.loads(child.read_text())
                records.append(PostMortem.from_dict(payload))
            except Exception:
                # Corrupt files are skipped, never poison the loader.
                continue
        return records

    def list_recent(self, *, now_iso: str, max_age_days: int = 90) -> list[PostMortem]:
        from packages.policies.postmortem_retention import is_visible

        return [r for r in self._iter_records() if is_visible(r, now_iso=now_iso, window_days=max_age_days)]

    def list_open_stale(
        self,
        *,
        now_iso: str,
        threshold_days: int = 14,
    ) -> list[PostMortem]:
        from packages.policies.postmortem_retention import is_stale

        return [r for r in self._iter_records() if is_stale(r, now_iso=now_iso, threshold_days=threshold_days)]

    def list_open(self) -> list[PostMortem]:
        return [r for r in self._iter_records() if r.status is PostMortemStatus.OPEN]

    def update_status(
        self,
        postmortem_id: str,
        *,
        status: PostMortemStatus,
        now_iso: str,
        caller_identity: str,
        notes: str | None = None,
    ) -> PostMortem:
        current = self.load(postmortem_id)
        if current is None:
            raise KeyError(postmortem_id)
        prev_status = current.status
        updated = replace(
            current,
            status=status,
            notes=notes if notes is not None else current.notes,
            updated_at=now_iso,
        )
        self.save(updated)
        self._append_audit_record(
            postmortem_id=postmortem_id,
            prev_status=prev_status,
            new_status=status,
            caller_identity=caller_identity,
            now_iso=now_iso,
        )
        return updated

    def _append_audit_record(
        self,
        *,
        postmortem_id: str,
        prev_status: PostMortemStatus,
        new_status: PostMortemStatus,
        caller_identity: str,
        now_iso: str,
    ) -> None:
        record = {
            "postmortem_id": postmortem_id,
            "prev_status": prev_status.value,
            "new_status": new_status.value,
            "caller_identity": caller_identity,
            "timestamp_iso": now_iso,
            "schema_version": "1",
        }
        line = json.dumps(record, sort_keys=True) + "\n"
        # O_APPEND + fsync: append-only, atomic per-record on POSIX.
        fd = os.open(
            str(self._audit_log_path),
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    def read_audit_log(self) -> list[dict]:
        """Read the append-only audit log. Returns [] if absent."""
        if not self._audit_log_path.exists():
            return []
        records: list[dict] = []
        for line in self._audit_log_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
        return records
