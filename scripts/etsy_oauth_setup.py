#!/usr/bin/env python3
"""Run one confirmed, local Etsy OAuth PKCE setup flow.

This command only persists credentials when invoked with
``--confirmed-persistent-access``. It does not open a browser and never prints
OAuth codes, token material, the PKCE verifier, or the shared secret.
"""

from __future__ import annotations

import argparse
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.etsy.auth import (
    CredentialReadiness,
    EtsyCredentials,
    build_authorization_url,
    create_pkce_pair,
    credential_readiness,
    exchange_authorization_code,
    validate_callback_state,
)
from packages.etsy.credentials import store_etsy_oauth_material

CALLBACK_URI = "http://localhost:3003/oauth/redirect"


class OAuthSetupFlow:
    """One in-memory PKCE exchange; ephemeral data never reaches stdout."""

    def __init__(self, credentials: EtsyCredentials) -> None:
        self.credentials = credentials
        self.verifier, self.challenge = create_pkce_pair()
        # OAuth state must be unpredictable and remains process-local.
        import secrets

        self.state = secrets.token_urlsafe(32)
        self.completed = False
        self.succeeded = False

    def authorization_url(self) -> str:
        return build_authorization_url(
            client_id=self.credentials.keystring,
            redirect_uri=CALLBACK_URI,
            state=self.state,
            code_challenge=self.challenge,
        )

    def complete_callback(self, *, code: str, state: str) -> None:
        validate_callback_state(self.state, state)
        token = exchange_authorization_code(
            client_id=self.credentials.keystring,
            redirect_uri=CALLBACK_URI,
            code=code,
            code_verifier=self.verifier,
        )
        store_etsy_oauth_material(
            composite_credential=self.credentials.api_key,
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            expires_at=token.expires_at.isoformat(),
        )
        self.completed = True
        self.succeeded = True


def _handler_for(flow: OAuthSetupFlow) -> type[BaseHTTPRequestHandler]:
    class OAuthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - HTTPServer requires this spelling.
            parsed = urlparse(self.path)
            if parsed.path == "/start":
                self.send_response(302)
                self.send_header("Location", flow.authorization_url())
                self.end_headers()
                return
            if parsed.path != "/oauth/redirect":
                self._page(404, "Not found")
                return
            values = parse_qs(parsed.query)
            code = values.get("code", [""])[0]
            received_state = values.get("state", [""])[0]
            if not code:
                self._page(400, "OAuth callback did not include an authorization code.")
                flow.completed = True
                return
            try:
                flow.complete_callback(code=code, state=received_state)
            except Exception:
                # Neither codes, tokens, nor upstream response details are safe to echo.
                self._page(400, "OAuth setup could not be completed. Check the local command and try again.")
                flow.completed = True
                return
            self._page(200, "Etsy read-only authorization completed. You may close this page.")

        def _page(self, status: int, message: str) -> None:
            body = f"<!doctype html><title>Etsy OAuth setup</title><p>{message}</p>".encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            """Suppress HTTP request logs because callback URLs contain OAuth codes."""

    return OAuthHandler


def serve_oauth_server(flow: OAuthSetupFlow, timeout_seconds: int) -> bool:
    """Serve `/start` and exactly one callback, returning whether it succeeded."""
    deadline = time.monotonic() + timeout_seconds
    with HTTPServer(("localhost", 3003), _handler_for(flow)) as server:
        while not flow.completed and time.monotonic() < deadline:
            server.timeout = min(1.0, max(0.01, deadline - time.monotonic()))
            server.handle_request()
    return flow.succeeded


def main(
    argv: list[str] | None = None,
    *,
    readiness_provider: Callable[[], CredentialReadiness] = credential_readiness,
    server_runner: Callable[[OAuthSetupFlow, int], bool | None] = serve_oauth_server,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirmed-persistent-access", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")

    readiness = readiness_provider()
    if readiness.credentials is None:
        print(readiness.message)
        return 2
    if not args.confirmed_persistent_access:
        print("Refusing to launch OAuth without --confirmed-persistent-access confirmation.")
        return 2

    print("Open http://localhost:3003/start to begin the Etsy read-only authorization.")
    succeeded = server_runner(OAuthSetupFlow(readiness.credentials), args.timeout_seconds)
    if succeeded:
        print("Etsy read-only authorization completed and credentials were stored in .etsy.env.")
        return 0
    print("Etsy OAuth setup ended without completing authorization.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
