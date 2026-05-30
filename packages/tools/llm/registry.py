"""Chat-model registry — the one place agents and tasks ask for "a model".

The platform's seam is the :class:`~packages.tools.llm.client.ChatModel`
protocol: a caller depends on ``complete(system, user)``, not on a vendor. This
module is the *connector* for that seam — a small factory so any worker, agent,
or task can obtain a configured provider by name without importing a specific
client or knowing its constructor::

    from packages.tools.llm import build_chat_model

    model = build_chat_model("nvidia")           # NVIDIA NIM, default model
    model = build_chat_model("nvidia:reasoning") # NVIDIA reasoning model
    model = build_chat_model()                   # platform default provider

That keeps provider choice a single string (configurable, swappable) instead of
a hard-coded import scattered across call sites. New providers register their
factory in :data:`CHAT_MODEL_FACTORIES` and become available everywhere.
"""

from __future__ import annotations

import os
from typing import Callable

from packages.tools.llm.client import ChatModel, ModelError, OpenRouterClient
from packages.tools.llm.nvidia import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_REASONING_MODEL,
    NvidiaClient,
)

__all__ = [
    "build_chat_model",
    "default_chat_model",
    "available_providers",
    "CHAT_MODEL_FACTORIES",
    "CHAT_MODEL_PROVIDER_ENV_VAR",
    "DEFAULT_PROVIDER",
]

# Set CHAT_MODEL_PROVIDER in the env to change what build_chat_model() returns by
# default, so deployments can switch providers without code edits.
CHAT_MODEL_PROVIDER_ENV_VAR = "CHAT_MODEL_PROVIDER"
DEFAULT_PROVIDER = "openrouter"

# A factory takes an optional model-id override and returns a ChatModel. Keep
# construction lazy: don't read API keys here — the client checks for its key at
# call time, so building a model without a key configured is harmless.
ChatModelFactory = Callable[[str | None], ChatModel]


def _build_openrouter(model: str | None) -> ChatModel:
    return OpenRouterClient(model=model) if model else OpenRouterClient()


def _build_nvidia(model: str | None) -> ChatModel:
    return NvidiaClient(model=model or DEFAULT_CHAT_MODEL)


def _build_nvidia_reasoning(model: str | None) -> ChatModel:
    return NvidiaClient(model=model or DEFAULT_REASONING_MODEL)


CHAT_MODEL_FACTORIES: dict[str, ChatModelFactory] = {
    "openrouter": _build_openrouter,
    "nvidia": _build_nvidia,
    "nvidia:reasoning": _build_nvidia_reasoning,
}


def available_providers() -> list[str]:
    """Provider names accepted by :func:`build_chat_model`."""
    return sorted(CHAT_MODEL_FACTORIES)


def build_chat_model(provider: str | None = None, *, model: str | None = None) -> ChatModel:
    """Return a configured :class:`ChatModel` for ``provider``.

    ``provider`` is a key of :data:`CHAT_MODEL_FACTORIES` (e.g. ``"nvidia"`` or
    ``"nvidia:reasoning"``). When omitted it falls back to the
    ``CHAT_MODEL_PROVIDER`` env var, then :data:`DEFAULT_PROVIDER`. Pass ``model``
    to override the provider's default model id. Raises :class:`ModelError` for
    an unknown provider.
    """
    name = provider or os.environ.get(CHAT_MODEL_PROVIDER_ENV_VAR) or DEFAULT_PROVIDER
    factory = CHAT_MODEL_FACTORIES.get(name)
    if factory is None:
        raise ModelError(
            f"unknown chat-model provider {name!r}; available: {', '.join(available_providers())}"
        )
    return factory(model)


def default_chat_model() -> ChatModel:
    """The platform's default chat model (honours ``CHAT_MODEL_PROVIDER``)."""
    return build_chat_model()
