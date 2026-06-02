"""Prospecting grid cells and resumable cursor state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.prospecting.config import CityConfig, GenreConfig


@dataclass(frozen=True)
class GridCell:
    city: CityConfig
    genre: GenreConfig

    @property
    def id(self) -> str:
        return f"{self.city.id}:{self.genre.id}"


@dataclass(frozen=True)
class GridCursor:
    completed_cells: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"completed_cells": list(self.completed_cells)}

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "GridCursor":
        return cls(completed_cells=[str(item) for item in list(payload.get("completed_cells", []))])


def build_grid(cities: list[CityConfig], genres: list[GenreConfig]) -> list[GridCell]:
    # Genres flagged `enabled: false` (e.g. lead-gen/service-area spam verticals
    # like garage_door) are kept in the catalog for reference but skipped when
    # generating cells, so the runner never spends API budget on them.
    active_genres = [genre for genre in genres if genre.enabled]
    return [GridCell(city=city, genre=genre) for city in cities for genre in active_genres]


def default_cursor_path(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).state_root / "prospects" / "grid" / "cursors.json"


class GridCursorStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or default_cursor_path()

    def load(self) -> GridCursor:
        if not self._path.exists():
            return GridCursor()
        return GridCursor.from_dict(json.loads(self._path.read_text()))

    def save(self, cursor: GridCursor) -> GridCursor:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(cursor.to_dict(), indent=2, sort_keys=True))
        return cursor

    def mark_completed(self, cell_id: str) -> GridCursor:
        cursor = self.load()
        if cell_id in cursor.completed_cells:
            return cursor
        updated = GridCursor(completed_cells=[*cursor.completed_cells, cell_id])
        return self.save(updated)


def select_cells(
    cells: list[GridCell],
    *,
    cursor: GridCursor | None,
    limit: int,
    selected_cells: list[str] | None = None,
) -> list[GridCell]:
    wanted = set(selected_cells or [])
    completed = set(cursor.completed_cells if cursor else [])
    chosen: list[GridCell] = []
    for cell in cells:
        if wanted and cell.id not in wanted:
            continue
        if not wanted and cell.id in completed:
            continue
        chosen.append(cell)
        if len(chosen) >= limit:
            break
    return chosen

