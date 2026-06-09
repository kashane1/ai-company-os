"""Block generators — propose raw block designs to feed the tournament.

Two sources, one interface (``Generator`` = request -> raw designs):

* **Claude** (the in-pipeline baseline, GA): generates an original HTML section from
  a brief. Always available, clean terms.
* **Stitch** (the external idea-generator, experimental): calls Google Stitch's MCP
  API to generate a UI screen and returns its HTML + screenshot URL. Isolated behind
  an injected transport so the generator logic is testable and the experimental
  vendor never becomes load-bearing.

Both emit ``RawDesign`` (untokenized markup). The normalizer (`block_normalizer`)
turns each into a tokenized Astro block; the tournament judges them. So "external
widens, Claude normalizes, the judge admits" holds for both sources, and they
compete on equal footing.

Live Stitch access uses a minimal MCP-over-Streamable-HTTP client built on httpx
(the SDK is TypeScript; the wire protocol is JSON-RPC 2.0 `tools/call` with an
`X-Goog-Api-Key` header). No new dependency, and `StitchClient.call_tool` is the
seam the generator is tested against.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from packages.config.settings import STITCH_API_KEY_ENV_VAR, get_api_key
from packages.tools.llm.client import ChatModel

STITCH_MCP_URL = "https://stitch.googleapis.com/mcp"
STITCH_MODEL_FLASH = "GEMINI_3_FLASH"  # cheapest tier — used sparingly on a free key


@dataclass(frozen=True)
class GenerationRequest:
    slot: str
    archetype: str
    brief: str
    n: int = 1


@dataclass(frozen=True)
class RawDesign:
    source: str  # "claude" | "stitch"
    markup: str  # raw HTML (untokenized — the normalizer handles that)
    prompt: str
    screenshot_url: str = ""
    license: str = "generated"


# (request) -> raw designs
Generator = Callable[[GenerationRequest], list[RawDesign]]
# (tool_name, arguments) -> unwrapped MCP result dict
StitchCall = Callable[[str, dict], dict]


def _extract_block(text: str) -> str:
    import re

    match = re.search(r"```(?:html|astro)?\s*(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


# --------------------------------------------------------------------------- #
# Claude baseline generator
# --------------------------------------------------------------------------- #
_CLAUDE_SYSTEM = (
    "You are an Awwwards-caliber web designer. Produce ONE bold, original, art-directed "
    "HTML section for the requested slot of a premium small-business site. Return ONLY "
    "the HTML in a single ```html code block — no <html>/<head>, just the <section>. "
    "AVOID every generic AI tell: no purple/indigo aurora gradient, no three-icon "
    "feature grid, no centered-everything hero, no glassmorphism, no fake stat bar. "
    "Commit to a specific, confident layout idea."
)


def claude_generator(model: ChatModel, *, temperature: float = 0.9) -> Generator:
    """A baseline generator backed by the repo's ChatModel (Claude via OpenRouter)."""

    def generate(req: GenerationRequest) -> list[RawDesign]:
        out: list[RawDesign] = []
        for i in range(max(1, req.n)):
            user = (
                f"Slot: {req.slot}\nArchetype: {req.archetype}\nBrief: {req.brief}\n"
                f"This is variant #{i + 1} — make it structurally distinct from a "
                "generic template and from the other variants."
            )
            markup = _extract_block(model.complete(_CLAUDE_SYSTEM, user, temperature=temperature))
            out.append(RawDesign(source="claude", markup=markup, prompt=user))
        return out

    return generate


# --------------------------------------------------------------------------- #
# Stitch generator (external, experimental)
# --------------------------------------------------------------------------- #
def _resource_id(obj: dict, field: str = "name") -> str:
    """The bare id from a Stitch resource (its `name` is `projects/{id}` etc.).

    Verified against a live create_project response, whose id lives in `name`, not a
    top-level `projectId`. Falls back to explicit id fields if a future shape adds them.
    """

    name = obj.get(field, "")
    if name:
        return name.rsplit("/", 1)[-1]
    return obj.get("projectId") or obj.get("id", "")


def tool_error(result: dict) -> str | None:
    """The error message if an MCP tool result is a tool-level failure, else None.

    Stitch returns tool errors as ``{"content": [{"text": "..."}], "isError": true}``
    inside an otherwise-200 envelope — so a naive caller reads an error as success.
    """

    if not result.get("isError"):
        return None
    for item in result.get("content", []) or []:
        if isinstance(item, dict) and item.get("text"):
            return str(item["text"])
    return "unknown tool error"


def _first_screen_id(resp: dict) -> str:
    """Locate the generated screen id, scanning all output components.

    The live generate response nests screens under ``outputComponents[].design`` and
    can return several components; fail loudly (not KeyError) if none carries a screen.
    """

    for comp in resp.get("outputComponents", []) or []:
        screens = (comp.get("design") or {}).get("screens") or []
        for screen in screens:
            sid = screen.get("id") or _resource_id(screen)
            if sid:
                return sid
    raise StitchError("no screen id in generate response: " + json.dumps(resp)[:200])


def _html_from_file(file_obj: dict, fetch: Callable[[str], str] | None) -> str:
    """Resolve a Stitch File object to HTML text (inline base64, else downloadUrl)."""

    b64 = file_obj.get("fileContentBase64")
    if b64:
        return base64.b64decode(b64).decode("utf-8", errors="replace")
    url = file_obj.get("downloadUrl")
    if url and fetch:
        return fetch(url)
    return ""


