"""Online booking setup (Agency layer, G6 — Package C service).

Injects a supported provider's booking embed into a client site, idempotently,
and records the setup. Reuses the scaffolded ``BOOKING.md`` stub's intent: the
owner manages the booking provider; we wire its embed into the site.

[D8] guardrails: only a known provider's embed is injected; the booking URL is
scheme-checked (no ``javascript:``); the injection target is validated; and a
re-run **replaces** the existing block rather than appending (no double-inject).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from packages.config.settings import load_runtime_paths
from packages.db.json_store import JsonStore

_RECORD_ID = "booking"
_START = "<!-- bbw:booking:start -->"
_END = "<!-- bbw:booking:end -->"
# Optional placeholder a site can expose for precise placement.
_MARKER = "<!-- BOOKING_EMBED -->"

# Supported providers → embed template ({url} substituted). Link-style embeds are
# used where a provider's inline widget needs account-specific script ids.
def _link(label: str) -> str:
    return '<a class="book-now" href="{url}" target="_blank" rel="noopener">' + label + "</a>"


_PROVIDERS: dict[str, str] = {
    "calendly": (
        '<div class="calendly-inline-widget" data-url="{url}" data-resize="true" '
        'style="min-width:320px;height:700px"></div>\n'
        '<script src="https://assets.calendly.com/assets/external/widget.js" async></script>'
    ),
    # Acuity ships an embed.js that auto-resizes the iframe to its content height.
    "acuity": (
        '<iframe src="{url}" title="Schedule Appointment" width="100%" height="800" '
        'frameborder="0"></iframe>\n'
        '<script src="https://embed.acuityscheduling.com/js/embed.js" async></script>'
    ),
    "square": _link("Book an appointment"),
    "vagaro": _link("Book on Vagaro"),
    "mindbody": _link("Book on Mindbody"),
    "fresha": _link("Book on Fresha"),
    "booksy": _link("Book on Booksy"),
}

SUPPORTED_PROVIDERS = tuple(sorted(_PROVIDERS))


class BookingError(ValueError):
    """Unsupported provider, bad URL, or no injection target."""


def _validate_url(url: str) -> str:
    value = url.strip()
    if not (value.startswith("http://") or value.startswith("https://")):
        raise BookingError(f"booking url must be http(s): {url!r}")
    if any(c in value for c in '"<> '):
        raise BookingError(f"booking url has invalid characters: {url!r}")
    return value


def render_booking_embed(provider: str, booking_url: str) -> str:
    """Return the provider's embed HTML for ``booking_url`` (validated)."""
    key = provider.strip().lower()
    template = _PROVIDERS.get(key)
    if template is None:
        raise BookingError(
            f"unsupported provider {provider!r}; supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )
    return template.format(url=_validate_url(booking_url))


def inject_booking_embed(html: str, embed: str) -> str:
    """Inject ``embed`` into ``html`` idempotently (re-run replaces, never appends).

    Placement preference: an existing booking block → a ``<!-- BOOKING_EMBED -->``
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
    raise BookingError("no injection target (need an existing block, a marker, or </body>)")


def inject_booking_into_file(path: Path, provider: str, booking_url: str) -> Path:
    """Inject the embed into an HTML file in place. Idempotent."""
    if not path.is_file():
        raise BookingError(f"site file not found: {path}")
    embed = render_booking_embed(provider, booking_url)
    path.write_text(inject_booking_embed(path.read_text(encoding="utf-8"), embed), encoding="utf-8")
    return path


def inject_booking_html_into_file(path: Path, embed_html: str) -> Path:
    """Inject an operator-supplied embed snippet (raw HTML) into a file. Idempotent.

    For platforms whose real embed is account-specific HTML pasted from their
    dashboard (e.g. Square Appointments' advanced booking widget) rather than a
    URL we can template. The snippet is trusted operator input. Re-runs replace
    the existing block, never append.
    """
    if not path.is_file():
        raise BookingError(f"site file not found: {path}")
    embed = embed_html.strip()
    if not embed:
        raise BookingError("empty booking embed")
    path.write_text(inject_booking_embed(path.read_text(encoding="utf-8"), embed), encoding="utf-8")
    return path


@dataclass(frozen=True)
class BookingSetup:
    product_id: str
    provider: str
    booking_url: str
    injected: bool = False
    completed_at: str = ""
    # True for the recurring "Booking — Fully Managed" service (we run it on the
    # platform for the client); False for one-time Connect / Done-for-you setup.
    managed: bool = False

    def validate(self) -> None:
        if not self.product_id.strip():
            raise ValueError("booking: product_id is required")
        if self.provider.strip().lower() not in _PROVIDERS:
            raise BookingError(f"unsupported provider {self.provider!r}")
        _validate_url(self.booking_url)

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "provider": self.provider,
            "booking_url": self.booking_url,
            "injected": self.injected,
            "completed_at": self.completed_at,
            "managed": self.managed,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "BookingSetup":
        return cls(
            product_id=str(payload["product_id"]),
            provider=str(payload["provider"]),
            booking_url=str(payload["booking_url"]),
            injected=bool(payload.get("injected", False)),
            completed_at=str(payload.get("completed_at", "")),
            managed=bool(payload.get("managed", False)),
        )


def _store(product_id: str, root: Path | None = None) -> JsonStore:
    base = root or (load_runtime_paths().state_root / "clients" / product_id / "services")
    return JsonStore(base)


def save_booking_setup(record: BookingSetup, *, root: Path | None = None) -> Path:
    record.validate()
    return _store(record.product_id, root).save(_RECORD_ID, record.to_dict())


def load_booking_setup(product_id: str, *, root: Path | None = None) -> BookingSetup | None:
    store = _store(product_id, root)
    if not store.path_for(_RECORD_ID).exists():
        return None
    return BookingSetup.from_dict(store.load(_RECORD_ID))
