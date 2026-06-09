"""Tests for the Figma token mapping (brand source-of-truth).

The network client is not exercised here — these lock the pure mapping (Figma
variables -> flat token dict -> CSS) and the hand-authored tokens.json fallback,
so the premium brand-lock works whether or not the Variables REST API is reachable.
"""

from __future__ import annotations

import json

from packages.web.figma_tokens import (
    load_manual_tokens,
    rgba_to_hex,
    tokens_to_css,
    variables_to_tokens,
    write_tokens,
)

# A realistic /variables/local payload (the shape Figma returns).
PAYLOAD = {
    "meta": {
        "variables": {
            "VariableID:1": {
                "name": "color/canvas",
                "resolvedType": "COLOR",
                "valuesByMode": {"1:0": {"r": 0.06, "g": 0.06, "b": 0.07, "a": 1}},
            },
            "VariableID:2": {
                "name": "color/accent",
                "resolvedType": "COLOR",
                "valuesByMode": {"1:0": {"r": 1, "g": 0.31, "b": 0.13, "a": 1}},
            },
            "VariableID:3": {
                "name": "space/unit",
                "resolvedType": "FLOAT",
                "valuesByMode": {"1:0": 8},
            },
            "VariableID:4": {
                "name": "display/font",
                "resolvedType": "STRING",
                "valuesByMode": {"1:0": "Fraunces"},
            },
        }
    }
}


def test_rgba_to_hex() -> None:
    assert rgba_to_hex({"r": 1, "g": 0, "b": 0, "a": 1}) == "#ff0000"
    assert rgba_to_hex({"r": 0, "g": 0, "b": 0, "a": 0.5}) == "#00000080"


def test_variables_to_tokens_maps_each_type() -> None:
    tokens = variables_to_tokens(PAYLOAD)
    assert tokens["--color-canvas"] == "#0f0f12"
    assert tokens["--color-accent"] == "#ff4f21"
    assert tokens["--space-unit"] == "8px"  # size/space floats -> px
    assert tokens["--display-font"] == "Fraunces"


def test_tokens_to_css_emits_root_override() -> None:
    css = tokens_to_css({"--color-canvas": "#0f0f12", "--color-accent": "#ff4f21"})
    assert ":root {" in css
    assert "--color-accent: #ff4f21;" in css
    # sorted + closed
    assert css.index("--color-accent") < css.index("--color-canvas")
    assert css.rstrip().endswith("}")


def test_manual_tokens_fallback_adds_prefix(tmp_path) -> None:
    path = tmp_path / "tokens.json"
    path.write_text(json.dumps({"color-canvas": "#101014", "--color-accent": "#e0512f"}))
    tokens = load_manual_tokens(path)
    assert tokens["--color-canvas"] == "#101014"
    assert tokens["--color-accent"] == "#e0512f"  # already-prefixed left as-is


def test_write_tokens_emits_json_and_css(tmp_path) -> None:
    json_path, css_path = write_tokens({"--color-canvas": "#0f0f12"}, tmp_path / "brand")
    assert json_path.exists() and css_path.exists()
    assert json.loads(json_path.read_text())["--color-canvas"] == "#0f0f12"
    assert "--color-canvas: #0f0f12;" in css_path.read_text()
