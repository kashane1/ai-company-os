import plistlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / 'infra/launchd/com.ai-company-os.runtime-supervisor.plist'


def test_launchd_owns_the_foreground_supervisor():
    payload = plistlib.loads(TEMPLATE.read_bytes())
    assert payload['ProgramArguments'] == [
        '__REPO_ROOT__/.venv/bin/python',
        '__REPO_ROOT__/apps/runtime-supervisor/main.py',
    ]
    assert payload['WorkingDirectory'] == '__REPO_ROOT__'


def test_render_handles_spaces_and_xml_characters(tmp_path):
    from scripts.render_launch_agent import render
    root = tmp_path / 'My repo & tools'
    output = tmp_path / 'agent.plist'
    render(root, output)
    payload = plistlib.loads(output.read_bytes())
    assert payload['WorkingDirectory'] == str(root.resolve())
    assert payload['ProgramArguments'][0] == str(root.resolve() / '.venv/bin/python')
    assert '__REPO_ROOT__' not in output.read_text()
    assert Path(payload['StandardOutPath']).parent.is_dir()


def test_supervisor_handles_sigterm_and_reports_failure(monkeypatch):
    import signal
    from dataclasses import dataclass

    from tests.python.unit.test_runtime_supervisor import load_runtime_supervisor_main
    load_runtime_supervisor_main()
    from supervisor import core
    previous = signal.getsignal(signal.SIGTERM)
    @dataclass
    class Status:
        state: str = 'failed'
    class FakeSupervisor:
        def run(self, *, stop_event):
            signal.raise_signal(signal.SIGTERM)
            assert stop_event.is_set()
            return Status()
    monkeypatch.setattr(core, 'RuntimeSupervisor', FakeSupervisor)
    assert core.run_main() == 1
    assert signal.getsignal(signal.SIGTERM) == previous


def test_sigterm_stops_foreground_supervisor_and_synthetic_child(tmp_path):
    import json
    import os
    import signal
    import subprocess
    import sys
    import time
    code = '''
import sys
sys.path.insert(0, sys.argv[1])
from supervisor import core
from supervisor.specs import WorkerProcessSpec
original = core.RuntimeSupervisor
core.RuntimeSupervisor = lambda: original(worker_specs=[WorkerProcessSpec(lane="synthetic", worker_id="test-child", script_path=sys.argv[2], log_path=sys.argv[2] + ".log")])
raise SystemExit(core.run_main())
'''
    child = tmp_path / 'child.py'
    child.write_text('import time\nwhile True: time.sleep(0.1)\n')
    env = dict(os.environ, AI_COMPANY_OS_REPO_ROOT=str(tmp_path))
    process = subprocess.Popen([sys.executable, '-c', code, str(ROOT / 'apps/runtime-supervisor'), str(child)], env=env, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    status_path = tmp_path / 'state/checkpoints/platform/runtime-supervisor-status.json'
    child_pid = None
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError(process.communicate())
            if status_path.exists():
                try:
                    status = json.loads(status_path.read_text())
                    if status['state'] == 'running':
                        child_pid = status['workers'][0]['pid']
                        break
                except json.JSONDecodeError:
                    pass
            time.sleep(0.05)
        assert child_pid is not None
        process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, (stdout, stderr)
        assert json.loads(status_path.read_text())['state'] == 'stopped'
        import pytest
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if child_pid:
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
