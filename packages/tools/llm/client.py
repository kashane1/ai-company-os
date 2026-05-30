"""Chat-model client: a narrow protocol + an OpenRouter implementation.

Design notes
------------
* **One method.** ``ChatModel.complete(system, user)`` returns the assistant's
  text. Anything richer (tools, streaming) is out of scope until something needs
  it — keeping the surface small keeps callers vendor-agnostic and tests trivial.
* **Injectable transport.** ``OpenRouterClient`` takes an optional
  ``httpx.Client`` so it can be driven by ``httpx.MockTransport`` in tests with
  no network and no API key.
* **Deterministic by default.** ``temperature`` defaults to ``0.0`` because the
  first caller (signal scoring) wants reproducible structured output, not prose.
* **Fail loud, fail typed.** Any non-200, missing key, or unexpected response
  shape raises :class:`ModelError` rather than returning a misleading empty
  string — callers can then decide to skip, retry, or surface the failure.

OpenRouter is used because it speaks the OpenAI-compatible ``/chat/completions``
shape and the platform already reserves ``OPENROUTER_API_KEY`` in settings; swap
``base_url``/``model`` for any compatible endpoint.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from packages.config.settings import OPENROUTER_API_KEY_ENV_VAR, get_api_key

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-sonnet-4"


class ModelError(RuntimeError):
    """Raised when a model call fails or returns an unusable response."""


class ChatModel(Protocol):
    """A single-turn chat model. Implementations return the assistant text."""

    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        ...


class OpenRouterClient:
    """``ChatModel`` backed by OpenRouter's OpenAI-compatible chat API."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        # Explicit key wins; otherwise read from the environment (loads .env).
        self._api_key = api_key if api_key is not None else get_api_key(OPENROUTER_API_KEY_ENV_VAR)
        self._client = client or httpx.Client(timeout=timeout)

    def complete(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        if not self._api_key:
            raise ModelError(
                f"no model API key — set ${OPENROUTER_API_KEY_ENV_VAR} or pass api_key"
            )
        response = self._client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        if response.status_code != 200:
            raise ModelError(f"model HTTP {response.status_code}: {response.text[:200]}")
        try:
            return str(response.json()["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelError(f"unexpected model response shape: {exc}") from exc
