"""Phase 3 — unit tests for packages/policies/skill_evolution.py.

Covers every branch of ``check_evolution_allowed`` in isolation, plus
the composite entry point. Each test pins ``registry`` and ``lock_store``
explicitly so the suite never touches the real registry on disk or the
real control-plane DB.
"""
from __future__ import annotations

import pytest

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.db.control_plane_db import ControlPlaneDatabase
from packages.db.locks.skill_evolution import SkillEvolutionLockStore
from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.policies.skill_evolution import (
    ProposedDiff,
    check_evolution_allowed,
    check_fixture_skill_atomicity,
)
from packages.tools.skills.loader import SkillSpec


# ---------------------------------------------------------------------- #
# Fixtures                                                                #
# ---------------------------------------------------------------------- #


@pytest.fixture
def empty_db(tmp_path, monkeypatch) -> SkillEvolutionLockStore:
    """Clean per-test lock store on a temp DB."""
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    return SkillEvolutionLockStore(ControlPlaneDatabase())


def _spec(skill_id: str, *, self_evolvable: bool) -> SkillSpec:
    return SkillSpec(
        id=skill_id,
        name=skill_id,
        kind="agentic",
        path=f"canonical/{skill_id}/skill.md",
        owner_agent="test",
        target_runtimes=("claude",),
        stage="active",
        fixture_status="passing",
        source="internal",
        self_evolvable=self_evolvable,
    )


def _ok_diff(skill_id: str = "demo") -> ProposedDiff:
    prefix = f"skills/canonical/{skill_id}/"
    return ProposedDiff(
        target_skill_id=skill_id,
        paths=frozenset(
            {
                prefix + "skill.md",
                prefix + "validator.py",
                prefix + "fixtures/new_case.yaml",
            }
        ),
        target_runtimes=("claude",),
    )


# ---------------------------------------------------------------------- #
# Happy path                                                              #
# ---------------------------------------------------------------------- #


def test_happy_path_patch_existing_passes(empty_db: SkillEvolutionLockStore) -> None:
    check_evolution_allowed(
        _ok_diff(),
        registry=[_spec("demo", self_evolvable=True)],
        lock_store=empty_db,
    )


# ---------------------------------------------------------------------- #
# Allowlist (SKILL_NOT_SELF_EVOLVABLE)                                    #
# ---------------------------------------------------------------------- #


def test_rejects_skill_without_self_evolvable_true(
    empty_db: SkillEvolutionLockStore,
) -> None:
    with pytest.raises(PolicyViolation) as exc:
        check_evolution_allowed(
            _ok_diff("locked-skill"),
            registry=[_spec("locked-skill", self_evolvable=False)],
            lock_store=empty_db,
        )
    assert exc.value.code == PolicyViolationCode.SKILL_NOT_SELF_EVOLVABLE.value


def test_rejects_skill_not_in_registry(empty_db: SkillEvolutionLockStore) -> None:
    """New skill creation via the worker is refused. Registry lives
    on the config denylist, so there's no way to flip
    self_evolvable=true without a human PR."""
    with pytest.raises(PolicyViolation) as exc:
        check_evolution_allowed(
            _ok_diff("brand-new"),
            registry=[],  # empty
            lock_store=empty_db,
        )
    assert exc.value.code == PolicyViolationCode.SKILL_NOT_SELF_EVOLVABLE.value


# ---------------------------------------------------------------------- #
# Config denylist                                                         #
# ---------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "forbidden_path",
    [
        "packages/config/policies.yaml",
        "packages/config/peer_runtimes.yaml",
        "packages/policies/command_scan.py",
        "packages/policies/skill_evolution.py",
        "packages/db/connection.py",
        "packages/schemas/task_packet.py",
        ".github/workflows/ci.yml",
        "infra/launchd/workers.plist",
        "infra/sandbox/hermes.sb",
    ],
)
def test_config_denylist_rejects_forbidden_paths(
    forbidden_path: str, empty_db: SkillEvolutionLockStore
) -> None:
    diff = ProposedDiff(
        target_skill_id="demo",
        paths=frozenset({"skills/canonical/demo/skill.md", forbidden_path}),
        target_runtimes=("claude",),
    )
    with pytest.raises(PolicyViolation) as exc:
        check_evolution_allowed(
            diff,
            registry=[_spec("demo", self_evolvable=True)],
            lock_store=empty_db,
        )
    assert exc.value.code == PolicyViolationCode.CONFIG_MUTATION_REQUIRES_HUMAN.value


