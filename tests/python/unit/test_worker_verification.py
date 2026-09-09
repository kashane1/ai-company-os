from pathlib import Path

import pytest
from engineering import validator as engineering_validator
from ios import validator as ios_validator

from tests.python.factories.task_data import build_task


@pytest.mark.parametrize("validator", [engineering_validator, ios_validator])
def test_prose_and_test_filenames_do_not_prove_verification(tmp_path, validator):
    packet = tmp_path / "packet.md"
    packet.write_text("Task")
    result = tmp_path / "result.md"
    result.write_text("## Testing\nNot run.")
    diff = tmp_path / "worktree.diff"
    diff.write_text("diff --git a/source b/source\n")
    checks, _, _ = validator.validate_run(
        build_task(), str(packet), str(tmp_path), str(result), 0, str(diff),
        [" M apps/api/platform.py", " M tests/python/unit/test_platform.py"],
    )
    assert not all(check.passed for check in checks)
    assert any(check.code == "verification_missing" for check in checks)


def git_repo(tmp_path):
    import subprocess
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    subprocess.run(['git', '-C', str(tmp_path), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'baseline'], check=True)
    return tmp_path


@pytest.mark.parametrize('exit_code', [0, 1])
def test_real_command_outcome_and_redacted_logs(tmp_path, exit_code, monkeypatch):
    from packages.schemas.repo import VerificationCommand
    from packages.schemas.task_run import VerificationResult
    from packages.tools.verification import run_verification, verification_check
    root = git_repo(tmp_path / 'repo')
    monkeypatch.setenv('GITHUB_TOKEN', 'never-forward-this-synthetic-token')
    code = "import os, sys; assert 'GITHUB_TOKEN' not in os.environ; print('sk-' + 'z' * 24); print('diagnostic', file=sys.stderr); sys.exit(%d)" % exit_code
    results = run_verification([VerificationCommand(['{python}', '-c', code])], str(root), tmp_path / 'logs')
    result = results[0]
    assert result.exit_code == exit_code
    assert result.passed is (exit_code == 0)
    assert verification_check(results).passed is (exit_code == 0)
    assert result.cwd == str(root.resolve())
    assert len(result.revision) == 40
    assert result.started_at <= result.finished_at
    assert Path(result.stdout_path).read_text() == '[REDACTED]\n'
    assert Path(result.stderr_path).read_text() == 'diagnostic\n'
    assert VerificationResult.from_dict(result.to_dict()) == result


def test_failed_command_stops_later_commands(tmp_path):
    from packages.schemas.repo import VerificationCommand
    from packages.tools.verification import run_verification
    root = git_repo(tmp_path / 'repo')
    commands = [VerificationCommand(['missing-synthetic-executable']), VerificationCommand(['{python}', '-c', "open('should-not-exist', 'w').write('bad')"])]
    results = run_verification(commands, str(root), tmp_path / 'logs')
    assert len(results) == 1
    assert not results[0].passed
    assert not (root / 'should-not-exist').exists()


def test_timeout_is_failed_evidence(tmp_path):
    from packages.schemas.repo import VerificationCommand
    from packages.tools.verification import run_verification
    root = git_repo(tmp_path / 'repo')
    results = run_verification([VerificationCommand(['{python}', '-c', 'import time; time.sleep(30)'], timeout_seconds=0.1)], str(root), tmp_path / 'logs')
    assert results[0].timed_out
    assert not results[0].passed
    assert 'timed out' in Path(results[0].stderr_path).read_text()


def test_command_cwd_cannot_escape_worktree(tmp_path):
    from packages.schemas.repo import VerificationCommand
    from packages.tools.verification import run_verification
    root = git_repo(tmp_path / 'repo')
    results = run_verification([VerificationCommand(['{python}', '-c', 'raise SystemExit(0)'], cwd='..')], str(root), tmp_path / 'logs')
    assert not results[0].passed
    assert 'inside' in Path(results[0].stderr_path).read_text()


