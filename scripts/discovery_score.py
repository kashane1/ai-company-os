#!/usr/bin/env python3
"""Score the discovery inbox — operator CLI.

The companion to ``scripts/discovery_run.py``. A run *fills* the inbox; this
*ranks* it: it fills the twelve signals for every unscored ``inbox`` record via a
``SignalProvider``, runs the scorecard, applies the validate gate, persists the
result, and prints a ranked report. Records it can't score yet (no evidence) are
left in the inbox rather than guessed.

    python3 scripts/discovery_score.py                 # heuristic baseline (offline)
    python3 scripts/discovery_score.py --provider llm  # real analyst (needs OPENROUTER_API_KEY)
    python3 scripts/discovery_score.py --top 10        # show more rows
    python3 scripts/discovery_score.py --limit 50      # cap how many records to score this pass

Provider choice mirrors the guide: ``heuristic`` is the deterministic, offline
first pass; ``llm`` is the production analyst behind ``ChatModel`` and needs
``OPENROUTER_API_KEY`` in the environment (see ``.env.example``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.discovery.analyst import (  # noqa: E402
    HeuristicSignalProvider,
    LLMSignalProvider,
)
from packages.discovery.inbox import OpportunityInbox  # noqa: E402
from packages.discovery.scoring_pass import ScoringPass, SignalProvider  # noqa: E402
from packages.tools.llm.client import ModelError, OpenRouterClient  # noqa: E402

PROVIDERS = ("heuristic", "llm")


def build_provider(name: str) -> SignalProvider:
    """Map a ``--provider`` name to a concrete ``SignalProvider``.

    ``heuristic`` is fully offline and deterministic. ``llm`` constructs the
    OpenRouter-backed analyst; the client only reads the API key when it makes a
    call, so construction here stays cheap and key errors surface at score time
    with a clear message rather than on import.
    """
    if name == "heuristic":
        return HeuristicSignalProvider()
    if name == "llm":
        return LLMSignalProvider(OpenRouterClient())
    raise ValueError(f"unknown provider {name!r} (choose from {', '.join(PROVIDERS)})")


def _cmd_run(args: argparse.Namespace) -> int:
    provider = build_provider(args.provider)
    pass_ = ScoringPass(OpportunityInbox(), signal_provider=provider)
    try:
        report = pass_.run(limit=args.limit)
    except ModelError as exc:
        # Only the llm provider can raise this — a missing key or a transport
        # failure. Fail with a useful message instead of a traceback.
        print(f"Model error while scoring: {exc}", file=sys.stderr)
        print("Set OPENROUTER_API_KEY (see .env.example) or use --provider heuristic.")
        return 1

    if not report.scored and report.skipped_no_signals == 0:
        print("Inbox is empty — run a discovery sweep first (scripts/discovery_run.py start).")
        return 0

    print(report.to_markdown(top_n=args.top), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score and rank the discovery inbox")
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        default="heuristic",
        help="signal provider: heuristic (offline, default) or llm (needs OPENROUTER_API_KEY)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="max number of unscored records to score this pass (default: all)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="how many ranked rows to show in the report (default: 5)",
    )
    parser.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
