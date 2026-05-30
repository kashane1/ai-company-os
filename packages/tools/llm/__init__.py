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

__all__ = ["ChatModel", "ModelError", "OpenRouterClient"]
