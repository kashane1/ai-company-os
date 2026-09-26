from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

import pytest

from radar import db, sources

FIXTURES = Path(__file__).parent / "fixtures"
NOW = dt.datetime(2026, 9, 25, 20, 30, tzinfo=dt.timezone.utc)


def load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def load_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture()
def connection() -> sqlite3.Connection:
    connection = db.connect(":memory:")
    db.init(connection)
    sources.ensure_registered(connection)
    return connection