@pytest.mark.parametrize('lane_name', ['engineering', 'ios'])
@pytest.mark.parametrize('test_passes', [True, False])
def test_runner_requires_real_passing_test_command(isolated_repo_root, tmp_path, monkeypatch, lane_name, test_passes):
    import importlib
    from dataclasses import replace

    from apps.api.control_plane import ControlPlaneService
    from packages.db.task_run_store import TaskRunStore
    from packages.schemas.repo import VerificationCommand
    from packages.schemas.task_packet import TaskStatus, WorkerLane
    from tests.python.factories.task_data import (
        build_repo_config,
        build_repo_record,
        build_worktree_metadata,
    )
    from tests.python.unit.test_runner import build_execution_record
    runner = importlib.import_module(lane_name + '.runner')
    root = git_repo(tmp_path / 'repo')
    service = ControlPlaneService()
    goal = service.create_goal(title="Verify a synthetic change", summary="Exercise real completion")
    task = service.create_task_for_goal(
        goal_id=goal.id, repo_id="repo-123", lane=WorkerLane(lane_name),
        title="Synthetic change", summary="Use real verification", task_type="code_change",
    )
    assert service.claim_task(lane=task.lane, worker_id="test-worker").id == task.id
    config = replace(build_repo_config(source_path=str(root)), verification={lane_name: [VerificationCommand(['{python}', '-m', 'pytest', 'tests/python', '-q'])]})
    monkeypatch.setattr(runner, 'load_repo_configs', lambda: {task.repo_id: config})
    monkeypatch.setattr(runner, 'prepare_repo', lambda _: build_repo_record())
    monkeypatch.setattr(runner, 'prepare_worktree', lambda *_: build_worktree_metadata(str(root)))
    # Only the external coding engine is substituted; Git capture, subprocess
    # verification, policy, classification, and persistence remain real.
    def code_change(*_):
        (root / 'apps').mkdir()
        (root / 'apps/module.py').write_text('answer = 42\n')
        tests = root / 'tests/python'
        tests.mkdir(parents=True)
        (tests / 'test_answer.py').write_text('def test_answer():\n    assert %s\n' % test_passes)
        result = root / 'result.md'
        result.write_text('## Testing\nAdded a regression test.')
        stdout = root / "codex.stdout.log"
        stderr = root / "codex.stderr.log"
        stdout.write_text("synthetic coding engine finished")
        stderr.write_text("")
        execution = replace(build_execution_record(), cwd=str(root), stdout_path=str(stdout), stderr_path=str(stderr))
        return str(result), execution, str(result), str(result)
    monkeypatch.setattr(runner, 'execute_codex', code_change)
    result = runner.execute_task(task.id, update_task_status=False)
    completed = service.submit_task_result(
        task_id=task.id, status=result.status, summary=result.summary, worker_id="test-worker",
        artifacts=result.artifacts, events=["task_claimed"],
    )
    assert completed.status is result.status, completed.error_summary
    run = TaskRunStore().load('run-' + task.id)
    assert result.status is (TaskStatus.COMPLETED if test_passes else TaskStatus.FAILED)
    assert result.classification == ('safe_for_review' if test_passes else 'validation_failed')
    assert run.verification_results[0].exit_code == (0 if test_passes else 1)
    assert '1 passed' in Path(run.verification_results[0].stdout_path).read_text() if test_passes else '1 failed' in Path(run.verification_results[0].stdout_path).read_text()
    if not test_passes:
        assert result.approval_id is None
        assert 'verification_failed' in result.failure_codes


def test_verification_cannot_pass_after_modifying_reviewed_code(tmp_path):
    from packages.schemas.repo import VerificationCommand
    from packages.tools.verification import run_verification
    root = git_repo(tmp_path / 'repo')
    (root / 'source.py').write_text('answer = 42\n')
    results = run_verification([VerificationCommand(['{python}', '-c', "open('source.py', 'w').write('answer = 0\\n')"])], str(root), tmp_path / 'logs')
    assert not results[0].passed
    assert 'changed the reviewed worktree' in Path(results[0].stderr_path).read_text()
