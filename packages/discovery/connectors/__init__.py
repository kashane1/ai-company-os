"""Source connectors + the compliance controls they share.

A connector's ONLY job is to turn a query into raw signals with provenance. It
does not make scoring or compliance *decisions* — it surfaces facts and flags;
the analyst and the compliance reviewer decide. Robots.txt checking and
per-domain rate limiting live here so they are enforced once, not reinvented.
"""

from packages.discovery.connectors.base import (
    CompliancePolicyError,
    Connector,
    ConnectorConfig,
    RawSignal,
)
from packages.discovery.connectors.rate_limiter import RateLimiter
from packages.discovery.connectors.robots import RobotsPolicy

__all__ = [
    "CompliancePolicyError",
    "Connector",
    "ConnectorConfig",
    "RawSignal",
    "RateLimiter",
    "RobotsPolicy",
]
