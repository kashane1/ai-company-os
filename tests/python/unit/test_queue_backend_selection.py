from __future__ import annotations

import pytest

from packages.config.settings import QUEUE_BACKEND_ENV_VAR
from packages.queue import active_queue_backend_name, build_queue_backend
from packages.queue import task_queue as tq
from packages.queue.task_queue import DatabaseQueueBackend, RedisStreamQueueBackend
from packages.schemas.task import Task
from packages.schemas.task_packet import RiskLevel, WorkerLane


def test_queue_backend_defaults_to_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(QUEUE_BACKEND_ENV_VAR, raising=False)

    assert active_queue_backend_name() == "database"
    assert isinstance(build_queue_backend(), DatabaseQueueBackend)


def test_queue_backend_rejects_unknown_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(QUEUE_BACKEND_ENV_VAR, "kafka")

    with pytest.raises(ValueError, match="Unsupported queue backend"):
        build_queue_backend()


def test_redis_stream_backend_enqueues_claims_and_acknowledges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeRedisClient()

    class FakeRedisModule:
        class Redis:
            @staticmethod
            def from_url(url: str, decode_responses: bool = False):
                assert url == "redis://example/0"
                assert decode_responses is True
                return fake_client

    monkeypatch.setattr(tq, "redis", FakeRedisModule)
    backend = RedisStreamQueueBackend(url="redis://example/0")
    task = Task(
        id="task-1",
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Work",
        summary="Do work.",
        task_type="engineering_change",
        risk_level=RiskLevel.LOW,
        created_at="2026-06-01T00:00:00+00:00",
        updated_at="2026-06-01T00:00:00+00:00",
    )

    backend.enqueue(task)
    claimed = backend.claim_next(lanes=[WorkerLane.ENGINEERING], worker_id="worker-1")
    assert claimed is not None
    assert claimed.task_id == task.id
    assert claimed.lane is WorkerLane.ENGINEERING
    assert backend.counts_by_lane() == {WorkerLane.ENGINEERING.value: 1}

    backend.acknowledge(task.id)

    assert backend.counts_by_lane() == {}


class _FakeRedisClient:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.groups: set[tuple[str, str]] = set()
        self.hashes: dict[str, dict[str, str]] = {}
        self._next_id = 0

    def xgroup_create(self, stream: str, group: str, id: str, mkstream: bool) -> None:
        self.streams.setdefault(stream, [])
        key = (stream, group)
        if key in self.groups:
            raise Exception("BUSYGROUP Consumer Group name already exists")
        self.groups.add(key)

    def xadd(self, stream: str, fields: dict[str, str]) -> str:
        self._next_id += 1
        message_id = f"{self._next_id}-0"
        self.streams.setdefault(stream, []).append((message_id, fields))
        return message_id

    def xreadgroup(
        self,
        group: str,
        consumer: str,
        streams: dict[str, str],
        count: int,
        block: int,
    ):
        for stream in streams:
            messages = self.streams.get(stream, [])
            if messages:
                return [(stream, [messages[0]])]
        return []

    def hset(self, name: str, key: str, value: str) -> None:
        self.hashes.setdefault(name, {})[key] = value

    def hget(self, name: str, key: str) -> str | None:
        return self.hashes.get(name, {}).get(key)

    def hdel(self, name: str, key: str) -> None:
        self.hashes.get(name, {}).pop(key, None)

    def xack(self, stream: str, group: str, message_id: str) -> None:
        return None

    def xdel(self, stream: str, message_id: str) -> None:
        self.streams[stream] = [
            message for message in self.streams.get(stream, []) if message[0] != message_id
        ]

    def xlen(self, stream: str) -> int:
        return len(self.streams.get(stream, []))
