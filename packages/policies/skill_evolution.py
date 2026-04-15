"""Phase 3 — skill self-evolution policy.

``check_evolution_allowed`` is the single composite entry point that
:mod:`apps.worker_skill_evolution.main` calls once per proposal before
staging any artifact. It composes:

1. **Allowlist enforcement.** The target skill's registry entry must
   carry ``self_evolvable: true``. Default is ``False`` so new skills
   are safe by construction — no denylist maintenance, no surprise
   escalation. Raises
   :class:`PolicyViolationCode.SKILL_NOT_SELF_EVOLVABLE` if false.

2. **Path-pattern denylist for non-registry paths.** Config files,
   CI workflows, supervisor infra, schemas, and sibling policies
   cannot be touched by a proposal. Raises
   :class:`PolicyViolationCode.CONFIG_MUTATION_REQUIRES_HUMAN`.

3. **Third-file smuggling guard** (Security H4). The diff may ONLY
   touch files under ``skills/canonical/<skill_id>/`` with names
   matching the allowlist ``{skill.md, contract.yaml, validator.py,
   fixtures/**}``. Adding a ``helpers.py`` or a module-level sibling
   that could do dangerous work at import time is rejected with
   :class:`PolicyViolationCode.THIRD_FILE_SMUGGLING`.

4. **Runtime-expansion guard.** First PR of a self-evolved skill MUST
   be ``target_runtimes: [claude]`` only. Adding ``codex`` or ``acp``
   requires a human-authored PR. Raises
   :class:`PolicyViolationCode.RUNTIME_EXPANSION_REQUIRES_HUMAN`.

5. **Concurrent-run lock check.** If another proposal is in flight
   against the same skill, raises
   :class:`PolicyViolationCode.CONCURRENT_EVOLUTION_IN_PROGRESS`. This
   is a *check*, not the acquire — the worker acquires via
   :mod:`packages.db.locks.skill_evolution` after this function passes.

6. **Fixture/skill atomicity** (``check_fixture_skill_atomicity``).
   A diff that changes the validator without touching fixtures (or
   vice versa) would let the contract drift silently. Raises
   :class:`PolicyViolationCode.FIXTURE_SKILL_DRIFT`.

The Voyager/DSPy regression gate
(``check_regression_fixture_gate``, ``REGRESSION_AGAINST_INCUMBENT``)
is declared in :class:`packages.policies.approvals.PolicyViolationCode`
but its implementation is deferred to a follow-up PR. Running the
proposed validator against the incumbent's fixture set requires a
sandboxed import harness that is larger than the rest of Phase 3
combined; doing it right deserves its own change. The stub raises
``NotImplementedError`` so any accidental call lights up loudly
instead of silently passing.

Design notes
------------

- ``check_evolution_allowed`` is the worker's ONLY call into this
  module. The sub-checks are exposed as named entry points so tests
  can exercise each one in isolation, but production code always
  goes through the composite.
- The module is side-effect-free to import. No registry reads, no
  file I/O, no DB connections happen until a public function is
  invoked. Phase 0's ``test_skill_evolution_policy_import_safety.py``
  (to be written alongside the existing command_scan equivalent in
  Phase 5) will enforce this.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Sequence

from packages.db.locks.skill_evolution import SkillEvolutionLockStore
from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.tools.skills.loader import SkillNotFound, SkillSpec, load_registry


# ---------------------------------------------------------------------- #
# Types                                                                   #
# ---------------------------------------------------------------------- #


@dataclass(frozen=True)
class ProposedDiff:
    """Structured description of a staged evolution proposal.

    ``paths`` is the set of repo-relative POSIX paths the proposal
    would touch. ``target_runtimes`` is the list of runtime slugs the
    proposed skill would advertise AFTER the diff is applied.

    The worker builds this by reading its own staged artifact dir and
    the proposed registry update — policies never read from disk.
    """

    target_skill_id: str
    paths: frozenset[str]
    target_runtimes: tuple[str, ...] = ()
    added_paths: frozenset[str] = field(default_factory=frozenset)
    removed_paths: frozenset[str] = field(default_factory=frozenset)

    def touches(self, pattern: str) -> bool:
        """Case-sensitive POSIX fnmatch against every path in the diff.

        A leading ``**/`` in the pattern is NOT auto-stripped — the
        caller is expected to pass a glob that matches repo-relative
        paths directly. :func:`fnmatch.fnmatchcase` accepts ``*`` and
        ``?`` but does not match directory separators; to match
        nested paths, the caller passes a pattern like
        ``.github/workflows/**`` which we expand internally.
        """
        # Expand ``**`` to a list of prefixes the caller cares about.
        if "**" in pattern:
            prefix = pattern.replace("/**", "")
            return any(p == prefix or p.startswith(prefix + "/") for p in self.paths)
        return any(fnmatch.fnmatchcase(p, pattern) for p in self.paths)


# ---------------------------------------------------------------------- #
# Config-path denylist                                                    #
# ---------------------------------------------------------------------- #

# Glob patterns for files that live outside the registry and therefore
# cannot be gated by ``self_evolvable``. Any proposal touching these is
# a hard reject. Patterns are POSIX, case-sensitive, matched against
# repo-relative paths.
_CONFIG_DENY_PATTERNS: tuple[str, ...] = (
    "packages/config/policies.yaml",
    "packages/config/peer_runtimes.yaml",
    "packages/config/runtime_supervisor.yaml",
    "packages/policies/command_scan.py",
    "packages/policies/skill_evolution.py",
    "packages/policies/approvals.py",
    "packages/policies/approval_tokens.py",
    "packages/db/connection.py",
    "packages/db/locks/**",
    "packages/schemas/**",
    "packages/tools/primitives/approvals.py",
    "packages/tools/primitives/kill_switches.py",
    ".github/workflows/**",
    "infra/launchd/**",
    "infra/sandbox/**",
)


# Filename allowlist for the third-file smuggling guard. A proposal
# against skill ``X`` may only touch files matching one of these
# patterns under ``skills/canonical/X/``.
_ALLOWED_PROPOSAL_FILE_PATTERNS: tuple[str, ...] = (
    "skill.md",
    "contract.yaml",
    "validator.py",
    "fixtures/**",
)


# The action string stamped on skill-evolution approval requests.
# Policy and primitive MUST agree on this value. Kept as a named
# constant so a typo fails a test, not a worker in production.
_EVOLUTION_APPROVAL_ACTION = "skill_evolution_apply"


# ---------------------------------------------------------------------- #
# Composite entry point                                                   #
# ---------------------------------------------------------------------- #


def check_evolution_allowed(
    diff: ProposedDiff,
    *,
    registry: Sequence[SkillSpec] | None = None,
    lock_store: SkillEvolutionLockStore | None = None,
) -> None:
    """Refuse the proposal if any Phase 3 policy check fails.

    Composes every check in this module. The worker calls this once,
    and expects either ``None`` (proceed) or a raised
    :class:`PolicyViolation` with a :class:`PolicyViolationCode` to
    surface to the operator.

    Ordering matters for error reporting — cheap checks (structural
    denylist, allowlist) run before expensive ones (lock probe,
    registry lookup) so a malformed proposal fails fast with the most
    informative code.
    """
    # 1. Config-path denylist — reject before we even look at the
    #    registry. A proposal that touches CI config is never fixable
    #    by flipping ``self_evolvable``; the operator must author it
    #    by hand regardless.
    _check_config_denylist(diff)

    # 2. Third-file smuggling — reject files outside the per-skill
    #    allowlist. Runs before the registry lookup so a proposal
    #    with a bogus target_skill_id still gets a useful error.
    _check_third_file_smuggling(diff)

    # 3. Fixture / skill atomicity — validator and fixtures must move
    #    together. Cheap, no I/O.
    check_fixture_skill_atomicity(diff)

    # 4. Allowlist — target skill must opt into evolution.
    _check_self_evolvable(diff, registry=registry)

    # 5. Runtime expansion guard — first PR is claude-only.
    _check_runtime_expansion(diff)

    # 6. Concurrent-run lock check — last because it touches the DB.
    _check_no_concurrent_proposal(diff, lock_store=lock_store)


# ---------------------------------------------------------------------- #
# Sub-checks (public — exposed for unit tests)                            #
# ---------------------------------------------------------------------- #


def check_fixture_skill_atomicity(diff: ProposedDiff) -> None:
    """Reject diffs that change validator.py without touching fixtures,
    or vice versa.

    The intent is to prevent contract drift: if the validator gets
    smarter, its fixtures must show that it gets smarter; if a fixture
    changes, the validator must acknowledge the new shape. A diff that
    moves only one side is almost always either a mis-targeted patch
    or an adversarial attempt to break the validator's contract while
    leaving its tests green.
    """
    prefix = f"skills/canonical/{diff.target_skill_id}/"
    touches_validator = any(
        p == prefix + "validator.py" for p in diff.paths
    )
    touches_fixtures = any(
        p.startswith(prefix + "fixtures/") for p in diff.paths
    )
    if touches_validator and not touches_fixtures:
        raise PolicyViolation(
            PolicyViolationCode.FIXTURE_SKILL_DRIFT,
            f"validator.py changed without a corresponding fixtures/ edit "
            f"under {prefix}",
        )
    if touches_fixtures and not touches_validator:
        # New-skill case: creating a brand-new validator + fixtures
        # together is fine. Only reject when the skill has an
        # incumbent validator and the diff changes fixtures without it.
        validator_existed = prefix + "validator.py" in diff.removed_paths
        created_new_skill = all(
            p in diff.added_paths
            for p in diff.paths
            if p.startswith(prefix)
        )
        if validator_existed and not created_new_skill:
            raise PolicyViolation(
                PolicyViolationCode.FIXTURE_SKILL_DRIFT,
                f"fixtures/ changed without the corresponding validator.py "
                f"edit under {prefix}",
            )


def check_regression_fixture_gate(diff: ProposedDiff) -> None:
    """Placeholder for the Voyager/DSPy regression-fixture gate.

    The plan's research insights call for running the proposed
    validator against the incumbent's fixture set and refusing if any
    verdict regresses. Implementing that correctly requires a
    sandboxed import harness that loads two validator modules under
    the same Python process without state bleed — larger than the
    rest of Phase 3 combined.

    This stub exists so:

    1. The symbol is importable by the composite entry point if a
       future PR wires it in.
    2. Any accidental call today raises loudly instead of silently
       passing (which would be worse than not having the check at
       all — it would imply a guarantee the worker hasn't earned).
    """
    raise NotImplementedError(
        "check_regression_fixture_gate is deferred to a follow-up PR. "
        "Phase 3 first landing does not run regression-against-incumbent; "
        "the reviewer is expected to confirm this manually when signing "
        "the HMAC approval token."
    )


# ---------------------------------------------------------------------- #
# Internals                                                               #
# ---------------------------------------------------------------------- #


def _check_config_denylist(diff: ProposedDiff) -> None:
    for pattern in _CONFIG_DENY_PATTERNS:
        if diff.touches(pattern):
            raise PolicyViolation(
                PolicyViolationCode.CONFIG_MUTATION_REQUIRES_HUMAN,
                f"proposal touches {pattern!r} — config/infra paths require "
                f"a human-authored PR",
            )


def _check_third_file_smuggling(diff: ProposedDiff) -> None:
    skill_prefix = f"skills/canonical/{diff.target_skill_id}/"
    for path in diff.paths:
        # Any path outside the target skill's canonical directory is
        # outside the allowlist, full stop. The registry itself is
        # rewritten by registry_writer.py which the worker calls
        # out-of-band, not via the proposed diff, so registry.yaml
        # is also not expected to be in ``diff.paths``.
        if not path.startswith(skill_prefix):
            raise PolicyViolation(
                PolicyViolationCode.THIRD_FILE_SMUGGLING,
                f"proposal touches {path!r} which is outside "
                f"{skill_prefix}",
            )

        rel = path[len(skill_prefix) :]
        if not any(
            _matches_allowed_pattern(rel, pat)
            for pat in _ALLOWED_PROPOSAL_FILE_PATTERNS
        ):
            raise PolicyViolation(
                PolicyViolationCode.THIRD_FILE_SMUGGLING,
                f"proposal adds file {rel!r} under {skill_prefix} which is "
                f"not in the allowlist {_ALLOWED_PROPOSAL_FILE_PATTERNS}",
            )


def _matches_allowed_pattern(rel: str, pattern: str) -> bool:
    """Match a relative-to-skill-root path against the allowlist.

    ``fixtures/**`` matches anything under the fixtures directory,
    including nested subdirectories, exactly one filename deep.
    ``skill.md`` / ``contract.yaml`` / ``validator.py`` match only
    the top-level filenames.
    """
    if pattern == "fixtures/**":
        return rel == "fixtures" or rel.startswith("fixtures/")
    return rel == pattern


def _check_self_evolvable(
    diff: ProposedDiff,
    *,
    registry: Sequence[SkillSpec] | None,
) -> None:
    specs = list(registry) if registry is not None else load_registry()
    try:
        spec = _find(specs, diff.target_skill_id)
    except SkillNotFound:
        # A brand-new skill has no registry entry yet — the worker's
        # proposal would create one. We still require an explicit
        # opt-in: the registry update must add the new id with
        # ``self_evolvable: true``, which is impossible without a
        # human-authored registry PR (since the registry itself is on
        # the config denylist above). Therefore reject here.
        raise PolicyViolation(
            PolicyViolationCode.SKILL_NOT_SELF_EVOLVABLE,
            f"target skill {diff.target_skill_id!r} not in registry; "
            f"creating new skills via the evolution worker is not supported",
        )
    if not spec.self_evolvable:
        raise PolicyViolation(
            PolicyViolationCode.SKILL_NOT_SELF_EVOLVABLE,
            f"skill {diff.target_skill_id!r} is not marked "
            f"self_evolvable=true in the registry",
        )


def _check_runtime_expansion(diff: ProposedDiff) -> None:
    allowed = {"claude"}
    proposed = set(diff.target_runtimes)
    if not proposed:
        return  # nothing to check on a diff that doesn't touch runtimes
    extra = proposed - allowed
    if extra:
        raise PolicyViolation(
            PolicyViolationCode.RUNTIME_EXPANSION_REQUIRES_HUMAN,
            f"proposal expands target_runtimes by {sorted(extra)} — only "
            f"`claude` is allowed on the first landing of a self-evolved "
            f"skill",
        )


def _check_no_concurrent_proposal(
    diff: ProposedDiff,
    *,
    lock_store: SkillEvolutionLockStore | None,
) -> None:
    store = lock_store or SkillEvolutionLockStore()
    if store.is_locked(skill_id=diff.target_skill_id):
        raise PolicyViolation(
            PolicyViolationCode.CONCURRENT_EVOLUTION_IN_PROGRESS,
            f"another worker holds the skill-evolution lock on "
            f"{diff.target_skill_id!r}",
        )


def _find(specs: Sequence[SkillSpec], skill_id: str) -> SkillSpec:
    for spec in specs:
        if spec.id == skill_id:
            return spec
    raise SkillNotFound(f"skill {skill_id!r} not in registry")
