"""Phase 5.4 — Claude output policy.

Every strategic artifact Claude writes (product brief, mvp spec,
positioning pack, metadata draft, screenshot plan, artifact-chain
review, founder brief intake, GTM campaign brief) must carry a
machine-readable header so the platform can audit provenance:

- a YAML front-matter block (or an HTML comment fallback) containing
  ``last_updated`` (ISO date), ``source_session_id`` (the SupervisorSession
  that produced it), and, if the artifact has a declared parent in the
  product-artifact-chain, a ``parent`` link to that parent file.

``SupervisorSession.close()`` invokes :func:`validate_claude_output` on
every strategic artifact the session touched. Violations are raised as
:class:`ClaudeOutputViolation` with a ``code`` attribute so the caller
can log them into the session's close summary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_HTML_HEADER_RE = re.compile(
    r"<!--\s*claude-output(.*?)-->", re.DOTALL | re.IGNORECASE
)
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


class ClaudeOutputViolation(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class ClaudeOutputHeader:
    last_updated: str
    source_session_id: str
    parent: str | None


def _parse_header(text: str) -> dict[str, str]:
    match = _FRONT_MATTER_RE.search(text)
    if match:
        body = match.group(1)
    else:
        match = _HTML_HEADER_RE.search(text)
        if not match:
            raise ClaudeOutputViolation(
                "claude_output_header_missing",
                "no YAML front-matter and no <!-- claude-output ... --> block",
            )
        body = match.group(1)
    out: dict[str, str] = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def validate_claude_output(
    path: Path,
    *,
    expected_parent: str | None = None,
) -> ClaudeOutputHeader:
    """Parse + validate the header on ``path``.

    ``expected_parent`` is the file name (relative) of the declared
    parent node in ``packages/tools/product_artifacts/chain.yaml``; if
    provided, the header must reference it.
    """
    if not path.exists():
        raise ClaudeOutputViolation(
            "strategic_artifact_missing",
            f"{path} does not exist",
        )
    text = path.read_text(errors="replace")
    header = _parse_header(text)

    last_updated = header.get("last_updated", "")
    if not _ISO_DATE_RE.match(last_updated):
        raise ClaudeOutputViolation(
            "last_updated_missing",
            f"{path}: last_updated={last_updated!r} is not ISO YYYY-MM-DD",
        )
    session_id = header.get("source_session_id", "")
    if not session_id:
        raise ClaudeOutputViolation(
            "source_session_id_missing",
            f"{path}: source_session_id not declared",
        )
    parent = header.get("parent") or None
    if expected_parent:
        # Accept either the bare filename or a markdown-style link.
        if not parent or expected_parent not in parent:
            raise ClaudeOutputViolation(
                "parent_link_missing",
                f"{path}: expected parent reference to {expected_parent}, got {parent!r}",
            )
    return ClaudeOutputHeader(
        last_updated=last_updated,
        source_session_id=session_id,
        parent=parent,
    )
