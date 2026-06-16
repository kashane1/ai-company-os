"""Online ordering setup (Agency layer — the Online Ordering service line).

Wires a supported POS's hosted online-ordering page into a client site as an
"Order Online" button, idempotently, and records the setup. The client takes
orders + payment through their **own** POS merchant account (Square / Clover);
the agency is never a payment facilitator and never touches funds. This mirrors
``booking.py``: the owner runs the platform, we wire its entry point into the
site.

Launch scope is **hosted/embedded only** — there is no custom cart → Orders API
→ fulfillment ("Premium") tier here. If/when that is greenlit, the Square/Clover
Orders-API integration would live in this module behind the same platform gate.

Platform gate (see docs/agency/ordering-platform-routing.md): Square + Clover are
freely supported. **Toast is gated** — its ordering write API is partner-gated and
restaurant-only, so a ``ordering_setup`` on Toast is a hard block; only a
``ordering_connect`` link against an existing Toast ordering page is allowed.

[D8] guardrails: only a known platform's link is injected; the ordering URL is
scheme-checked (no ``javascript:``); the injection target is validated; and a
re-run **replaces** the existing block rather than appending (no double-inject).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore

_RECORD_ID = "ordering"
_START = "<!-- bbw:ordering:start -->"
_END = "<!-- bbw:ordering:end -->"
# Optional placeholder a site can expose for precise placement.
_MARKER = "<!-- ORDER_ONLINE_EMBED -->"

_DEFAULT_LABEL = "Order Online"


def _link(label: str) -> str:
    return '<a class="order-online" href="{url}" target="_blank" rel="noopener">' + label + "</a>"


# Supported POS platforms → "Order Online" button template ({url} substituted).
# All three render an identical customer-facing link to the POS's hosted ordering
# page; the difference between them is the SALE gate (see _PLATFORM_TIER), not the
# markup. Square Online / Clover also expose account-specific inline embed snippets
# — paste those through ``inject_order_html_into_file`` instead of templating a URL.
_PLATFORMS: dict[str, str] = {
    "square": _link(_DEFAULT_LABEL),
    "clover": _link(_DEFAULT_LABEL),
    "toast": _link(_DEFAULT_LABEL),
}

# Freely sold + advertised on the public site.
SUPPORTED_PLATFORMS = ("square", "clover")
# Assess-on-request only; never advertised as supported.
GATED_PLATFORMS = ("toast",)
ALL_PLATFORMS = tuple(sorted(_PLATFORMS))

# The two pick-one bases (catalog `exclusive_group: ordering_base`).
ORDERING_BASES = ("ordering_connect", "ordering_setup")

# The stackable ordering modifier SKUs (catalog `requires_group: ordering_base`).
ORDERING_MODIFIERS = (
    "ordering_menu_entry",   # "Menu Build" — one-time
    "ordering_management",   # "Menu Management" — recurring retainer
)

# Platform capability for each base tier, encoding the routing matrix in
# docs/agency/ordering-platform-routing.md so a sale can't be fulfilled on a
# platform that can't deliver it. Level is one of:
#   "none"    — not deliverable on this platform (hard block → OrderingError)
#   "limited" — deliverable but constrained (operator advisory, not a block)
# A (base, platform) pair absent from this map is fully supported.
_PLATFORM_TIER: dict[str, dict[str, tuple[str, str]]] = {
    "ordering_setup": {
        "toast": (
            "none",
            "Toast's ordering write API is partner-gated and restaurant-only — confirm the "
            "client's integration tier grants write access before a Setup; otherwise sell "
            "Connect against their existing Toast ordering link",
        ),
    },
    "ordering_connect": {
        "toast": (
            "limited",
            "Toast is assess-on-request — only link to an existing Toast online-ordering page, "
            "don't promise a managed setup",
        ),
    },
}


class OrderingError(ValueError):
    """Unsupported platform, bad URL, no injection target, or platform/tier mismatch."""


def _validate_url(url: str) -> str:
    value = url.strip()
    if not (value.startswith("http://") or value.startswith("https://")):
        raise OrderingError(f"ordering url must be http(s): {url!r}")
    if any(c in value for c in '"<> '):
        raise OrderingError(f"ordering url has invalid characters: {url!r}")
    return value


def render_order_embed(platform: str, ordering_url: str, label: str = _DEFAULT_LABEL) -> str:
    """Return the platform's "Order Online" button HTML for ``ordering_url`` (validated)."""
    key = platform.strip().lower()
    template = _PLATFORMS.get(key)
    if template is None:
        raise OrderingError(
            f"unsupported platform {platform!r}; supported: {', '.join(ALL_PLATFORMS)}"
        )
    text = label.strip() or _DEFAULT_LABEL
    return _link(text).format(url=_validate_url(ordering_url))


