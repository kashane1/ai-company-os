"""Phase 3 — approval-reviewer CLI.

A small, deliberately boring command-line tool that a human runs to:

1. ``list`` — show every pending skill-evolution approval with its
   staged artifact dir, rationale, and the magic-link token the
   reviewer will burn when signing.
2. ``show <approval_id>`` — render the proposal artifact dir
   contents (diff, rationale, manifest) so the reviewer can read
   what they're about to sign without leaving the terminal.
3. ``sign <approval_id>`` — verify the HMAC signature on the token
   and flip the underlying :class:`ApprovalRecord` to ``approved``.
   The worker's next poll will see the new status and proceed.
4. ``reject <approval_id> --reason "..."`` — mark the approval
   ``rejected`` so the worker can quarantine the staged artifact
   and re-queue or give up.

The CLI reads its HMAC signing secret via the same
:func:`packages.tools.primitives.approvals._load_signing_secret`
path the worker uses, so a single machine can sign the tokens it
issues without any out-of-band key transport.

Deliberately NOT here (all follow-up):

- ``rich``-printed side-by-side diffs. First landing uses plain
  ``print``; tests don't want TUI dependencies.
- GitHub PR integration (Option C). Sign today = write the decision
  to :class:`ApprovalStore`. A future wrapper can open a PR from
  the same approval_id without changing this CLI.
- macOS Keychain prompts. The signing secret lives on disk mode 0600
  for the first landing; Keychain is a one-place swap in
  ``_load_signing_secret``.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.config.settings import load_runtime_paths
from packages.db.approval_store import ApprovalStore
from packages.db.approval_token_store import ApprovalTokenStore
from packages.schemas.approval import ApprovalStatus
from packages.tools.primitives.approvals import (
    ApprovalTokenError,
    SKILL_EVOLUTION_APPROVAL_TYPE,
    reject_evolution_approval,
    submit_evolution_approval,
)


# ---------------------------------------------------------------------- #
# Commands                                                                #
# ---------------------------------------------------------------------- #


def cmd_list(args: argparse.Namespace) -> int:
    """List pending skill-evolution approvals.

    Filters to ``approval_type == skill_evolution`` and
    ``status == pending`` so the reviewer sees only actionable items.
    Sorted by ``created_at`` so the oldest request surfaces first.
    """
    store = ApprovalStore()
    token_store = ApprovalTokenStore()
    pending = _list_pending_skill_evolution(store)
    if not pending:
        print("no pending skill-evolution approvals")
        return 0

    for record in pending:
        tokens = token_store.list_by_approval(record.id)
        token = tokens[0] if tokens else None
        print(f"approval_id : {record.id}")
        print(f"target_skill: {record.subject_id}")
        print(f"created_at  : {record.created_at}")
        print(f"rationale   : {record.summary}")
        print(f"artifact    : {record.review_artifact_path}")
        if token is not None:
            print(f"token_id    : {token.token_id}")
            print(f"signature   : {token.signature}")
        else:
            print("token_id    : (missing — worker did not issue a token)")
        print()
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Render the artifact directory for a single approval.

    Prints every file in ``artifact_dir`` that is small enough to
    read safely. Binary files are listed by size only. ``diff.patch``
    is always streamed in full so the reviewer sees what they would
    be approving.
    """
    store = ApprovalStore()
    try:
        record = store.load(args.approval_id)
    except FileNotFoundError:
        print(f"error: approval {args.approval_id!r} not found", file=sys.stderr)
        return 2

    if record.approval_type != SKILL_EVOLUTION_APPROVAL_TYPE:
        print(
            f"error: approval {args.approval_id!r} is not a skill-evolution "
            f"approval (type={record.approval_type!r})",
            file=sys.stderr,
        )
        return 2

    print(f"approval_id : {record.id}")
    print(f"status      : {record.status.value}")
    print(f"target_skill: {record.subject_id}")
    print(f"created_at  : {record.created_at}")
    print(f"rationale   : {record.summary}")
    print()
    artifact_dir = (
        Path(record.review_artifact_path) if record.review_artifact_path else None
    )
    if artifact_dir is None or not artifact_dir.exists():
        print("(no artifact directory found)")
        return 0

    print(f"artifact_dir: {artifact_dir}")
    print("-" * 60)
    for entry in sorted(artifact_dir.iterdir()):
        if entry.is_dir():
            print(f"  dir  {entry.name}/")
            continue
        size = entry.stat().st_size
        print(f"  file {entry.name} ({size} bytes)")
    print()

    # Always show the diff + rationale in full.
    for name in ("rationale.md", "diff.patch"):
        target = artifact_dir / name
        if not target.exists():
            continue
        print(f"=== {name} ===")
        print(target.read_text())
        print()
    return 0


