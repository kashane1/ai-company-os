"""Outreach action panel endpoint (operator-local, loopback only).

Serves the interactive panel and the three write actions: log a manual send
(touch), edit a contact field (override), set deal status. Every write is
human-initiated from the local UI; none of them send a message.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from packages.agency import outreach_actions as actions
from packages.dashboard.outreach_panel import render_outreach_html

router = APIRouter()


class TouchRequest(BaseModel):
    place_id: str
    channel: str


class ContactRequest(BaseModel):
    place_id: str
    field: str
    value: str = ""


class StatusRequest(BaseModel):
    place_id: str
    status: str


@router.get("/dashboard/outreach", response_class=HTMLResponse)
def outreach_panel() -> HTMLResponse:
    return HTMLResponse(content=render_outreach_html(actions.build_outreach_panel()))


@router.get("/dashboard/outreach/data")
def outreach_panel_data() -> dict[str, object]:
    return actions.build_outreach_panel().to_dict()


@router.post("/dashboard/outreach/touch")
def log_touch(request: TouchRequest) -> dict[str, object]:
    try:
        return actions.record_touch(request.place_id, request.channel)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/dashboard/outreach/contact")
def save_contact(request: ContactRequest) -> dict[str, object]:
    try:
        return actions.set_contact(request.place_id, request.field, request.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/dashboard/outreach/status")
def save_status(request: StatusRequest) -> dict[str, object]:
    try:
        return actions.set_status(request.place_id, request.status)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


__all__ = ["router"]
