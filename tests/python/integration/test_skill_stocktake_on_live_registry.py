"""Phase 2a integration test — skill-stocktake on the real registry.

Runs `check_drift()` against the real repo state. Per the plan's
"drift captured, not drift fixed" pattern (Phase 2a deepening
finding), pre-existing drift is tagged as `known_drift` rather than
fixed in-PR. A drift item whose skill_id or affected_path matches
any entry in KNOWN_DRIFT is allowed; everything else is a hard
failure.

Known drift:

- `post-run-validation`: the registry entry `path:` points at
  `canonical/shared/post-run-validation.md` but the actual skill
  directory is `canonical/post-run-validation/skill.md`. This is
  pre-existing debt outside this plan's scope. Follow-up issue
  captured via `followup_issue_writer`.
"""
from __future__ import annotations

from packages.tools.primitives.registry_drift import check_drift


# Pre-existing drift that Phase 2a does not fix. Each entry is a
# tuple of (drift_type, matching_substring_in_detail_or_path).
KNOWN_LIVE_DRIFT = frozenset(
    {
        ("orphan_canonical", "post-run-validation"),
    }
)


def _is_known(item_drift_type: str, item_detail: str, item_path: str) -> bool:
    for known_type, known_match in KNOWN_LIVE_DRIFT:
        if item_drift_type == known_type and (
            known_match in item_detail or known_match in item_path
        ):
            return True
    return False


def test_live_registry_stocktake_only_known_drift() -> None:
    report = check_drift()
    assert report.registry_entries_checked > 0

    unknown = [
        item
        for item in report.drift_items
        if not _is_known(
            item.drift_type, item.detail, item.affected_path
        )
    ]
    assert not unknown, (
        f"skill-stocktake surfaced {len(unknown)} drift item(s) "
        "not in KNOWN_LIVE_DRIFT:\n"
        + "\n".join(f"  - {it.drift_type}: {it.detail}" for it in unknown)
        + "\nEither fix the drift or add it to KNOWN_LIVE_DRIFT with "
        "a follow-up issue captured via followup_issue_writer."
    )
