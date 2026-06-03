#!/usr/bin/env python3
"""Regenerate ``docs/agency/service-catalog.md`` from ``packages/agency/catalog.yaml``.

The mirror is a generated render — never hand-edit prices. Run this after editing
the catalog; the drift test
(``tests/python/unit/test_agency_service_catalog_render.py``) fails if the
committed file and this output diverge.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.catalog import load_catalog  # noqa: E402
from packages.agency.templates import render_service_catalog  # noqa: E402

MIRROR = REPO / "docs" / "agency" / "service-catalog.md"


def main() -> None:
    catalog = load_catalog()
    catalog.validate()
    MIRROR.write_text(render_service_catalog(catalog), encoding="utf-8")
    print(f"wrote {MIRROR}")


if __name__ == "__main__":
    main()