def stitch_generator(
    call_tool: StitchCall,
    *,
    model_id: str = STITCH_MODEL_FLASH,
    fetch: Callable[[str], str] | None = None,
) -> Generator:
    """A generator backed by Google Stitch's MCP API.

    ``call_tool`` performs one MCP ``tools/call`` and returns the unwrapped result
    dict — injected so this is unit-tested with a fake and the live client
    (`StitchClient`) is the only thing that touches the network/key.
    """

    def generate(req: GenerationRequest) -> list[RawDesign]:
        out: list[RawDesign] = []
        for i in range(max(1, req.n)):
            project = call_tool("create_project", {"title": f"{req.slot}-{req.archetype}-{i}"})
            project_id = _resource_id(project)
            prompt = (
                f"A website {req.slot} section for a premium small business. "
                f"{req.brief}. Visual direction: {req.archetype}."
            )
            screen = call_tool(
                "generate_screen_from_text",
                {
                    "projectId": project_id,
                    "prompt": prompt,
                    "deviceType": "DESKTOP",
                    "modelId": model_id,
                },
            )
            screen_id = _first_screen_id(screen)
            got = call_tool(
                "get_screen",
                {
                    "name": f"projects/{project_id}/screens/{screen_id}",
                    "projectId": project_id,
                    "screenId": screen_id,
                },
            )
            markup = _html_from_file(got.get("htmlCode", {}), fetch)
            shot = got.get("screenshot", {}).get("downloadUrl", "")
            out.append(
                RawDesign(source="stitch", markup=markup, prompt=prompt, screenshot_url=shot)
            )
        return out

    return generate


class StitchError(RuntimeError):
    """A Stitch MCP call failed (auth, quota, or protocol)."""


class StitchClient:
    """A minimal MCP-over-Streamable-HTTP client for the Stitch API.

    Implements just enough of MCP to call tools: an ``initialize`` handshake (carrying
    the ``Mcp-Session-Id`` it returns), then ``tools/call``. Replies may be JSON or an
    SSE stream — both are parsed. Auth is the ``X-Goog-Api-Key`` header (NOT Bearer).
    Built on httpx (already a dependency); no Node, no `mcp` package.
    """

    PROTOCOL_VERSION = "2025-06-18"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        url: str = STITCH_MCP_URL,
        client: httpx.Client | None = None,
        timeout: float = 300.0,
    ) -> None:
        self.url = url
        self._key = api_key if api_key is not None else get_api_key(STITCH_API_KEY_ENV_VAR)
        self._client = client or httpx.Client(timeout=timeout)
        self._session_id: str | None = None
        self._next_id = 0
        self._initialized = False

    def _headers(self) -> dict[str, str]:
        if not self._key:
            raise StitchError(f"missing {STITCH_API_KEY_ENV_VAR}")
        h = {
            "X-Goog-Api-Key": self._key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            h["Mcp-Session-Id"] = self._session_id
        return h

    def _rpc(self, method: str, params: dict | None, *, notify: bool = False) -> dict | None:
        body: dict = {"jsonrpc": "2.0", "method": method}
        if not notify:
            self._next_id += 1
            body["id"] = self._next_id
        if params is not None:
            body["params"] = params
        resp = self._client.post(self.url, headers=self._headers(), json=body)
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self._session_id = sid
        if resp.status_code not in (200, 202):
            raise StitchError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        if notify or resp.status_code == 202 or not resp.content:
            return None
        return _parse_jsonrpc(resp)

    def initialize(self) -> None:
        self._rpc(
            "initialize",
            {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "ai-company-os/block-studio", "version": "0.1"},
            },
        )
        self._rpc("notifications/initialized", None, notify=True)

    def call_tool(self, name: str, arguments: dict) -> dict:
        if not self._initialized:
            self.initialize()
            self._initialized = True
        result = self._rpc("tools/call", {"name": name, "arguments": arguments}) or {}
        err = tool_error(result)
        if err:
            raise StitchError(f"tool {name}: {err}")
        return _unwrap_tool_result(result)


def _parse_jsonrpc(resp: httpx.Response) -> dict:
    """Parse a JSON-RPC reply that may be plain JSON or an SSE stream."""

    ctype = resp.headers.get("content-type", "")
    if "text/event-stream" in ctype:
        payload = None
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                payload = json.loads(line[5:].strip())
        if payload is None:
            raise StitchError("empty SSE stream from Stitch")
    else:
        payload = resp.json()
    if "error" in payload:
        raise StitchError(f"JSON-RPC error: {payload['error']}")
    return payload.get("result", {})


def _unwrap_tool_result(result: dict) -> dict:
    """Pull the tool's structured payload out of the MCP result envelope.

    The server may put it in ``structuredContent`` or as a JSON string inside
    ``content[].text``; handle both (the exact field isn't pinned in the SDK source).
    """

    if isinstance(result.get("structuredContent"), dict):
        return result["structuredContent"]
    for item in result.get("content", []) or []:
        text = item.get("text") if isinstance(item, dict) else None
        if text:
            try:
                return json.loads(text)
            except (json.JSONDecodeError, ValueError):
                continue
    return result
