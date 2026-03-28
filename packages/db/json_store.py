import json
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
        with path.open("w") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        return path

    def load(self, record_id: str) -> dict[str, object]:
        with self.path_for(record_id).open() as handle:
            return json.load(handle)
