"""Google Maps embeds for demo/prospect sites (Agency layer).

The browser-side companion to the server-side Places connector
(``packages/prospecting/connectors/google_places.py``). Places powers
prospecting/enrichment from the backend; this module turns a business location
into an *embeddable map* for the demo sites we ship to leads.

Two API surfaces, both keyed by ``GOOGLE_MAPS_DEMO_API_KEY``:

* **Maps Embed API** (:func:`embed_place_url` / :func:`embed_iframe_html`) — an
  interactive iframe. Embed API "place" loads are not billed per-load, which is
  why it's the default for demos.
* **Maps Static API** (:func:`static_map_url`) — a single ``<img>`` URL, useful
  when an iframe is undesirable (email, very light pages). Static loads ARE
  billed, so it's opt-in.

Everything degrades gracefully: with no key configured, the URL builders raise
(explicit misuse) but :func:`has_demo_maps_key` and :func:`embed_iframe_html`
let callers skip the map block instead of failing a demo build.
"""

from __future__ import annotations

import html
from urllib.parse import urlencode

from packages.config.settings import GOOGLE_MAPS_DEMO_API_KEY_ENV_VAR, get_api_key

EMBED_ENDPOINT = "https://www.google.com/maps/embed/v1/place"
STATIC_ENDPOINT = "https://maps.googleapis.com/maps/api/staticmap"

DEFAULT_STATIC_SIZE = "600x300"
DEFAULT_STATIC_ZOOM = 14


class DemoMapsKeyError(RuntimeError):
    """Raised when a map URL is requested but no demo Maps key is configured."""


def demo_maps_key() -> str | None:
    """Return the configured demo Maps key, or ``None`` if unset."""
    key = get_api_key(GOOGLE_MAPS_DEMO_API_KEY_ENV_VAR)
    return key or None


def has_demo_maps_key() -> bool:
    """True when a demo Maps key is available (use to gate the map block)."""
    return demo_maps_key() is not None


def _require_key(key: str | None) -> str:
    resolved = key or demo_maps_key()
    if not resolved:
        raise DemoMapsKeyError(
            f"demo maps embed needs ${GOOGLE_MAPS_DEMO_API_KEY_ENV_VAR} "
            "(set it in .env or the process env)"
        )
    return resolved


def embed_place_url(query: str, *, key: str | None = None) -> str:
    """Maps Embed API ``place`` URL for ``query`` (a business name/address).

    ``query`` is the same kind of free-text "place query" Google Maps accepts,
    e.g. ``"Joe's Plumbing, 123 Main St, Dallas, TX"``.
    """
    if not query.strip():
        raise ValueError("embed_place_url needs a non-empty place query")
    params = urlencode({"key": _require_key(key), "q": query.strip()})
    return f"{EMBED_ENDPOINT}?{params}"


def static_map_url(
    query: str,
    *,
    key: str | None = None,
    size: str = DEFAULT_STATIC_SIZE,
    zoom: int = DEFAULT_STATIC_ZOOM,
) -> str:
    """Maps Static API image URL centered on ``query`` with a marker.

    Static loads are billed per request — prefer :func:`embed_place_url` for
    interactive demos; reach for this only where an iframe won't do.
    """
    if not query.strip():
        raise ValueError("static_map_url needs a non-empty place query")
    params = urlencode(
        {
            "key": _require_key(key),
            "center": query.strip(),
            "zoom": zoom,
            "size": size,
            "markers": f"color:red|{query.strip()}",
        }
    )
    return f"{STATIC_ENDPOINT}?{params}"


def embed_iframe_html(
    query: str,
    *,
    key: str | None = None,
    title: str = "Find us on the map",
) -> str:
    """Drop-in ``<iframe>`` map block for a demo site, or ``""`` if no key.

    Returns an empty string when no key is configured so a demo build can splice
    the result in unconditionally and simply render no map. Pass an explicit
    ``key`` to force-raise instead (useful in tests / strict callers).
    """
    resolved = key or demo_maps_key()
    if not resolved:
        return ""
    src = embed_place_url(query, key=resolved)
    safe_title = html.escape(title, quote=True)
    return (
        f'<iframe class="demo-map" title="{safe_title}" loading="lazy" '
        'width="100%" height="320" style="border:0" '
        'referrerpolicy="no-referrer-when-downgrade" allowfullscreen '
        f'src="{html.escape(src, quote=True)}"></iframe>'
    )
