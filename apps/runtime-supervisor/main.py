from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
from threading import Event
from typing import Protocol

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.config.settings import ensure_runtime_directories


class ManagedProcess(Protocol):
    pid: int

    def poll(self) -> int | None:
        ...

    def send_signal(self, sig: signal.Signals) -> None:
        ...

    def wait(self, timeout: float | None = None) -> int:
        ...

    def terminate(self) -> None:
        ...

    def kill(self) -> None:
        ...


@dataclass(frozen=True)
class WorkerProcessSpec:
    lane: str
    worker_id: str
    script_path: Path
    log_path: Path


@dataclass(frozen=True)
class WorkerProcessStatus:
    lane: str
    worker_id: str
    pid: int | None
    state: str
    last_known_status: str
    started_at: str | None = None
    exited_at: str | None = None
    exit_code: int | None = None


@dataclass(frozen=True)
class SupervisorStatus:
    state: str
    started_at: str
    updated_at: str
    workers: list[WorkerProcessStatus]


@dataclass
class ManagedWorker:
    spec: WorkerProcessSpec
    process: ManagedProcess
    log_handle: object | None


def default_worker_specs() -> list[WorkerProcessSpec]:
    paths = ensure_runtime_directories()
    runtime_logs_root = paths.logs_root / "runtime-supervisor"
    runtime_logs_root.mkdir(parents=True, exist_ok=True)
    return [
        WorkerProcessSpec(
            lane="engineering",
            worker_id="worker-engineering",
            script_path=paths.repo_root / "apps" / "worker-engineering" / "main.py",
            log_path=runtime_logs_root / "worker-engineering.log",
        ),
        WorkerProcessSpec(
            lane="ios",
            worker_id="worker-ios",
            script_path=paths.repo_root / "apps" / "worker-ios" / "main.py",
            log_path=runtime_logs_root / "worker-ios.log",
        ),
        WorkerProcessSpec(
            lane="appstore",
            worker_id="worker-appstore",
            script_path=paths.repo_root / "apps" / "worker-appstore" / "main.py",
            log_path=runtime_logs_root / "worker-appstore.log",
        ),
        WorkerProcessSpec(
            lane="api",
            worker_id="worker-api",
            script_path=paths.repo_root / "apps" / "api" / "server.py",
            log_path=runtime_logs_root / "worker-api.log",
        ),
    ]


