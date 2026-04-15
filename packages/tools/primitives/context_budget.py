"""Context-budget primitive (ECC Gap Recommendations Phase 2b).

Counts approximate tokens across every adapter file, canonical body,
and project-skill pointer, buckets the totals by `owner_agent` lane,
and produces a per-lane report. Pure-Python deterministic; imports
`tiktoken` lazily (inside `count_tokens()`) with a char-count fallback
when `tiktoken` is unavailable.

Per deepening finding #4, this first landing REPORTS NUMBERS, NOT
VERDICTS. No `LANE_THRESHOLDS`, no `over_threshold_lanes`, no
`packages/policies/context_budget.py`. Threshold-setting waits until
the baseline run produces real numbers and an incident motivates a
specific cap. The validator's `verdict` is always `"pass"` — the
report carries the measurements, the operator interprets them.

Convention per the primitives ADR:
- Stateless module-level.
- tiktoken import is lazy, inside `count_tokens()`.
- Typed frozen-dataclass returns serialized via `json_safe_factory`.
- No imports from `packages/tools/skills/`.

Lanes are `owner_agent` values from the registry. A special
`system_prompt` lane (per todo 014) sums CLAUDE.md + every
discoverable `.claude/skills/*.md` pointer; MCP block discovery is a
v2 TODO documented in the report.
"""
from __future__ import annotations

import functools
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from packages.tools.primitives._safe_paths import UnsafePathError, safe_join
from packages.tools.primitives._serialization import json_safe_factory


Tokenizer = Literal["tiktoken:o200k_base", "char_count_fallback"]
# Tightness of the char-count fallback heuristic. Matches the
# conventional "4 chars per token" rule-of-thumb for English prose.
CHAR_PER_TOKEN_DIVISOR = 4


@dataclass(frozen=True)
class SkillSize:
    skill_id: str
    lane: str
    canonical_tokens: int
    adapter_tokens: int
    project_skill_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class LaneBudget:
    lane: str
    total_tokens: int
    skill_count: int


@dataclass(frozen=True)
class SystemPromptBreakdown:
    claude_md_tokens: int
    project_skill_pointer_tokens: int
    mcp_block_tokens: int  # v1 always 0 with a TODO note
    total_tokens: int


@dataclass(frozen=True)
class ContextBudgetReport:
    schema_version: str
    tokenizer: Tokenizer
    tokenizer_version: str
    lanes: tuple[LaneBudget, ...]
    top_largest: tuple[SkillSize, ...]
    system_prompt: SystemPromptBreakdown
    notes: tuple[str, ...]


@functools.lru_cache(maxsize=1)
def _encoder() -> Any | None:
    """Lazily load the tiktoken `o200k_base` encoder.

    Returns None when `tiktoken` is unavailable so callers can fall
    through to the char-count path. Cached so warm calls amortize
    the 100-200 ms cold-start cost.
    """
    try:
        import tiktoken  # lazy; primitives convention forbids top-level
    except ImportError:
        return None
    try:
        return tiktoken.get_encoding("o200k_base")
    except Exception:
        return None


