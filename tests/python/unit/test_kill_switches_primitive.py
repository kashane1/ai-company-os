"""Phase 3 — unit tests for packages/tools/primitives/kill_switches.py."""
from __future__ import annotations

import pytest

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.tools.primitives.kill_switches import (
    KNOWN_SWITCHES,
    KillSwitch,
    UnknownKillSwitchError,
    get_switch,
    list_switches,
)


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    flags_dir = tmp_path / "state" / "flags"
    flags_dir.mkdir(parents=True, exist_ok=True)
    return flags_dir


def test_get_switch_reports_disengaged_when_file_absent(isolated_state) -> None:
    switch = get_switch("skill_evolution_frozen")
    assert isinstance(switch, KillSwitch)
    assert switch.name == "skill_evolution_frozen"
    assert switch.engaged is False
    assert switch.path.endswith("state/flags/skill_evolution_frozen")


def test_get_switch_reports_engaged_when_file_present(isolated_state) -> None:
    (isolated_state / "skill_evolution_frozen").write_text("x")
    switch = get_switch("skill_evolution_frozen")
    assert switch.engaged is True


def test_unknown_switch_raises(isolated_state) -> None:
    with pytest.raises(UnknownKillSwitchError) as exc:
        get_switch("nonexistent_switch")
    # Error message must list the known switches so a typo gets a
    # fixable hint immediately.
    assert "skill_evolution_frozen" in str(exc.value)


def test_list_switches_returns_sorted_tuple(isolated_state) -> None:
    snapshot = list_switches()
    assert isinstance(snapshot, tuple)
    names = [s.name for s in snapshot]
    assert names == sorted(KNOWN_SWITCHES)
    assert all(isinstance(s, KillSwitch) for s in snapshot)


def test_gtm_frozen_is_a_known_switch(isolated_state) -> None:
    # The GTM worker predates this primitive and uses its own file
    # reader; registering the name here makes the switch discoverable
    # from the primitive layer too, so future refactors have a
    # single source of truth to grep.
    switch = get_switch("gtm_frozen")
    assert switch.engaged is False
