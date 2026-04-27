"""PostMortem schema (harness learning loop, Phase 1).

A PostMortem is a typed, durable record of an observed failure that
needs founder follow-up: a stub is emitted by ``failure-mode-regression``
whenever it captures a fixture, and the founder later fills in the
``root_cause_category``, ``remediation_action``, ``owner`` fields.

Convention mirror of ``packages/schemas/task_run.py``: frozen dataclass,
ISO-8601 string timestamps (never ``datetime`` objects), ``str, Enum``
patterns, manual ``to_dict`` / ``from_dict``.

Security-relevant: ``__post_init__`` redacts every string field uniformly
so call sites cannot accidentally leave PII or secrets unredacted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class PostMortemSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class PostMortemStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in-progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont-fix"


class RootCauseCategory(str, Enum):
    AMBIGUOUS_TASK_SPEC = "ambiguous-task-spec"
    POLICY_MISS = "policy-miss"
    TOOL_LIMITATION = "tool-limitation"
    EXTERNAL_DEPENDENCY = "external-dependency"
    WORKER_PROMPT_DRIFT = "worker-prompt-drift"
    UNKNOWN = "unknown"


def _redact_string(value: str) -> str:
    """Redact a free-text field. Returns ``value`` unchanged if redaction
    is unavailable. Lazy import keeps schema importable in minimal envs.
    """
    try:
        from packages.tools.observability.redaction import redact

        return redact(value).text
    except Exception:
        return value


def _redact_path_field(value: str | None) -> str | None:
    """Strip user/home-dir prefixes from filesystem paths so postmortems
    do not leak ``/Users/<name>/...`` into shipped logs."""
    if value is None:
        return None
    redacted = _redact_string(value)
    for prefix in ("/Users/", "/home/", "/var/folders/"):
        idx = redacted.find(prefix)
        if idx >= 0:
            tail = redacted[idx + len(prefix) :]
            slash = tail.find("/")
            if slash >= 0:
                redacted = redacted[:idx] + prefix + "[REDACTED-USER]" + tail[slash:]
            else:
                redacted = redacted[:idx] + prefix + "[REDACTED-USER]"
    return redacted


@dataclass(frozen=True)
class PostMortem:
    id: str
    created_at: str
    updated_at: str
    failure_code: str
    lane: str
    task_id: str | None = None
    task_run_id: str | None = None
    fixture_path: str | None = None
    excerpt_redacted: str | None = None
    redaction_hits: int | None = None
    severity: PostMortemSeverity = PostMortemSeverity.WARN
    root_cause_category: RootCauseCategory = RootCauseCategory.UNKNOWN
    remediation_action: str = ""
    owner: str | None = None
    status: PostMortemStatus = PostMortemStatus.OPEN
    notes: str = ""
    schema_version: str = "1"

    def __post_init__(self) -> None:
        # Redact every free-text string field uniformly. Frozen dataclass
        # forces object.__setattr__ for the rewrite. This is the M1 fix:
        # call sites can no longer accidentally leave a field unredacted.
        object.__setattr__(self, "remediation_action", _redact_string(self.remediation_action))
        object.__setattr__(self, "notes", _redact_string(self.notes))
        if self.excerpt_redacted is not None:
            object.__setattr__(self, "excerpt_redacted", _redact_string(self.excerpt_redacted))
        if self.fixture_path is not None:
            object.__setattr__(self, "fixture_path", _redact_path_field(self.fixture_path))

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        payload["status"] = self.status.value
        payload["root_cause_category"] = self.root_cause_category.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "PostMortem":
        return cls(
            id=str(payload["id"]),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            failure_code=str(payload["failure_code"]),
            lane=str(payload["lane"]),
            task_id=str(payload["task_id"]) if payload.get("task_id") else None,
            task_run_id=str(payload["task_run_id"]) if payload.get("task_run_id") else None,
            fixture_path=str(payload["fixture_path"]) if payload.get("fixture_path") else None,
            excerpt_redacted=str(payload["excerpt_redacted"])
            if payload.get("excerpt_redacted") is not None
            else None,
            redaction_hits=int(payload["redaction_hits"])
            if payload.get("redaction_hits") is not None
            else None,
            severity=PostMortemSeverity(str(payload.get("severity", PostMortemSeverity.WARN.value))),
            root_cause_category=RootCauseCategory(
                str(payload.get("root_cause_category", RootCauseCategory.UNKNOWN.value))
            ),
            remediation_action=str(payload.get("remediation_action", "")),
            owner=str(payload["owner"]) if payload.get("owner") else None,
            status=PostMortemStatus(str(payload.get("status", PostMortemStatus.OPEN.value))),
            notes=str(payload.get("notes", "")),
            schema_version=str(payload.get("schema_version", "1")),
        )