def check_platform_for_tier(platform: str, base: str) -> tuple[list[str], list[str]]:
    """Return ``(errors, warnings)`` for selling base tier ``base`` on ``platform``.

    ``errors`` are hard blocks (the platform genuinely can't deliver this tier —
    e.g. a Done-for-you Setup on Toast); ``warnings`` are deliverable-but-gated
    combos the operator must confirm first (e.g. a Connect link against an
    existing Toast ordering page). Unknown platform/base ids are reported as
    errors.
    """
    key = platform.strip().lower()
    errors: list[str] = []
    warnings: list[str] = []
    if base not in ORDERING_BASES:
        errors.append(f"unknown ordering base {base!r}")
        return errors, warnings
    if key not in _PLATFORMS:
        errors.append(f"unsupported platform {platform!r}")
        return errors, warnings
    level, note = _PLATFORM_TIER.get(base, {}).get(key, ("full", ""))
    if level == "none":
        errors.append(f"{base} is not supported on {key}: {note}")
    elif level == "limited":
        warnings.append(f"{base} is gated on {key}: {note}")
    return errors, warnings


def assert_platform_supported(platform: str, base: str) -> None:
    """Raise :class:`OrderingError` if base tier ``base`` can't be delivered on ``platform``."""
    errors, _ = check_platform_for_tier(platform, base)
    if errors:
        raise OrderingError("; ".join(errors))


def check_modifiers(modifiers: tuple[str, ...] | list[str]) -> list[str]:
    """Return a list of errors for unknown ordering modifier ids.

    Menu Build / Menu Management are platform-agnostic operational add-ons (they
    work the same on Square or Clover), so there is no per-platform gate — only a
    known-id check, kept parallel to ``booking.check_modifiers_for_platform``.
    """
    return [f"unknown ordering modifier {m!r}" for m in modifiers if m not in ORDERING_MODIFIERS]


def assert_modifiers_supported(modifiers: tuple[str, ...] | list[str]) -> None:
    """Raise :class:`OrderingError` if any modifier id is unknown."""
    errors = check_modifiers(modifiers)
    if errors:
        raise OrderingError("; ".join(errors))


def recommend_platform(existing_pos: str = "") -> str:
    """Recommend a POS for online ordering, mirroring ordering-platform-routing.md.

    Default to Square (easiest API, free hosted ordering). Keep a client already on
    Clover on Clover (don't migrate POS to sell ordering). Toast routes to Toast but
    as Connect-only (assess-on-request).
    """
    pos = existing_pos.strip().lower()
    if pos in ("clover", "toast"):
        return pos
    return "square"


def inject_order_embed(html: str, embed: str) -> str:
    """Inject ``embed`` into ``html`` idempotently (re-run replaces, never appends).

    Placement preference: an existing ordering block → a ``<!-- ORDER_ONLINE_EMBED -->``
    marker → before ``</body>``. Raises if none of those targets exist.
    """
    block = f"{_START}\n{embed}\n{_END}"
    if _START in html and _END in html:
        pattern = re.escape(_START) + r".*?" + re.escape(_END)
        return re.sub(pattern, lambda _m: block, html, count=1, flags=re.DOTALL)
    if _MARKER in html:
        return html.replace(_MARKER, block, 1)
    if "</body>" in html:
        return html.replace("</body>", f"{block}\n</body>", 1)
    raise OrderingError("no injection target (need an existing block, a marker, or </body>)")


