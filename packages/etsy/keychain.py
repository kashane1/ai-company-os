"""Deprecated compatibility exports for the Etsy ``.etsy.env`` credential store.

This module performs no macOS Keychain or subprocess access. New code should
import the same names from :mod:`packages.etsy.credentials`.
"""

from packages.etsy.credentials import (
    ETSY_API_CREDENTIAL,
    ETSY_OAUTH_ACCESS_TOKEN,
    ETSY_OAUTH_EXPIRES_AT,
    ETSY_OAUTH_REFRESH_TOKEN,
    store_etsy_api_credential,
    store_etsy_oauth_material,
)

__all__ = [
    "ETSY_API_CREDENTIAL",
    "ETSY_OAUTH_ACCESS_TOKEN",
    "ETSY_OAUTH_EXPIRES_AT",
    "ETSY_OAUTH_REFRESH_TOKEN",
    "store_etsy_api_credential",
    "store_etsy_oauth_material",
]
