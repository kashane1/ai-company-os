import json
import os
import tempfile
from pathlib import Path


class JsonStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, record_id: str) -> Path:
        return self.root / f"{record_id}.json"

    def save(self, record_id: str, payload: dict[str, object]) -> Path:
        path = self.path_for(record_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: a crash mid-write must never truncate the existing record
        # to empty/partial JSON (it holds lead/billing/entitlement state). Write a
        # temp file in the same dir, then os.replace (atomic on the same volume).
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{record_id}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return path

    def load(self, record_id: str) -> dict[str, object]:
        with self.path_for(record_id).open() as handle:
            return json.load(handle)
