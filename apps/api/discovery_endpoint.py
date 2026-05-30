"""Discovery dashboard endpoint — the operator dashboard's first panel (D3).

A tiny FastAPI ``APIRouter`` that serves the read-only discovery view:

- ``GET /discovery`` — the HTML panel (ranked inbox + run status), self-contained.
- ``GET /discovery/data`` — the same view as JSON, for tooling.

The heavy lifting (reading the stores, ranking, rendering) lives in
``packages.discovery.dashboard``; this module only wires the control-plane stores
in as the default repositories and adapts the result to HTTP responses. It does
*not* import the control-plane service, so it stays free of that module's
heavier dependencies — the discovery view is independently mountable.

Like the rest of the API, this is meant to run on ``127.0.0.1`` on Kashane's Mac.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from packages.db.discovery_run_store import DiscoveryRunRecordStore
from packages.db.opportunity_store import OpportunityStore
from packages.discovery.dashboard import build_dashboard, render_html

router = APIRouter()


def _view():
    """Build the dashboard view from the control-plane stores.

    Stores are constructed per request (cheap — they hold no connection) so the
    panel always reflects the latest committed state.
    """
    return build_dashboard(OpportunityStore(), DiscoveryRunRecordStore())


@router.get("/discovery", response_class=HTMLResponse)
def discovery_panel() -> HTMLResponse:
    return HTMLResponse(content=render_html(_view()))


@router.get("/discovery/data")
def discovery_data() -> dict[str, object]:
    return _view().to_dict()