def cmd_sign(args: argparse.Namespace) -> int:
    """Verify HMAC + flip the approval record to ``approved``.

    The reviewer passes ``--token-id`` and ``--signature`` — both are
    what the worker wrote into the approval request when it was
    staged. The CLI can read them off the matching
    :class:`ApprovalTokenStore` entry, so ``--token-id`` is optional
    (we pick the most recent token for the approval id).
    """
    store = ApprovalStore()
    tokens = ApprovalTokenStore()
    try:
        record = store.load(args.approval_id)
    except FileNotFoundError:
        print(f"error: approval {args.approval_id!r} not found", file=sys.stderr)
        return 2

    if record.approval_type != SKILL_EVOLUTION_APPROVAL_TYPE:
        print(
            f"error: approval {args.approval_id!r} is not a skill-evolution "
            f"approval",
            file=sys.stderr,
        )
        return 2
    if record.status is not ApprovalStatus.PENDING:
        print(
            f"error: approval {args.approval_id!r} is already "
            f"{record.status.value}",
            file=sys.stderr,
        )
        return 2

    token_id = args.token_id
    signature = args.signature
    if token_id is None or signature is None:
        candidates = tokens.list_by_approval(args.approval_id)
        if not candidates:
            print(
                f"error: no token on file for approval {args.approval_id!r}",
                file=sys.stderr,
            )
            return 2
        latest = sorted(candidates, key=lambda t: t.issued_at, reverse=True)[0]
        token_id = token_id or latest.token_id
        signature = signature or latest.signature

    try:
        decision = submit_evolution_approval(
            approval_id=args.approval_id,
            token_id=token_id,
            provided_signature=signature,
            device_fingerprint=args.device or _default_device(),
            decided_by=args.reviewer or _default_reviewer(),
            decision_notes=args.note,
        )
    except ApprovalTokenError as exc:
        print(
            f"error: token rejected ({type(exc).__name__}): {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"approved: {decision.approval_id} by {decision.decided_by}")
    return 0


def cmd_reject(args: argparse.Namespace) -> int:
    """Mark an approval ``rejected`` without touching the token.

    See ``packages/tools/primitives/approvals.py:reject_evolution_approval``
    for why rejection doesn't need HMAC verification.
    """
    store = ApprovalStore()
    try:
        record = store.load(args.approval_id)
    except FileNotFoundError:
        print(f"error: approval {args.approval_id!r} not found", file=sys.stderr)
        return 2
    if record.status is not ApprovalStatus.PENDING:
        print(
            f"error: approval {args.approval_id!r} is already "
            f"{record.status.value}",
            file=sys.stderr,
        )
        return 2

    decision = reject_evolution_approval(
        approval_id=args.approval_id,
        decided_by=args.reviewer or _default_reviewer(),
        decision_notes=args.reason,
    )
    print(f"rejected: {decision.approval_id} by {decision.decided_by}")
    return 0


# ---------------------------------------------------------------------- #
# Helpers                                                                 #
# ---------------------------------------------------------------------- #


def _list_pending_skill_evolution(store: ApprovalStore) -> list:
    """Read the raw :class:`ControlPlaneDatabase` rows for pending
    skill-evolution approvals.

    We do a direct query rather than adding a new method on
    :class:`ApprovalStore` so the CLI stays self-contained and the
    store's surface doesn't grow for a one-off list operation.
    """
    from packages.db.contracts import APPROVALS_TABLE

    db = store.db
    query = f"""
        SELECT id
          FROM {APPROVALS_TABLE}
         WHERE status = {db.placeholder("status")}
           AND approval_type = {db.placeholder("approval_type")}
         ORDER BY created_at ASC
    """
    rows = db.fetch_all(
        query,
        {
            "status": ApprovalStatus.PENDING.value,
            "approval_type": SKILL_EVOLUTION_APPROVAL_TYPE,
        },
    )
    return [store.load(row["id"]) for row in rows if row.get("id")]


def _default_reviewer() -> str:
    """Build a short default "who is signing" string from env.

    Falls through to ``human@<hostname>`` when ``USER`` is unset (CI
    containers). The reviewer can always override with ``--reviewer``.
    """
    import os

    user = os.environ.get("USER") or "human"
    host = socket.gethostname() or "unknown-host"
    return f"{user}@{host}"


def _default_device() -> str:
    return socket.gethostname() or "unknown-device"


# ---------------------------------------------------------------------- #
# Parser                                                                  #
# ---------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="approval-reviewer",
        description=(
            "Human-operated CLI for signing Phase 3 skill-evolution "
            "approval tokens."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list pending approvals")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="render one approval's artifacts")
    p_show.add_argument("approval_id")
    p_show.set_defaults(func=cmd_show)

    p_sign = sub.add_parser("sign", help="verify + approve one request")
    p_sign.add_argument("approval_id")
    p_sign.add_argument(
        "--token-id",
        default=None,
        help="override the token_id (defaults to latest token for approval)",
    )
    p_sign.add_argument(
        "--signature",
        default=None,
        help="override the signature (defaults to the one on file)",
    )
    p_sign.add_argument(
        "--reviewer",
        default=None,
        help="decided_by string (defaults to USER@hostname)",
    )
    p_sign.add_argument(
        "--device",
        default=None,
        help="device fingerprint (defaults to hostname)",
    )
    p_sign.add_argument(
        "--note",
        default=None,
        help="optional decision note attached to the approval record",
    )
    p_sign.set_defaults(func=cmd_sign)

    p_reject = sub.add_parser("reject", help="mark one request as rejected")
    p_reject.add_argument("approval_id")
    p_reject.add_argument(
        "--reason",
        required=True,
        help="short explanation recorded on the approval record",
    )
    p_reject.add_argument(
        "--reviewer",
        default=None,
        help="decided_by string (defaults to USER@hostname)",
    )
    p_reject.set_defaults(func=cmd_reject)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
