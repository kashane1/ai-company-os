#!/usr/bin/env python3
"""Safe Etsy read-only setup diagnostics; this command only reads .etsy.env."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.etsy.auth import build_authorization_url, credential_readiness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization-url", action="store_true", help="generate a read-only OAuth URL")
    parser.add_argument("--redirect-uri", help="registered OAuth callback URI")
    parser.add_argument("--state", help="privately generated callback state")
    parser.add_argument("--code-challenge", help="S256 challenge derived from a privately held PKCE verifier")
    args = parser.parse_args()

    readiness = credential_readiness()
    result = {
        "ready": readiness.ready,
        "message": readiness.message,
        "diagnostics": readiness.diagnostics or {},
    }
    if args.authorization_url:
        if not args.redirect_uri or not args.state or not args.code_challenge:
            parser.error("--redirect-uri, --state, and --code-challenge are required with --authorization-url")
        credential = readiness.credentials
        client_id = credential.keystring if credential else None
        if not client_id:
            parser.error("missing Etsy keystring; configure ETSY_API_CREDENTIAL in .etsy.env first")
        result["authorization_url"] = build_authorization_url(
            client_id=client_id,
            redirect_uri=args.redirect_uri,
            state=args.state,
            code_challenge=args.code_challenge,
        )
        result["warning"] = "This command does not retain callback state, PKCE verifier, or OAuth tokens."
    print(json.dumps(result))
    return 0 if readiness.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