class RuntimeSupervisor:
    def __init__(
        self,
        *,
        worker_specs: list[WorkerProcessSpec] | None = None,
        process_factory=subprocess.Popen,
    ) -> None:
        self.paths = ensure_runtime_directories()
        self.status_path = self.paths.platform_state_root / "runtime-supervisor-status.json"
        self.stop_request_path = self.paths.platform_state_root / "runtime-supervisor-stop.json"
        self.worker_specs = worker_specs or default_worker_specs()
        self.process_factory = process_factory
        self.started_at = self._now()
        self._workers: dict[str, ManagedWorker] = {}
        self._worker_statuses = {
            spec.lane: WorkerProcessStatus(
                lane=spec.lane,
                worker_id=spec.worker_id,
                pid=None,
                state="not_started",
                last_known_status="not_started",
            )
            for spec in self.worker_specs
        }

    def start_all(self) -> None:
        if self.stop_request_path.exists():
            self.stop_request_path.unlink()
        for spec in self.worker_specs:
            if spec.lane in self._workers:
                continue
            log_handle = open(spec.log_path, "a", encoding="utf-8")
            process = self.process_factory(
                [sys.executable, str(spec.script_path)],
                cwd=str(self.paths.repo_root),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self._workers[spec.lane] = ManagedWorker(spec=spec, process=process, log_handle=log_handle)
            self._worker_statuses[spec.lane] = WorkerProcessStatus(
                lane=spec.lane,
                worker_id=spec.worker_id,
                pid=process.pid,
                state="running",
                last_known_status="started",
                started_at=self._now(),
            )
        self._persist_status(state="running")

    def monitor_once(self) -> list[WorkerProcessStatus]:
        for lane, managed in self._workers.items():
            if self._worker_statuses[lane].state == "exited":
                continue
            exit_code = managed.process.poll()
            if exit_code is None:
                current = self._worker_statuses[lane]
                self._worker_statuses[lane] = WorkerProcessStatus(
                    lane=current.lane,
                    worker_id=current.worker_id,
                    pid=current.pid,
                    state="running",
                    last_known_status="running",
                    started_at=current.started_at,
                    exited_at=None,
                    exit_code=None,
                )
                continue
            current = self._worker_statuses[lane]
            self._worker_statuses[lane] = WorkerProcessStatus(
                lane=current.lane,
                worker_id=current.worker_id,
                pid=current.pid,
                state="exited",
                last_known_status="exited",
                started_at=current.started_at,
                exited_at=self._now(),
                exit_code=exit_code,
            )
            self._close_log_handle(lane)
        self._persist_status(state="running")
        return self.status().workers

    def stop_all(self, *, timeout_seconds: float = 2.0) -> None:
        for lane, managed in self._workers.items():
            if self._worker_statuses[lane].state == "exited":
                continue
            try:
                managed.process.send_signal(signal.SIGINT)
            except ProcessLookupError:
                continue

        for lane, managed in self._workers.items():
            if self._worker_statuses[lane].state == "exited":
                continue
            try:
                exit_code = managed.process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                managed.process.terminate()
                try:
                    exit_code = managed.process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    managed.process.kill()
                    exit_code = managed.process.wait(timeout=timeout_seconds)
            current = self._worker_statuses[lane]
            self._worker_statuses[lane] = WorkerProcessStatus(
                lane=current.lane,
                worker_id=current.worker_id,
                pid=current.pid,
                state="exited",
                last_known_status="stopped",
                started_at=current.started_at,
                exited_at=self._now(),
                exit_code=exit_code,
            )
            self._close_log_handle(lane)
        self._persist_status(state="stopped")

    def status(self) -> SupervisorStatus:
        return SupervisorStatus(
            state=self._overall_state(),
            started_at=self.started_at,
            updated_at=self._now(),
            workers=list(self._worker_statuses.values()),
        )

    def run(
        self,
        *,
        stop_event: Event | None = None,
        poll_interval_seconds: float = 2.0,
        sleep_fn=time.sleep,
        max_iterations: int | None = None,
    ) -> SupervisorStatus:
        stop_signal = stop_event or Event()
        if not self._workers:
            self.start_all()
        iterations = 0
        try:
            while not stop_signal.is_set():
                if self.stop_request_path.exists():
                    stop_signal.set()
                    break
                self.monitor_once()
                iterations += 1
                if all(status.state == "exited" for status in self._worker_statuses.values()):
                    break
                if max_iterations is not None and iterations >= max_iterations:
                    break
                sleep_fn(poll_interval_seconds)
        except KeyboardInterrupt:
            stop_signal.set()
        finally:
            self.stop_all()
        return self.status()

    def _persist_status(self, *, state: str) -> None:
        payload = {
            "state": state,
            "started_at": self.started_at,
            "updated_at": self._now(),
            "workers": [asdict(status) for status in self._worker_statuses.values()],
        }
        self.status_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _overall_state(self) -> str:
        states = {status.state for status in self._worker_statuses.values()}
        if states == {"exited"}:
            return "stopped"
        if "running" in states:
            return "running"
        return "not_started"

    def _close_log_handle(self, lane: str) -> None:
        managed = self._workers.get(lane)
        if managed is None or managed.log_handle is None:
            return
        handle = managed.log_handle
        managed.log_handle = None
        handle.close()

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()


def load_supervisor_status() -> dict[str, object]:
    paths = ensure_runtime_directories()
    status_path = paths.platform_state_root / "runtime-supervisor-status.json"
    if not status_path.exists():
        return {"state": "not_started", "workers": []}
    return json.loads(status_path.read_text(encoding="utf-8"))


def request_supervisor_shutdown() -> dict[str, object]:
    paths = ensure_runtime_directories()
    stop_request_path = paths.platform_state_root / "runtime-supervisor-stop.json"
    payload = {
        "requested_at": datetime.now(UTC).isoformat(),
        "reason": "operator_requested_shutdown",
    }
    stop_request_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


if __name__ == "__main__":
    supervisor = RuntimeSupervisor()
    status = supervisor.run()
    print(json.dumps(asdict(status), default=str))
