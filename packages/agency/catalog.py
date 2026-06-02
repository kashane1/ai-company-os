"""Load + validate the agency service catalog (Agency layer, Phase 1).

Reads ``packages/agency/catalog.yaml`` into the typed
:class:`~packages.schemas.offer.ServiceCatalog`. The YAML is the editable source;
this module is the validated accessor every downstream consumer should use rather
than parsing the YAML ad hoc.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from packages.schemas.offer import ServiceCatalog

CATALOG_PATH = Path(__file__).resolve().parent / "catalog.yaml"


def load_catalog(path: Path | None = None) -> ServiceCatalog:
    """Load and validate the catalog from ``path`` (default: bundled YAML)."""
    catalog_path = path or CATALOG_PATH
    with catalog_path.open() as handle:
        payload = yaml.safe_load(handle) or {}
    catalog = ServiceCatalog.from_dict(payload)
    catalog.validate()
    return catalog


@lru_cache(maxsize=1)
def default_catalog() -> ServiceCatalog:
    """Cached load of the bundled catalog for read-only callers."""
    return load_catalog()
