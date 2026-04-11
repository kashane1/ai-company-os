"""Phase 5.3 — derived product projections.

The runtime-supervisor's ``build_work_summary`` writes a per-product
projection to ``state/checkpoints/platform/products/<id>.projection.json``
on every sweep. The projection is read-only: the source of truth for
static product metadata is ``infra/products.json``, and the phase field
is the only dynamic value the platform authors.
"""

from __future__ import annotations

import json
from pathlib import Path

from packages.schemas.product import ProductConfig


def projection_path(state_root: Path, product_id: str) -> Path:
    return state_root / "checkpoints" / "platform" / "products" / f"{product_id}.projection.json"


def write_projection(
    *,
    state_root: Path,
    config: ProductConfig,
    open_tasks: int = 0,
    last_touched_at: str = "",
    blockers: list[str] | None = None,
) -> Path:
    path = projection_path(state_root, config.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "id": config.id,
        "name": config.name,
        "slug": config.slug,
        "phase": config.phase.value,
        "docs_root": config.docs_root,
        "open_tasks": open_tasks,
        "last_touched_at": last_touched_at,
        "blockers": list(blockers or []),
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(body, indent=2, sort_keys=True))
    tmp.replace(path)
    return path
