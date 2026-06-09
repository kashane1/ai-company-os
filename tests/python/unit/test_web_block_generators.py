"""Tests for the block generators (Claude baseline + Stitch).

The model and the Stitch transport are injected, so these run with no key/network.
They lock the request→RawDesign contract and the Stitch create→generate→get_screen
flow (including base64 and downloadUrl HTML resolution).
"""

from __future__ import annotations

import base64

import pytest

from packages.web.block_generators import (
    GenerationRequest,
    StitchError,
    _first_screen_id,
    _unwrap_tool_result,
    claude_generator,
    stitch_generator,
    tool_error,
)


class FakeModel:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls: list[tuple[str, str, float]] = []

    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        self.calls.append((system, user, temperature))
        return self._replies.pop(0)


# --------------------------------------------------------------------------- #
# Claude baseline
# --------------------------------------------------------------------------- #
def test_claude_generator_emits_one_rawdesign_per_variant() -> None:
    model = FakeModel(["```html\n<section>A</section>```", "```html\n<section>B</section>```"])
    gen = claude_generator(model)
    out = gen(GenerationRequest(slot="hero", archetype="gallery-led", brief="show artistry", n=2))
    assert [d.markup for d in out] == ["<section>A</section>", "<section>B</section>"]
    assert all(d.source == "claude" for d in out)
    # high temperature for diversity, and the brief reached the model
    assert model.calls[0][2] == 0.9
    assert "show artistry" in model.calls[0][1]


# --------------------------------------------------------------------------- #
# Stitch — the create → generate → get_screen flow
# --------------------------------------------------------------------------- #
def _stitch_calls(html_file: dict):
    seen = []

    def call_tool(name: str, arguments: dict) -> dict:
        seen.append((name, arguments))
        if name == "create_project":
            return {"projectId": "P123"}
        if name == "generate_screen_from_text":
            return {"outputComponents": [{"design": {"screens": [{"id": "S456"}]}}]}
        if name == "get_screen":
            return {"htmlCode": html_file, "screenshot": {"downloadUrl": "https://shot.png"}}
        raise AssertionError(name)

    return call_tool, seen


def test_stitch_generator_resolves_base64_html() -> None:
    html = "<section>stitch hero</section>"
    file_obj = {"fileContentBase64": base64.b64encode(html.encode()).decode()}
    call_tool, seen = _stitch_calls(file_obj)
    gen = stitch_generator(call_tool)
    out = gen(GenerationRequest(slot="hero", archetype="product-led", brief="bold"))
    assert len(out) == 1
    assert out[0].source == "stitch"
    assert out[0].markup == html
    assert out[0].screenshot_url == "https://shot.png"
    # the flow hit all three tools, with the screen name assembled from ids
    assert [c[0] for c in seen] == ["create_project", "generate_screen_from_text", "get_screen"]
    assert seen[2][1]["name"] == "projects/P123/screens/S456"


def test_stitch_generator_resolves_downloadurl_html_via_fetch() -> None:
    file_obj = {"downloadUrl": "https://stitch/html"}
    call_tool, _ = _stitch_calls(file_obj)
    gen = stitch_generator(call_tool, fetch=lambda url: f"<section>from {url}</section>")
    out = gen(GenerationRequest(slot="hero", archetype="x", brief="y"))
    assert out[0].markup == "<section>from https://stitch/html</section>"


# --------------------------------------------------------------------------- #
# MCP envelope unwrapping
# --------------------------------------------------------------------------- #
def test_unwrap_prefers_structured_content() -> None:
    assert _unwrap_tool_result({"structuredContent": {"projectId": "X"}}) == {"projectId": "X"}


def test_unwrap_falls_back_to_json_in_content_text() -> None:
    env = {"content": [{"type": "text", "text": '{"projectId": "Y"}'}]}
    assert _unwrap_tool_result(env) == {"projectId": "Y"}


# --------------------------------------------------------------------------- #
# tool-level error detection (Stitch returns errors inside a 200 envelope)
# --------------------------------------------------------------------------- #
def test_tool_error_detects_iserror_envelope() -> None:
    # verified against the live API: errors arrive as content+isError, not JSON-RPC error
    env = {"content": [{"type": "text", "text": "Request contains an invalid argument."}], "isError": True}
    assert tool_error(env) == "Request contains an invalid argument."
    assert tool_error({"structuredContent": {"ok": 1}}) is None


def test_first_screen_id_scans_components_and_fails_loudly() -> None:
    ok = {"outputComponents": [{"designSystem": {}}, {"design": {"screens": [{"id": "S9"}]}}]}
    assert _first_screen_id(ok) == "S9"
    with pytest.raises(StitchError):
        _first_screen_id({"outputComponents": [{"designSystem": {}}]})
