from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from packages.dashboard.operator import build_operator_dashboard, render_html
from packages.queue import active_queue_backend_name

router = APIRouter()


def _view():
    return build_operator_dashboard(queue_backend=active_queue_backend_name())


@router.get("/dashboard", response_class=HTMLResponse)
def operator_dashboard() -> HTMLResponse:
    return HTMLResponse(content=render_html(_view()))


@router.get("/dashboard/data")
def operator_dashboard_data() -> dict[str, object]:
    return _view().to_dict()
