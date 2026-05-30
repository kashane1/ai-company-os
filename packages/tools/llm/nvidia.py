"""NVIDIA NIM client — a thorough, extensible wrapper over NVIDIA's free,
OpenAI-compatible inference API (``https://integrate.api.nvidia.com/v1``).

Why this exists
---------------
The platform already has a deliberately tiny ``ChatModel`` seam
(``packages.tools.llm.client``) backed by OpenRouter. NVIDIA publishes 100+ open
models — reasoning, vision, embeddings, speech, image — behind the same
OpenAI-compatible shape, for free (with generous rate limits). This module makes
that catalogue a first-class provider so any agent or task can reach for it.

Design
------
* **Drop-in compatible.** ``NvidiaClient.complete(system, user)`` satisfies the
  existing :class:`~packages.tools.llm.client.ChatModel` protocol, so every
  current caller (e.g. the discovery analyst) can use NVIDIA by swapping the
  client — no call-site changes.
* **Richer when you need it.** ``chat()`` takes full message lists and returns a
  structured :class:`ChatResult` (text + ``reasoning_content`` + token usage +
  raw payload). ``chat_stream()`` yields tokens incrementally. ``embed()`` hits
  the OpenAI-compatible ``/embeddings`` endpoint.
* **Reasoning-model aware.** NVIDIA's Nemotron / Qwen-QwQ reasoning models accept
  ``chat_template_kwargs={"enable_thinking": ...}`` and ``reasoning_budget`` via
  ``extra_body``; ``chat()`` exposes those as plain keyword arguments and pulls
  the model's hidden chain-of-thought out of ``reasoning_content``.
* **Injectable transport.** Like ``OpenRouterClient``, it accepts an optional
  ``httpx.Client`` so tests drive it with ``httpx.MockTransport`` — no network,
  no key.
* **Fail loud, fail typed.** Reuses :class:`~packages.tools.llm.client.ModelError`
  so callers catch one exception type across providers.
* **Built to grow.** Image and audio (Riva/Parakeet) models live on sibling
  endpoints under the same host and key. The low-level ``_post()`` /
  ``request_json()`` helpers and the :data:`NVIDIA_MODELS` registry are the seams
  to layer those on later without touching chat code — see ``EXTENSION POINTS``
  at the bottom of this file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Sequence

import httpx

from packages.config.settings import NVIDIA_API_KEY_ENV_VAR, get_api_key
from packages.tools.llm.client import ModelError

__all__ = [
    "NvidiaClient",
    "ChatResult",
    "NVIDIA_API_BASE_URL",
    "NVIDIA_MODELS",
    "DEFAULT_CHAT_MODEL",
    "DEFAULT_REASONING_MODEL",
    "DEFAULT_EMBED_MODEL",
]

NVIDIA_API_BASE_URL = "https://integrate.api.nvidia.com/v1"

# A curated slice of NVIDIA's catalogue, grouped by capability. These are model
# *ids* you pass as the ``model=`` argument; the full live list is at
# https://build.nvidia.com/models. Treat this as a convenience registry, not an
# exhaustive or frozen list — any id the API accepts works.
NVIDIA_MODELS: dict[str, dict[str, str]] = {
    "chat": {
        # General-purpose instruct models.
        "llama-3.3-70b": "meta/llama-3.3-70b-instruct",
        "llama-3.1-8b": "meta/llama-3.1-8b-instruct",
        "nemotron-70b": "nvidia/llama-3.1-nemotron-70b-instruct",
        "qwen-2.5-7b": "qwen/qwen2.5-7b-instruct",
        "gpt-oss-120b": "openai/gpt-oss-120b",
        "deepseek-v3": "deepseek-ai/deepseek-v3",
    },
    "reasoning": {
        # Models that emit an explicit chain of thought via reasoning_content.
        "nemotron-nano-omni": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "qwq-32b": "qwen/qwq-32b-preview",
        "deepseek-r1": "deepseek-ai/deepseek-r1",
    },
    "vision": {
        # Multimodal (image-in, text-out) — pass image content blocks to chat().
        "llama-3.2-90b-vision": "meta/llama-3.2-90b-vision-instruct",
        "llava-16-34b": "community/llava-v1.6-34b",
    },
    "embed": {
        "nv-embedqa-e5": "nvidia/nv-embedqa-e5-v5",
        "nv-embed-v1": "nvidia/nv-embed-v1",
    },
}

DEFAULT_CHAT_MODEL = NVIDIA_MODELS["chat"]["llama-3.3-70b"]
DEFAULT_REASONING_MODEL = NVIDIA_MODELS["reasoning"]["nemotron-nano-omni"]
DEFAULT_EMBED_MODEL = NVIDIA_MODELS["embed"]["nv-embedqa-e5"]


@dataclass(frozen=True)
class ChatResult:
    """The useful pieces of one chat completion.

    ``content`` is the assistant's visible answer. ``reasoning_content`` is the
    hidden chain-of-thought some reasoning models return alongside it (``None``
    for non-reasoning models). ``raw`` is the full decoded JSON for callers that
    need a field this dataclass doesn't surface.
    """

    content: str
    reasoning_content: str | None = None
    model: str = ""
    finish_reason: str | None = None
    usage: Mapping[str, Any] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)


class NvidiaClient:
    """``ChatModel`` backed by NVIDIA's OpenAI-compatible inference API.

    Minimal use (satisfies the platform ``ChatModel`` protocol)::

        model = NvidiaClient()
        text = model.complete("You are terse.", "Say hi.")

    Reasoning model with visible chain-of-thought::

        model = NvidiaClient(model=DEFAULT_REASONING_MODEL)
        result = model.chat(
            [{"role": "user", "content": "9.11 or 9.9 — which is larger?"}],
            enable_thinking=True,
            reasoning_budget=4096,
        )
        print(result.reasoning_content)  # the model's scratch work
        print(result.content)            # the final answer
    """

    def __init__(
        self,
        *,
        model: str = DEFAULT_CHAT_MODEL,
        api_key: str | None = None,
        base_url: str = NVIDIA_API_BASE_URL,
        client: httpx.Client | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        # Explicit key wins; otherwise read from the environment (loads .env).
        self._api_key = api_key if api_key is not None else get_api_key(NVIDIA_API_KEY_ENV_VAR)
        # Reasoning models can think for a while, so the default timeout is
        # roomier than the chat client's 30s.
        self._client = client or httpx.Client(timeout=timeout)

    # ── ChatModel protocol ────────────────────────────────────────────────
    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        """Single-turn helper. Returns just the assistant text.

        This is the method the platform's ``ChatModel`` protocol requires, so an
        ``NvidiaClient`` is a drop-in replacement anywhere an ``OpenRouterClient``
        is used today.
        """
        result = self.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return result.content

    # ── Rich chat ─────────────────────────────────────────────────────────
    def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.0,
        top_p: float = 1.0,
        max_tokens: int | None = None,
        stop: Sequence[str] | None = None,
        enable_thinking: bool | None = None,
        reasoning_budget: int | None = None,
        extra_body: Mapping[str, Any] | None = None,
    ) -> ChatResult:
        """Full chat completion returning a structured :class:`ChatResult`.

        ``messages`` is a standard OpenAI-style list of ``{"role", "content"}``
        dicts (``content`` may be a string or a list of content blocks for
        vision models). Set ``enable_thinking`` / ``reasoning_budget`` for
        reasoning models to surface and bound their chain-of-thought.
        """
        payload = self._build_chat_payload(
            messages,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop,
            enable_thinking=enable_thinking,
            reasoning_budget=reasoning_budget,
            extra_body=extra_body,
            stream=False,
        )
        data = self.request_json("/chat/completions", payload)
        return _parse_chat_result(data)

    def chat_stream(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.0,
        top_p: float = 1.0,
        max_tokens: int | None = None,
        stop: Sequence[str] | None = None,
        enable_thinking: bool | None = None,
        reasoning_budget: int | None = None,
        extra_body: Mapping[str, Any] | None = None,
    ) -> Iterator[str]:
        """Stream the assistant's visible text token-by-token.

        Yields content deltas as they arrive (reasoning deltas are skipped — use
        :meth:`chat` if you need the full ``reasoning_content``). Network errors
        and non-200 statuses raise :class:`ModelError`, same as :meth:`chat`.
        """
        self._require_key()
        payload = self._build_chat_payload(
            messages,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop,
            enable_thinking=enable_thinking,
            reasoning_budget=reasoning_budget,
            extra_body=extra_body,
            stream=True,
        )
        try:
            with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = response.read().decode("utf-8", "replace")
                    raise ModelError(f"model HTTP {response.status_code}: {body[:200]}")
                yield from _iter_sse_content(response.iter_lines())
        except httpx.HTTPError as exc:  # pragma: no cover - network failure path
            raise ModelError(f"model request failed: {exc}") from exc

    # ── Embeddings ────────────────────────────────────────────────────────
    def embed(
        self,
        texts: str | Sequence[str],
        *,
        model: str = DEFAULT_EMBED_MODEL,
        input_type: str = "query",
        extra_body: Mapping[str, Any] | None = None,
    ) -> list[list[float]]:
        """Return embedding vectors for one or more strings.

        NVIDIA's retrieval embedders distinguish ``input_type`` ``"query"`` vs
        ``"passage"``; pass the right one for asymmetric search. Always returns a
        list of vectors, even for a single input string.
        """
        items = [texts] if isinstance(texts, str) else list(texts)
        payload: dict[str, Any] = {
            "model": model,
            "input": items,
            "input_type": input_type,
        }
        if extra_body:
            payload.update(extra_body)
        data = self.request_json("/embeddings", payload)
        try:
            rows = sorted(data["data"], key=lambda d: d.get("index", 0))
            return [list(row["embedding"]) for row in rows]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError(f"unexpected embeddings response shape: {exc}") from exc

    # ── Low-level seams (reuse for image/audio/other endpoints) ───────────
    def request_json(self, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """POST ``payload`` to ``{base_url}{path}`` and return decoded JSON.

        The single choke point every higher-level method funnels through. New
        capabilities (image generation, speech) are usually just a new ``path``
        and payload shape — call this rather than re-implementing auth, error
        handling, and decoding.
        """
        response = self._post(path, payload)
        if response.status_code != 200:
            raise ModelError(f"model HTTP {response.status_code}: {response.text[:200]}")
        try:
            return dict(response.json())
        except (ValueError, TypeError) as exc:
            raise ModelError(f"non-JSON model response: {exc}") from exc

    def _post(self, path: str, payload: Mapping[str, Any]) -> httpx.Response:
        self._require_key()
        try:
            return self._client.post(
                f"{self.base_url}{path}",
                headers=self._headers(),
                json=dict(payload),
            )
        except httpx.HTTPError as exc:  # pragma: no cover - network failure path
            raise ModelError(f"model request failed: {exc}") from exc

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _require_key(self) -> None:
        if not self._api_key:
            raise ModelError(
                f"no model API key — set ${NVIDIA_API_KEY_ENV_VAR} or pass api_key"
            )

    def _build_chat_payload(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        model: str | None,
        temperature: float,
        top_p: float,
        max_tokens: int | None,
        stop: Sequence[str] | None,
        enable_thinking: bool | None,
        reasoning_budget: int | None,
        extra_body: Mapping[str, Any] | None,
        stream: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": [dict(m) for m in messages],
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if stop:
            payload["stop"] = list(stop)

        # Reasoning controls travel in extra_body so non-reasoning models ignore
        # them. chat_template_kwargs.enable_thinking toggles the chain-of-thought;
        # reasoning_budget caps the thinking tokens.
        body: dict[str, Any] = dict(extra_body or {})
        if enable_thinking is not None:
            template_kwargs = dict(body.get("chat_template_kwargs", {}))
            template_kwargs["enable_thinking"] = enable_thinking
            body["chat_template_kwargs"] = template_kwargs
        if reasoning_budget is not None:
            body["reasoning_budget"] = reasoning_budget
        payload.update(body)
        return payload


# ── Module-level parsers (pure, unit-testable without a client) ───────────────
def _parse_chat_result(data: Mapping[str, Any]) -> ChatResult:
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ModelError(f"unexpected model response shape: {exc}") from exc
    content = message.get("content")
    if content is None:
        raise ModelError("model response missing message content")
    return ChatResult(
        content=str(content),
        reasoning_content=message.get("reasoning_content"),
        model=str(data.get("model", "")),
        finish_reason=(data["choices"][0] or {}).get("finish_reason"),
        usage=data.get("usage", {}) or {},
        raw=data,
    )


def _iter_sse_content(lines: Iterable[str]) -> Iterator[str]:
    """Yield ``content`` deltas from an OpenAI-style ``text/event-stream``.

    Each event is a ``data: {json}`` line; the stream terminates with
    ``data: [DONE]``. Malformed/keepalive lines are skipped rather than fatal.
    """
    for line in lines:
        line = line.strip()
        if not line or not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        try:
            event = json.loads(payload)
            delta = event["choices"][0]["delta"]
        except (ValueError, KeyError, IndexError, TypeError):
            continue
        piece = delta.get("content")
        if piece:
            yield str(piece)


# ── EXTENSION POINTS ─────────────────────────────────────────────────────────
# This client covers the OpenAI-compatible surface (chat, streaming, embeddings)
# that the bulk of NVIDIA's catalogue speaks. To grow it:
#
#   • Image generation / vision-to-image: NVIDIA's image models (e.g. SDXL,
#     Sana, Cosmos) live on sibling endpoints under the same host and key. Add a
#     ``generate_image(prompt, ...)`` method that builds the model-specific
#     payload and calls ``self.request_json("/...", payload)`` — auth, error
#     handling, and decoding are already done there. Mirror the Gemini image
#     integration in ``packages/tools/content_tools`` for how generated bytes are
#     persisted as artifacts.
#   • Audio / speech (Riva, Parakeet ASR, TTS): same pattern — a new method and
#     payload over ``request_json`` (or ``_post`` for non-JSON/binary replies).
#   • Vision chat is already supported today: pass OpenAI-style content blocks
#     (``[{"type": "text", ...}, {"type": "image_url", ...}]``) as a message's
#     ``content`` to a model from ``NVIDIA_MODELS["vision"]``.
#
# Keep new capabilities funnelling through ``request_json`` / ``_post`` so there
# is exactly one place that knows about the host, the bearer token, and failure
# typing.
