"""A transient failure mid-write must not corrupt a prior audit artifact.

`PostMortemStore.save` writes to a temp file and atomically `os.replace`s
it into place, cleaning the temp file on error. This test proves the
guarantee the application answer relies on: an error part-way through a
run does not leave a half-written or destroyed audit record behind.
"""

from __future__ import annotations

import json

import pytest

from packages.db.postmortem_store import PostMortemStore
from packages.schemas.postmortem import PostMortem


def _pm(pm_id: str, note: str) -> PostMortem:
    return PostMortem(
        id=pm_id,
        created_at="2026-05-17T00:00:00+00:00",
        updated_at="2026-05-17T00:00:00+00:00",
        failure_code="execution_failed",
        lane="engineering",
        notes=note,
    )


def test_failed_write_preserves_previous_artifact_and_leaves_no_temp(tmp_path, monkeypatch):
    store = PostMortemStore(
        root=tmp_path / "postmortems",
        audit_log_path=tmp_path / "logs" / "audit.jsonl",
    )

    # First write succeeds and is the known-good state.
    good_path = store.save(_pm("pm_0001", "original good record"))
    assert store.load("pm_0001").notes == "original good record"

    # Simulate a transient failure part-way through the next write.
    real_dump = json.dump

    def exploding_dump(*args, **kwargs):
        raise OSError("simulated transient disk error mid-write")

    monkeypatch.setattr(json, "dump", exploding_dump)
    with pytest.raises(OSError):
        store.save(_pm("pm_0001", "corrupting half-written record"))
    monkeypatch.setattr(json, "dump", real_dump)

    # The prior artifact is intact, not half-written or destroyed.
    reloaded = store.load("pm_0001")
    assert reloaded is not None
    assert reloaded.notes == "original good record"

    # No leftover temp files next to the artifact.
    leftovers = [p.name for p in good_path.parent.iterdir() if ".tmp-" in p.name]
    assert leftovers == []
