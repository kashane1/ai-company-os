"""Figma tokens — brand source-of-truth for premium, brand-locked builds.

A premium build can lock its palette/type to a brand's Figma file instead of the
synthesized defaults. Figma exposes design tokens via the REST Variables API
(``/v1/files/{key}/variables/local``) — but that endpoint is **Enterprise-gated**,
so this module is built to degrade: it reads variables when the plan allows, and
otherwise loads a hand-authored ``tokens.json`` (the documented free-tier fallback).
Either way it emits a ``tokens.css`` ``:root`` override that layers over
``design-system.css``.

The mapping (Figma variables → flat token dict → CSS) is pure and tested; only
``FigmaClient`` touches the network/key (header ``X-Figma-Token``, NOT Bearer).
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from packages.config.settings import FIGMA_API_KEY_ENV_VAR, get_api_key

FIGMA_API = "https://api.figma.com/v1"


class FigmaError(RuntimeError):
    """A Figma REST call failed (auth, plan gate, or not found)."""


class FigmaClient:
    """Minimal Figma REST client (token read + auth check)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._key = api_key if api_key is not None else get_api_key(FIGMA_API_KEY_ENV_VAR)
        self._client = client or httpx.Client(timeout=timeout)

    def _get(self, path: str) -> dict:
        if not self._key:
            raise FigmaError(f"missing {FIGMA_API_KEY_ENV_VAR}")
        resp = self._client.get(f"{FIGMA_API}{path}", headers={"X-Figma-Token": self._key})
        if resp.status_code == 403:
            raise FigmaError(
                f"403 from {path} — the Variables REST API is Enterprise-gated; "
                "use a hand-authored tokens.json fallback instead"
            )
        if resp.status_code != 200:
            raise FigmaError(f"HTTP {resp.status_code} from {path}: {resp.text[:200]}")
        return resp.json()

    def me(self) -> dict:
        """The authenticated user — a cheap way to prove the key works."""

        return self._get("/me")

    def local_variables(self, file_key: str) -> dict:
        """Raw ``variables/local`` payload for a file (Enterprise-gated)."""

        return self._get(f"/files/{file_key}/variables/local")


# --------------------------------------------------------------------------- #
# Pure mapping: Figma variables -> flat token dict -> CSS
# --------------------------------------------------------------------------- #
def rgba_to_hex(value: dict) -> str:
    """Figma color ({r,g,b,a} in 0..1) -> #rrggbb or #rrggbbaa."""

    def ch(x: float) -> int:
        return max(0, min(255, round(float(x) * 255)))

    r, g, b = ch(value.get("r", 0)), ch(value.get("g", 0)), ch(value.get("b", 0))
    a = value.get("a", 1)
    hexs = f"#{r:02x}{g:02x}{b:02x}"
    return hexs if a in (1, 1.0, None) else f"{hexs}{ch(a):02x}"


def _token_name(figma_name: str) -> str:
    """`color/canvas/base` -> `--color-canvas-base` (CSS custom property)."""

    cleaned = figma_name.strip().lower().replace(" ", "-").replace("/", "-")
    return f"--{cleaned}"


def variables_to_tokens(payload: dict) -> dict[str, str]:
    """Flatten a ``variables/local`` payload to a {css-var-name: value} dict.

    Takes each variable's first mode value. Colors -> hex, floats -> px (for sizes)
    or bare number, strings -> the string. Unknown types are skipped.
    """

    meta = payload.get("meta", payload)
    variables = meta.get("variables", {})
    tokens: dict[str, str] = {}
    for var in variables.values():
        name = _token_name(var.get("name", ""))
        if not name or name == "--":
            continue
        values = var.get("valuesByMode") or {}
        if not values:
            continue
        value = next(iter(values.values()))
        rtype = var.get("resolvedType")
        if rtype == "COLOR" and isinstance(value, dict):
            tokens[name] = rgba_to_hex(value)
        elif rtype == "FLOAT":
            num = float(value)
            tokens[name] = f"{num:g}px" if "size" in name or "space" in name else f"{num:g}"
        elif rtype == "STRING":
            tokens[name] = str(value)
    return tokens


def tokens_to_css(tokens: dict[str, str]) -> str:
    """A ``:root`` override block layered over design-system.css."""

    lines = ["/* Brand tokens from Figma — overrides design-system.css. */", ":root {"]
    lines += [f"  {name}: {value};" for name, value in sorted(tokens.items())]
    lines.append("}")
    return "\n".join(lines) + "\n"


def load_manual_tokens(path: Path) -> dict[str, str]:
    """Load a hand-authored ``tokens.json`` ({name: value}) — the free-tier fallback.

    Names may omit the leading ``--`` (it's added); values are used verbatim.
    """

    raw = json.loads(Path(path).read_text())
    return {(k if k.startswith("--") else _token_name(k)): str(v) for k, v in raw.items()}


def write_tokens(tokens: dict[str, str], out_dir: Path) -> tuple[Path, Path]:
    """Persist tokens.json + tokens.css; return their paths."""

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "tokens.json"
    css_path = out_dir / "tokens.css"
    json_path.write_text(json.dumps(tokens, indent=2) + "\n")
    css_path.write_text(tokens_to_css(tokens))
    return json_path, css_path
