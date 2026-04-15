from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import signal
import sys
from threading import Event


def load_runtime_supervisor_main():
    module_path = Path(__file__).resolve().parents[3] / "apps" / "runtime-supervisor" / "main.py"
    spec = importlib.util.spec_from_file_location("runtime_supervisor_main", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeProcess:
    def __init__(self, pid: int, poll_results: list[int | None], wait_result: int = 0) -> None:
        self.pid = pid
        self._poll_results = list(poll_results)
        self._last_poll: int | None = None
        self.wait_result = wait_result
        self.sent_signals: list[signal.Signals] = []
        self.wait_calls: list[float | None] = []
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        if self._poll_results:
            self._last_poll = self._poll_results.pop(0)
        return self._last_poll

    def send_signal(self, sig: signal.Signals) -> None:
        self.sent_signals.append(sig)

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls.append(timeout)
        return self.wait_result

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


def test_runtime_supervisor_starts_three_bounded_worker_processes(
    isolated_repo_root: Path,
) -> None:
    runtime_supervisor_main = load_runtime_supervisor_main()
    created_commands: list[list[str]] = []
    # Phase 3 — supervisor now starts five workers. Keep the same
    # pattern but extend the pid counter and the expected lane list.
    pid_counter = iter([101, 102, 103, 104, 105])

    def fake_process_factory(command, **kwargs):
        created_commands.append(command)
        return FakeProcess(pid=next(pid_counter), poll_results=[None])

    supervisor = runtime_supervisor_main.RuntimeSupervisor(process_factory=fake_process_factory)
    supervisor.start_all()
    status = supervisor.status()

    expected_lanes = ["engineering", "ios", "appstore", "api", "skill_evolution"]
    assert [worker.lane for worker in status.workers] == expected_lanes
    assert all(worker.state == "running" for worker in status.workers)
    assert all(worker.pid is not None for worker in status.workers)
    assert len(created_commands) == 5
    assert created_commands[0][1].endswith("apps/worker-engineering/main.py")
    assert created_commands[1][1].endswith("apps/worker-ios/main.py")
    assert created_commands[2][1].endswith("apps/worker-appstore/main.py")
    assert created_commands[3][1].endswith("apps/api/server.py")
    assert created_commands[4][1].endswith("apps/worker-skill-evolution/main.py")

    payload = json.loads(supervisor.status_path.read_text())
    assert payload["state"] == "running"
    assert [worker["lane"] for worker in payload["workers"]] == expected_lanes


def test_runtime_supervisor_records_worker_exit_without_restart(
    isolated_repo_root: Path,
) -> None:
    runtime_supervisor_main = load_runtime_supervisor_main()
    processes = {
        "worker-engineering": FakeProcess(pid=201, poll_results=[7], wait_result=7),
        "worker-ios": FakeProcess(pid=202, poll_results=[None], wait_result=0),
        "worker-appstore": FakeProcess(pid=203, poll_results=[None], wait_result=0),
        "api": FakeProcess(pid=204, poll_results=[None], wait_result=0),
        "worker-skill-evolution": FakeProcess(
            pid=205, poll_results=[None], wait_result=0
        ),
    }
    created_workers: list[str] = []

    def fake_process_factory(command, **kwargs):
        worker_name = Path(command[1]).parent.name
        created_workers.append(worker_name)
        # Names map: the api worker's script lives under apps/api/, so
        # worker_name == "api" (not "worker-api"); every other entry
        # uses the worker-* dir name directly.
        return processes.get(worker_name, processes["api"])

    supervisor = runtime_supervisor_main.RuntimeSupervisor(process_factory=fake_process_factory)
    supervisor.start_all()
    statuses = supervisor.monitor_once()

    engineering = next(status for status in statuses if status.lane == "engineering")
    ios = next(status for status in statuses if status.lane == "ios")

    assert created_workers == [
        "worker-engineering",
        "worker-ios",
        "worker-appstore",
        "api",
        "worker-skill-evolution",
    ]
    assert engineering.state == "exited"
    assert engineering.exit_code == 7
    assert engineering.last_known_status == "exited"
    assert ios.state == "running"


def test_runtime_supervisor_stops_all_workers_cleanly_on_stop_request(
    isolated_repo_root: Path,
) -> None:
    runtime_supervisor_main = load_runtime_supervisor_main()
    stop_event = Event()
    # Phase 3 — five workers. One FakeProcess per worker spec.
    all_processes = [
        FakeProcess(pid=301, poll_results=[None], wait_result=0),
        FakeProcess(pid=302, poll_results=[None], wait_result=0),
        FakeProcess(pid=303, poll_results=[None], wait_result=0),
        FakeProcess(pid=304, poll_results=[None], wait_result=0),
        FakeProcess(pid=305, poll_results=[None], wait_result=0),
    ]
    processes = list(all_processes)

    def fake_process_factory(command, **kwargs):
        return processes.pop(0)

    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        stop_event.set()

    supervisor = runtime_supervisor_main.RuntimeSupervisor(process_factory=fake_process_factory)
    status = supervisor.run(
        stop_event=stop_event,
        poll_interval_seconds=0.25,
        sleep_fn=fake_sleep,
    )

    assert status.state == "stopped"
    assert sleep_calls == [0.25]
    for worker in status.workers:
        assert worker.state == "exited"
        assert worker.last_known_status == "stopped"
        assert worker.exit_code == 0

    payload = json.loads(supervisor.status_path.read_text())
    assert payload["state"] == "stopped"
    for process in all_processes:
        assert process.sent_signals == [signal.SIGINT]
        assert process.wait_calls == [2.0]


def test_runtime_supervisor_honors_external_stop_request_file(
    isolated_repo_root: Path,
) -> None:
    runtime_supervisor_main = load_runtime_supervisor_main()
    processes = [
        FakeProcess(pid=401, poll_results=[None], wait_result=0),
        FakeProcess(pid=402, poll_results=[None], wait_result=0),
        FakeProcess(pid=403, poll_results=[None], wait_result=0),
        FakeProcess(pid=404, poll_results=[None], wait_result=0),
        FakeProcess(pid=405, poll_results=[None], wait_result=0),
    ]

    def fake_process_factory(command, **kwargs):
        return processes.pop(0)

    supervisor = runtime_supervisor_main.RuntimeSupervisor(process_factory=fake_process_factory)
    supervisor.start_all()
    runtime_supervisor_main.request_supervisor_shutdown()
    status = supervisor.run(max_iterations=1)

    assert status.state == "stopped"
    for worker in status.workers:
        assert worker.state == "exited"
        assert worker.last_known_status == "stopped"