def inject_order_into_file(
    path: Path, platform: str, ordering_url: str, label: str = _DEFAULT_LABEL
) -> Path:
    """Inject the "Order Online" button into an HTML file in place. Idempotent."""
    if not path.is_file():
        raise OrderingError(f"site file not found: {path}")
    embed = render_order_embed(platform, ordering_url, label)
    path.write_text(inject_order_embed(path.read_text(encoding="utf-8"), embed), encoding="utf-8")
    return path


def inject_order_html_into_file(path: Path, embed_html: str) -> Path:
    """Inject an operator-supplied embed snippet (raw HTML) into a file. Idempotent.

    For platforms whose real online-ordering embed is account-specific HTML pasted
    from their dashboard (e.g. Square Online's order/checkout button, Clover's
    online-ordering widget) rather than a URL we can template. The snippet is
    trusted operator input. Re-runs replace the existing block, never append.
    """
    if not path.is_file():
        raise OrderingError(f"site file not found: {path}")
    embed = embed_html.strip()
    if not embed:
        raise OrderingError("empty ordering embed")
    path.write_text(inject_order_embed(path.read_text(encoding="utf-8"), embed), encoding="utf-8")
    return path


@dataclass(frozen=True)
class OrderingSetup:
    product_id: str
    platform: str
    ordering_url: str
    # The purchased pick-one base SKU: "ordering_connect" or "ordering_setup".
    # Validated against the platform so a sale can't be marked fulfilled on a
    # platform that can't deliver the tier (e.g. a Setup on Toast).
    base: str = "ordering_connect"
    injected: bool = False
    completed_at: str = ""
    # True when the recurring "Menu Management" retainer (ordering_management) is
    # active — we make ongoing menu edits; False for one-time setup only.
    managed: bool = False
    # The purchased modifier SKUs (ordering_menu_entry / ordering_management).
    modifiers: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.product_id.strip():
            raise ValueError("ordering: product_id is required")
        if self.platform.strip().lower() not in _PLATFORMS:
            raise OrderingError(f"unsupported platform {self.platform!r}")
        _validate_url(self.ordering_url)
        assert_platform_supported(self.platform, self.base)
        assert_modifiers_supported(self.modifiers)

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "platform": self.platform,
            "ordering_url": self.ordering_url,
            "base": self.base,
            "injected": self.injected,
            "completed_at": self.completed_at,
            "managed": self.managed,
            "modifiers": list(self.modifiers),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "OrderingSetup":
        return cls(
            product_id=str(payload["product_id"]),
            platform=str(payload["platform"]),
            ordering_url=str(payload["ordering_url"]),
            base=str(payload.get("base", "ordering_connect")),
            injected=bool(payload.get("injected", False)),
            completed_at=str(payload.get("completed_at", "")),
            managed=bool(payload.get("managed", False)),
            modifiers=tuple(str(m) for m in payload.get("modifiers", [])),
        )


def _store(product_id: str, root: Path | None = None) -> JsonStore:
    base = root or (load_runtime_paths().state_root / "clients" / product_id / "services")
    return JsonStore(base)


def save_ordering_setup(record: OrderingSetup, *, root: Path | None = None) -> Path:
    record.validate()
    return _store(record.product_id, root).save(_RECORD_ID, record.to_dict())


def load_ordering_setup(product_id: str, *, root: Path | None = None) -> OrderingSetup | None:
    store = _store(product_id, root)
    if not store.path_for(_RECORD_ID).exists():
        return None
    return OrderingSetup.from_dict(store.load(_RECORD_ID))