# ---------------------------------------------------------------------- #
# Third-file smuggling (H4)                                               #
# ---------------------------------------------------------------------- #


def test_third_file_smuggling_rejects_helper_module(
    empty_db: SkillEvolutionLockStore,
) -> None:
    """The diff paths all live inside skills/canonical/demo/ but a
    ``helpers.py`` sibling is not on the filename allowlist. This is
    the Security H4 branch."""
    diff = ProposedDiff(
        target_skill_id="demo",
        paths=frozenset(
            {
                "skills/canonical/demo/skill.md",
                "skills/canonical/demo/validator.py",
                "skills/canonical/demo/helpers.py",  # forbidden
                "skills/canonical/demo/fixtures/case.yaml",
            }
        ),
        target_runtimes=("claude",),
    )
    with pytest.raises(PolicyViolation) as exc:
        check_evolution_allowed(
            diff,
            registry=[_spec("demo", self_evolvable=True)],
            lock_store=empty_db,
        )
    assert exc.value.code == PolicyViolationCode.THIRD_FILE_SMUGGLING.value


def test_third_file_smuggling_rejects_outside_skill_dir(
    empty_db: SkillEvolutionLockStore,
) -> None:
    diff = ProposedDiff(
        target_skill_id="demo",
        paths=frozenset(
            {
                "skills/canonical/demo/skill.md",
                "skills/canonical/other-skill/skill.md",  # wrong skill
            }
        ),
        target_runtimes=("claude",),
    )
    with pytest.raises(PolicyViolation) as exc:
        check_evolution_allowed(
            diff,
            registry=[_spec("demo", self_evolvable=True)],
            lock_store=empty_db,
        )
    assert exc.value.code == PolicyViolationCode.THIRD_FILE_SMUGGLING.value


def test_fixtures_subdir_allowed(empty_db: SkillEvolutionLockStore) -> None:
    """Nested paths under fixtures/ must be allowed — the allowlist
    uses a ``fixtures/**`` glob."""
    diff = ProposedDiff(
        target_skill_id="demo",
        paths=frozenset(
            {
                "skills/canonical/demo/skill.md",
                "skills/canonical/demo/validator.py",
                "skills/canonical/demo/fixtures/nested/case.yaml",
            }
        ),
        target_runtimes=("claude",),
    )
    check_evolution_allowed(
        diff,
        registry=[_spec("demo", self_evolvable=True)],
        lock_store=empty_db,
    )


# ---------------------------------------------------------------------- #
# Fixture / skill atomicity                                               #
# ---------------------------------------------------------------------- #


def _canonical_with_incumbent(tmp_path, skill_id: str = "demo"):
    """Build a temp ``skills/canonical/<skill_id>/validator.py`` tree
    so ``check_fixture_skill_atomicity`` sees a real incumbent."""
    skill_dir = tmp_path / skill_id
    skill_dir.mkdir(parents=True)
    (skill_dir / "validator.py").write_text("# incumbent validator\n")
    return tmp_path


def test_validator_without_fixture_is_drift() -> None:
    diff = ProposedDiff(
        target_skill_id="demo",
        paths=frozenset({"skills/canonical/demo/validator.py"}),
    )
    with pytest.raises(PolicyViolation) as exc:
        check_fixture_skill_atomicity(diff)
    assert exc.value.code == PolicyViolationCode.FIXTURE_SKILL_DRIFT.value


def test_fixture_only_diff_is_drift_when_incumbent_exists(tmp_path) -> None:
    """Realistic drift case (kieran review, Blocker #1): a proposal
    that adds a new fixture to an existing skill, without touching
    the validator, should be rejected. The earlier implementation
    gated on ``removed_paths``, which never fires for this case."""
    root = _canonical_with_incumbent(tmp_path)
    diff = ProposedDiff(
        target_skill_id="demo",
        paths=frozenset({"skills/canonical/demo/fixtures/new_case.yaml"}),
    )
    with pytest.raises(PolicyViolation) as exc:
        check_fixture_skill_atomicity(diff, canonical_root=root)
    assert exc.value.code == PolicyViolationCode.FIXTURE_SKILL_DRIFT.value


