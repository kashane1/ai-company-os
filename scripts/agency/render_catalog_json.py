#!/usr/bin/env python3
"""Emit the BBW Astro site's ``src/data/packages.json`` from the catalog.

The Astro Packages section reads this file at build time, so bundle prices come
from ``packages/agency/catalog.yaml`` (the source of truth) and never drift. Run
after editing the catalog; the drift test
(``tests/python/unit/test_agency_catalog_json.py``) fails if the committed file
and this output diverge.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.catalog import load_catalog  # noqa: E402
from packages.agency.templates import render_catalog_json  # noqa: E402

OUT = REPO / "products" / "better-business-web" / "site" / "src" / "data" / "packages.json"


def render() -> str:
    catalog = load_catalog()
    catalog.validate()
    return json.dumps(render_catalog_json(catalog), indent=2) + "\n"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
