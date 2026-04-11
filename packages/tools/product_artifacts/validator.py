"""Phase 5.1 — Product Artifact Chain validator.

Walks ``docs/products/<product_id>/`` against the chain declared in
``chain.yaml`` and produces a structured report. Called from the
`product-artifact-chain` adapter skill and from
``SupervisorSession.close()`` when a product was touched during the
session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


CHAIN_PATH = Path(__file__).parent / "chain.yaml"


@dataclass(frozen=True)
class ChainNode:
    id: str
    file: str
    required_from: str
    parents: tuple[str, ...]


@dataclass(frozen=True)
class ChainViolation:
    node_id: str
    code: str
    detail: str


@dataclass(frozen=True)
class ChainReport:
    product_id: str
    phase: str
    present_nodes: tuple[str, ...]
    missing_nodes: tuple[str, ...]
    violations: tuple[ChainViolation, ...]

    @property
    def ok(self) -> bool:
        return not self.violations


def _load_chain() -> tuple[list[ChainNode], list[str]]:
    raw = CHAIN_PATH.read_text()
    if yaml is None:
        return _tiny_parse(raw)
    data = yaml.safe_load(raw) or {}
    nodes = [
        ChainNode(
            id=n["id"],
            file=n["file"],
            required_from=n.get("required_from", "discovery"),
            parents=tuple(n.get("parents", []) or []),
        )
        for n in data.get("nodes", [])
    ]
    phase_order = list(data.get("phase_order", []))
    return nodes, phase_order


def _tiny_parse(raw: str) -> tuple[list[ChainNode], list[str]]:
    nodes: list[ChainNode] = []
    phase_order: list[str] = []
    in_nodes = False
    in_phase_order = False
    cur: dict[str, Any] | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("nodes:"):
            in_nodes = True
            in_phase_order = False
            continue
        if line.startswith("phase_order:"):
            if cur is not None:
                nodes.append(_mk_node(cur))
                cur = None
            in_nodes = False
            in_phase_order = True
            continue
        if in_nodes:
            if line.startswith("  - "):
                if cur is not None:
                    nodes.append(_mk_node(cur))
                cur = {}
                k, _, v = stripped[2:].partition(":")
                if v.strip():
                    cur[k.strip()] = v.strip()
            elif line.startswith("    "):
                k, _, v = stripped.partition(":")
                v = v.strip()
                if v.startswith("[") and v.endswith("]"):
                    inner = v[1:-1].strip()
                    cur[k.strip()] = [s.strip() for s in inner.split(",") if s.strip()] if inner else []  # type: ignore[union-attr]
                else:
                    cur[k.strip()] = v  # type: ignore[union-attr]
        elif in_phase_order:
            if line.startswith("  - "):
                phase_order.append(stripped[2:].strip())
    if cur is not None:
        nodes.append(_mk_node(cur))
    return nodes, phase_order


def _mk_node(d: dict[str, Any]) -> ChainNode:
    parents = d.get("parents", [])
    if isinstance(parents, str):
        parents = []
    return ChainNode(
        id=d["id"],
        file=d["file"],
        required_from=d.get("required_from", "discovery"),
        parents=tuple(parents),
    )


def _phase_at_least(current: str, required: str, phase_order: list[str]) -> bool:
    try:
        return phase_order.index(current) >= phase_order.index(required)
    except ValueError:
        return True  # unknown phase: fail open on ordering, let presence check decide


def validate_chain(
    *,
    product_id: str,
    product_dir: Path,
    phase: str = "app-store-submission",
) -> ChainReport:
    nodes, phase_order = _load_chain()
    present: list[str] = []
    missing: list[str] = []
    violations: list[ChainViolation] = []
    texts: dict[str, str] = {}

    for node in nodes:
        fp = product_dir / node.file
        if not fp.exists():
            if _phase_at_least(phase, node.required_from, phase_order):
                missing.append(node.id)
                violations.append(
                    ChainViolation(
                        node.id,
                        "missing_required_node",
                        f"{node.file} not found (required from phase={node.required_from})",
                    )
                )
            continue
        present.append(node.id)
        try:
            texts[node.id] = fp.read_text(errors="replace")
        except OSError as exc:
            violations.append(
                ChainViolation(node.id, "unreadable", f"{fp}: {exc}")
            )

    for node in nodes:
        if node.id not in present or not node.parents:
            continue
        body = texts.get(node.id, "").lower()
        for parent in node.parents:
            parent_node = next((n for n in nodes if n.id == parent), None)
            if parent_node is None:
                continue
            # Accept either the parent's id or its filename as a reference.
            mentions = parent in body or parent_node.file.lower() in body
            if not mentions:
                violations.append(
                    ChainViolation(
                        node.id,
                        "parent_reference_missing",
                        f"{node.file} does not reference parent {parent_node.file}",
                    )
                )

    return ChainReport(
        product_id=product_id,
        phase=phase,
        present_nodes=tuple(present),
        missing_nodes=tuple(missing),
        violations=tuple(violations),
    )
