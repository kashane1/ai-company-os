"""Phase 2a — no legacy self_evolvable promotion (per todo 013).

Asserts every registry entry NOT in the Hermes Phase 3 allowlist has
`self_evolvable` either absent or explicitly `false`. Closes the flow
gap where a legacy entry could acquire `self_evolvable: true` without
going through the human-authored allowlist update.

The deferred `registry_schema_drift` stocktake check is the only
other thing that would catch this, and that check is not in the v1
stocktake set. So this test guards the invariant standalone.

Hermes Phase 3 ships with an empty allowlist — no skill currently
opts in to self-evolution. Any future allowlist addition MUST be
explicit here and in the matching policy wrapper.
"""
from __future__ import annotations

from packages.tools.skills.loader import load_registry

# Hermes Phase 3 self-evolution allowlist. Empty today. Any addition
# must be a human-authored PR that touches both this set and the
# policy wrapper at packages/policies/skill_evolution.py.
HERMES_SELF_EVOLVABLE_ALLOWLIST: frozenset[str] = frozenset()


def test_no_legacy_self_evolvable_promotion() -> None:
    """Every non-allowlisted registry entry has self_evolvable == False."""
    registry = load_registry()
    violations: list[str] = []
    for spec in registry:
        if spec.id in HERMES_SELF_EVOLVABLE_ALLOWLIST:
            continue
        if spec.self_evolvable:
            violations.append(spec.id)
    assert not violations, (
        f"Registry entries {violations!r} have self_evolvable=true but are "
        "not in HERMES_SELF_EVOLVABLE_ALLOWLIST. Promoting a skill to "
        "self-evolvable requires a human-authored PR that updates this "
        "test and packages/policies/skill_evolution.py together."
    )