def test_fixture_only_diff_passes_when_no_incumbent(tmp_path) -> None:
    """When no ``validator.py`` exists on disk yet, a fixture-only
    diff is legitimate new-skill staging. The allowlist check
    (tested elsewhere) still refuses in practice because the skill
    isn't in the registry, but atomicity itself must not raise."""
    diff = ProposedDiff(
        target_skill_id="brand-new",
        paths=frozenset({"skills/canonical/brand-new/fixtures/case.yaml"}),
    )
    check_fixture_skill_atomicity(diff, canonical_root=tmp_path)  # no raise


def test_atomic_diff_passes_fixture_check() -> None:
    diff = ProposedDiff(
        target_skill_id="demo",
        paths=frozenset(
            {
                "skills/canonical/demo/validator.py",
                "skills/canonical/demo/fixtures/case.yaml",
            }
        ),
    )
    check_fixture_skill_atomicity(diff)  # no raise


# ---------------------------------------------------------------------- #
# Runtime expansion                                                       #
# ---------------------------------------------------------------------- #


def test_runtime_expansion_to_codex_is_rejected(
    empty_db: SkillEvolutionLockStore,
) -> None:
    diff = ProposedDiff(
        target_skill_id="demo",
        paths=frozenset(
            {
                "skills/canonical/demo/skill.md",
                "skills/canonical/demo/validator.py",
                "skills/canonical/demo/fixtures/case.yaml",
            }
        ),
        target_runtimes=("claude", "codex"),
    )
    with pytest.raises(PolicyViolation) as exc:
        check_evolution_allowed(
            diff,
            registry=[_spec("demo", self_evolvable=True)],
            lock_store=empty_db,
        )
    assert exc.value.code == PolicyViolationCode.RUNTIME_EXPANSION_REQUIRES_HUMAN.value


def test_runtime_expansion_to_acp_is_rejected(
    empty_db: SkillEvolutionLockStore,
) -> None:
    diff = ProposedDiff(
        target_skill_id="demo",
        paths=frozenset(
            {
                "skills/canonical/demo/skill.md",
                "skills/canonical/demo/validator.py",
                "skills/canonical/demo/fixtures/case.yaml",
            }
        ),
        target_runtimes=("claude", "acp"),
    )
    with pytest.raises(PolicyViolation) as exc:
        check_evolution_allowed(
            diff,
            registry=[_spec("demo", self_evolvable=True)],
            lock_store=empty_db,
        )
    assert exc.value.code == PolicyViolationCode.RUNTIME_EXPANSION_REQUIRES_HUMAN.value


# ---------------------------------------------------------------------- #
# Concurrent lock probe                                                   #
# ---------------------------------------------------------------------- #


def test_concurrent_proposal_is_rejected(
    empty_db: SkillEvolutionLockStore,
) -> None:
    # Another worker already holds the lock on the same skill.
    # Stamp with real wall-clock time so the policy's is_locked
    # check — which always reads real time — sees it as live.
    import time

    real_now_us = int(time.time() * 1_000_000)
    other_lock = empty_db.acquire(
        skill_id="demo", worker_id="other", now_us=real_now_us
    )
    assert other_lock is not None

    with pytest.raises(PolicyViolation) as exc:
        check_evolution_allowed(
            _ok_diff(),
            registry=[_spec("demo", self_evolvable=True)],
            lock_store=empty_db,
        )
    assert (
        exc.value.code
        == PolicyViolationCode.CONCURRENT_EVOLUTION_IN_PROGRESS.value
    )


# The Voyager/DSPy regression-fixture gate is explicitly NOT
# implemented in the Phase 3 first landing. It will land as its own
# PR alongside a sandboxed two-validator import harness. See the
# module-level comment in packages/policies/skill_evolution.py for
# the design rationale. Until then, the HMAC-token reviewer is the
# regression gate — they confirm manually before signing.
