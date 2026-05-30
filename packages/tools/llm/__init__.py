"""Minimal chat-model client primitive.

The platform is agent-driven and historically had no in-process model client —
agents (Claude Code / Codex) supplied judgement and the platform supplied typed
I/O. Some steps, though, want a *programmatic* model call from inside the
platform (the discovery analyst scoring twelve signals is the first). This package
is that seam: a narrow ``ChatModel`` protocol plus one OpenRouter-backed
implementation. It is deliberately tiny — one ``complete()`` call — so callers
depend on the interface, not a vendor, and tests inject a stub.
"""

from packages.tools.llm.client import (
    ChatModel,
    ModelError,
    OpenRouterClient,
)
from packages.tools.llm.nvidia import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBED_MODEL,
    DEFAULT_REASONING_MODEL,
    NVIDIA_MODELS,
    ChatResult,
    NvidiaClient,
)
from packages.tools.llm.registry import (
    CHAT_MODEL_FACTORIES,
    available_providers,
    build_chat_model,
    default_chat_model,
)

__all__ = [
    # Protocol + shared error
    "ChatModel",
    "ModelError",
    # Providers
    "OpenRouterClient",
    "NvidiaClient",
    "ChatResult",
    # NVIDIA model registry
    "NVIDIA_MODELS",
    "DEFAULT_CHAT_MODEL",
    "DEFAULT_REASONING_MODEL",
    "DEFAULT_EMBED_MODEL",
    # Connector / factory seam
    "build_chat_model",
    "default_chat_model",
    "available_providers",
    "CHAT_MODEL_FACTORIES",
]