def count_tokens(text: str) -> int:
    """Return an approximate token count for `text`.

    Uses `tiktoken.o200k_base` when available; otherwise
    `len(text) // CHAR_PER_TOKEN_DIVISOR`. The char-count fallback
    under-counts real tokens for some inputs (tightly packed
    punctuation, CJK) and over-counts for others (ASCII code with
    short tokens); it is "good enough" for lane-level budgets but
    NOT for gating decisions.

    The fallback divisor is conservative by design.
    """
    if not isinstance(text, str):
        raise TypeError(
            f"count_tokens expects str, got {type(text).__name__}"
        )
    enc = _encoder()
    if enc is not None:
        return len(enc.encode(text))
    return max(1, len(text) // CHAR_PER_TOKEN_DIVISOR) if text else 0


def _detect_tokenizer() -> tuple[Tokenizer, str]:
    enc = _encoder()
    if enc is not None:
        try:
            import tiktoken
            version = getattr(tiktoken, "__version__", "unknown")
        except ImportError:
            version = "unknown"
        return "tiktoken:o200k_base", version
    return "char_count_fallback", "builtin"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _skills_root() -> Path:
    return _repo_root() / "skills"


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text()
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return ""


def _load_registry_yaml(registry_path: Path | None) -> list[dict]:
    path = registry_path or (_skills_root() / "registry.yaml")
    raw = yaml.safe_load(path.read_text()) or {}
    return list(raw.get("skills", []) or [])


def count_by_lane(
    registry_path: Path | None = None,
) -> dict[str, Any]:
    """Walk the registry and return per-lane totals + top-N.

    Returns a dict mapping `lane -> LaneBudget`-shaped sub-dict so
    the callable is cheap to consume directly. For the fully-typed
    report with `system_prompt` lane + metadata, use `measure()`.
    """
    report = measure(registry_path=registry_path)
    return {
        lb.lane: {"total_tokens": lb.total_tokens, "skill_count": lb.skill_count}
        for lb in report.lanes
    }


def measure(
    registry_path: Path | None = None, *, top_n: int = 10
) -> ContextBudgetReport:
    """Measure per-lane token totals across the skill surface.

    Returns a typed `ContextBudgetReport`. No verdict, no threshold
    check — the report carries the measurements and the operator
    (or a future Phase 3 composer) decides what to do with them.
    """
    skills_root = _skills_root()
    repo_root = _repo_root()
    entries = _load_registry_yaml(registry_path)

    per_skill: list[SkillSize] = []
    per_lane_totals: dict[str, int] = {}
    per_lane_count: dict[str, int] = {}
    notes: list[str] = []

    for entry in entries:
        skill_id = entry.get("id", "<unknown>")
        lane = entry.get("owner_agent") or "any"

        canonical_path = entry.get("path") or ""
        canonical_tokens = 0
        if canonical_path:
            try:
                full = safe_join(skills_root, canonical_path)
                canonical_tokens = count_tokens(_read_text_safe(full))
            except UnsafePathError as exc:
                notes.append(
                    f"{skill_id}: canonical path refused by safe_join: {exc}"
                )

        adapter_tokens = 0
        adapters_map = entry.get("adapters") or {}
        for _runtime, adapter_rel in adapters_map.items():
            if not isinstance(adapter_rel, str):
                continue
            try:
                full = safe_join(skills_root, adapter_rel)
                adapter_tokens += count_tokens(_read_text_safe(full))
            except UnsafePathError as exc:
                notes.append(
                    f"{skill_id}: adapter path refused by safe_join: {exc}"
                )

        project_skill_tokens = 0
        project_skill_rel = entry.get("project_skill")
        if project_skill_rel:
            project_skill_path = repo_root / project_skill_rel
            project_skill_tokens = count_tokens(
                _read_text_safe(project_skill_path)
            )

        total = canonical_tokens + adapter_tokens + project_skill_tokens
        per_skill.append(
            SkillSize(
                skill_id=skill_id,
                lane=lane,
                canonical_tokens=canonical_tokens,
                adapter_tokens=adapter_tokens,
                project_skill_tokens=project_skill_tokens,
                total_tokens=total,
            )
        )
        per_lane_totals[lane] = per_lane_totals.get(lane, 0) + total
        per_lane_count[lane] = per_lane_count.get(lane, 0) + 1

    lanes = tuple(
        sorted(
            (
                LaneBudget(
                    lane=lane,
                    total_tokens=total,
                    skill_count=per_lane_count[lane],
                )
                for lane, total in per_lane_totals.items()
            ),
            key=lambda lb: lb.total_tokens,
            reverse=True,
        )
    )

    top_largest = tuple(
        sorted(per_skill, key=lambda s: s.total_tokens, reverse=True)[:top_n]
    )

    # system_prompt lane (todo 014). v1 scope: CLAUDE.md + every
    # .claude/skills/*.md pointer. MCP block discovery is deferred
    # with an explicit TODO note so the gap is visible.
    claude_md_tokens = count_tokens(_read_text_safe(repo_root / "CLAUDE.md"))
    project_skill_pointer_dir = repo_root / ".claude" / "skills"
    pointer_tokens = 0
    if project_skill_pointer_dir.is_dir():
        for pointer in project_skill_pointer_dir.glob("*.md"):
            pointer_tokens += count_tokens(_read_text_safe(pointer))
    mcp_block_tokens = 0
    notes.append(
        "system_prompt lane v1 does not include MCP instruction "
        "blocks from .mcp.json/settings; deferred to v2 per todo 014."
    )
    system_prompt = SystemPromptBreakdown(
        claude_md_tokens=claude_md_tokens,
        project_skill_pointer_tokens=pointer_tokens,
        mcp_block_tokens=mcp_block_tokens,
        total_tokens=(claude_md_tokens + pointer_tokens + mcp_block_tokens),
    )

    tokenizer, tokenizer_version = _detect_tokenizer()
    return ContextBudgetReport(
        schema_version="1",
        tokenizer=tokenizer,
        tokenizer_version=tokenizer_version,
        lanes=lanes,
        top_largest=top_largest,
        system_prompt=system_prompt,
        notes=tuple(notes),
    )


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validator entry point for the skill-loader path.

    Always returns `verdict: "pass"` — this first-landing validator
    reports numbers, not verdicts. Threshold-setting comes later.
    """
    payload = payload or {}
    registry_path = payload.get("registry_path")
    if isinstance(registry_path, str):
        registry_path = Path(registry_path)
    report = measure(registry_path=registry_path)
    report_dict = asdict(report, dict_factory=json_safe_factory)
    return {"verdict": "pass", "report": report_dict}
