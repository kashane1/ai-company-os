# Discovery Guide (new user)

A practical guide to the discovery layer added to `ai-company-os` — the front of
the loop that finds product opportunities, scores them, and decides which ones
earn a validation experiment before any code gets written.

If you only read one thing: run the demo, then read "Five ways to start."

```bash
python3 scripts/discovery_demo.py
```

## What this adds

The platform already builds and ships products (supervisor → workers → approval
gates → App Store). What it did not have was a structured way to answer **"what
should we build next, and is anyone actually going to pay for it?"** This layer
fills that gap. Nothing here bypasses the existing approval gates — it feeds
them.

The loop:

```
discover  →  score  →  validate gate  →  (existing build/ship lanes)
   │            │            │
sources     scorecard    thresholds + hard gates
robots+rl   12 signals   "no build before a passed experiment"
```

## The pieces

| Piece | Path | What it does |
|-------|------|--------------|
| Opportunity schema | `packages/schemas/opportunity.py` | The atomic unit: a wedge with evidence + 12 signals |
| Experiment schema | `packages/schemas/experiment.py` | A cheap demand test with success criteria set in advance |
| Dossier schema | `packages/schemas/dossier.py` | The one-click brief the build lane works from |
| Scoring | `packages/discovery/scoring.py` | Weighted 0–100 score + confidence (math only) |
| Weights | `packages/discovery/config/scoring.yaml` | The tunable, versioned scoring asset |
| Connectors | `packages/discovery/connectors/` | Sources (HN, GitHub) behind one contract |
| Compliance | `connectors/robots.py`, `rate_limiter.py` | robots.txt + per-domain throttling, enforced once |
| Sources | `packages/discovery/config/sources.yaml` | Which sources are enabled + their limits |
| Inbox | `packages/discovery/inbox.py` | Deduped, persistent store of discovered wedges |
| Scoring pass | `packages/discovery/scoring_pass.py` | Batch: fill signals (via an analyst interface) → score → rank → report |
| Gates | `packages/policies/discovery_gates.py` | Validate gate + build gate (policy owns decisions) |
| Demo | `scripts/discovery_demo.py` | Runs all of the above end to end, offline |

Specs: [`opportunity-scorecard.md`](opportunity-scorecard.md),
[`founder-os.md`](founder-os.md), [`discovery-evals.md`](discovery-evals.md),
[`discovery-compliance.md`](discovery-compliance.md).

## How it works, end to end

**1. Discover.** A connector turns a query into `RawSignal`s — each with a
mandatory source URL and a short quote. Connectors only surface candidates;
they make no scoring or compliance *decisions*. Compliance is centralized:
robots.txt is checked before any HTML fetch and every source is rate-limited.

```python
from packages.discovery.connectors.registry import build_connectors
from packages.discovery.connectors.base import FetchOptions

connectors = build_connectors()                       # only enabled, known sources
signals = connectors["hackernews"].fetch(FetchOptions(query="automate invoicing"))
```

**2. Inbox.** Signals become `OpportunityRecord` drafts (status `inbox`). The id
is derived from the normalized title, so re-running discovery tomorrow *merges*
evidence into the existing record instead of creating duplicates — which is what
makes a daily schedule safe.

```python
from packages.discovery.inbox import OpportunityInbox

inbox = OpportunityInbox()
inbox.ingest_signals("hackernews", "automate invoicing", signals)
```

**3. Score.** A human or an analyst agent fills the twelve signals (0–10). The
scorer produces a normalized 0–100 score plus a confidence value driven by how
much evidence exists and how diverse the sources are.

**4. Validate gate.** `evaluate_opportunity` decides whether a wedge may advance
to a validation experiment. It blocks on hard gates (high ToS/regulatory risk,
blocked compliance flags, no distribution path) and on thresholds (score,
confidence). "Does not advance" is a normal outcome — it returns structured
reasons, it does not error.

**5. Build gate.** `assert_ready_to_build` refuses to hand a wedge to the build
lane unless a validation `ExperimentRecord` has actually *passed*. This is the
"validate before you build — code is the most expensive test" rule, enforced as
a real `PolicyViolation` consistent with the rest of `packages/policies/`.

## Five ways to start

Pick one. Don't do all five at once — the point of the loop is focus.

**1. Run the demo and read the output.** `python3 scripts/discovery_demo.py`.
It discovers from an offline fixture, scores the Etsy worked example to 71,
passes the validate gate, and shows the build gate blocking until an experiment
passes. ~10 seconds, no network, no setup. This is the fastest way to build a
mental model.

**2. Do one live discovery run on Hacker News.** No credentials needed:
`python3 scripts/discovery_demo.py --live --query "tool to automate <your niche>"`.
Hacker News is enabled by default and needs no auth. Read the inbox it produces
and ask: are these real, specific pains, or noise? That tells you whether your
query language is finding "the language of pain."

**3. Score five wedges by hand.** Take five inbox records and fill their twelve
signals yourself using [`opportunity-scorecard.md`](opportunity-scorecard.md).
Run them through `evaluate_opportunity`. The goal is to calibrate *your* sense of
the scorecard before you let an agent score — you want to trust the ranking
before you automate it. A scoring dashboard you trust beats six half-built
layers.

**4. Turn on GitHub as a second source.** Put a token in `GITHUB_TOKEN`
(`.env`), and the registry will build the GitHub connector automatically (it is
already `enabled: true` in `config/sources.yaml`, and refuses to run without a
token rather than hitting the anonymous quota). Two independent sources is the
minimum for the confidence model to clear the validate gate — so this is the
unlock for "actionable," not just "hypothesis."

**5. Run one validation experiment to completion.** Pick your single
highest-confidence wedge. Write an `ExperimentRecord` with `success_criteria`
set *before* you run (e.g. 50 waitlist signups in 7 days). Run the cheapest
sufficient test. Record the result. Whether it passes or fails, you've exercised
the full gate and produced the first row of the labeled dataset that becomes
your moat ([`discovery-evals.md`](discovery-evals.md)).

## Automating discovery (where you said you're headed)

The current surface is a clean, tested library plus a demo — deliberately not
yet wired into the supervisor/queue, to keep with the repo's "expand only where
daily use proves the need" rule. Discovery is **operator-triggered, not
scheduled**: you start a sweep when you want one and can stop it at any time
(like `./scripts/runtime start|status|stop`). The natural next steps, in order:

1. **An on-demand discovery run you can start and stop.** A thin controller that
   calls `build_connectors()` → `inbox.ingest_signals(...)` across your enabled
   sources and queries, honors a stop signal mid-run, and writes a `DiscoveryRun`
   record (status + sources hit + signals ingested) for the audit trail. The
   inbox dedup makes runs idempotent and resumable. Start here — run one, read the
   inbox, then decide what to add. (Scheduling is an optional later add-on, not
   the default.)
2. **Run the scoring pass.** ✅ *Implemented* — `packages/discovery/scoring_pass.py`.
   It selects unscored `inbox` records, fills the twelve signals via a
   `SignalProvider` (your analyst agent behind an interface), scores + gates each,
   persists the result, and returns a ranked `ScoringPassReport` you can render to
   markdown for your Monday review. Records it can't score yet are left in the
   inbox, not guessed. Wire a real `SignalProvider` (an LLM analyst) to automate
   the one analytical step:

   ```python
   from packages.discovery.analyst import HeuristicSignalProvider, LLMSignalProvider
   from packages.discovery.inbox import OpportunityInbox
   from packages.discovery.scoring_pass import ScoringPass
   from packages.tools.llm.client import OpenRouterClient

   # Baseline, deterministic, offline:
   provider = HeuristicSignalProvider()
   # Or the real analyst (needs OPENROUTER_API_KEY):
   provider = LLMSignalProvider(OpenRouterClient())

   report = ScoringPass(OpportunityInbox(), signal_provider=provider).run()
   print(report.to_markdown())     # top wedges, ranked, with advance/hold reasons
   ```

   **The LLM analyst (`LLMSignalProvider`).** It hands the model the evidence and
   asks for the twelve signals as strict JSON, scored against the rubric in
   `opportunity-scorecard.md`. Key heuristics, all enforced in `analyst.py`:
   temperature 0 for reproducible scoring; the rubric repeats that `risk` is
   *inverted* (10 = low risk) because that's the most common scoring error;
   parsing is **strict** — all twelve keys must be present and numeric or the
   provider returns `None` (incomplete == no score, so a silently-missing
   `distribution_path` can't trip a hard gate for the wrong reason); values are
   clamped to 0–10; and the model can return `{"insufficient_evidence": true}` to
   send a thin wedge back for more research instead of guessing. The model call
   sits behind a one-method `ChatModel` interface (`packages/tools/llm`), so it's
   vendor-swappable and fully unit-tested with a stub — no network in tests.
3. **Wire the gates into the orchestrator.** Have the supervisor call
   `assert_ready_to_build` before it ever routes a build task for a discovered
   wedge — so the "validate before build" rule is enforced by the platform, not
   by convention.
4. **Add connectors as needed.** Each new source is one class implementing the
   `Connector` contract plus a line in `config/sources.yaml` and the registry's
   `CONNECTOR_FACTORIES`. Reddit/Product Hunt/Google Trends are already stubbed
   as `enabled: false` entries to copy from.
5. **Close the loop with evals.** Once wedges ship, write outcomes back and
   retune `scoring.yaml` monthly. That is the compounding asset.

## Adding a new connector (recipe)

1. Implement the `Connector` protocol (`connectors/base.py`): `fetch()` returns
   `list[RawSignal]` with provenance; `healthcheck()` returns `(ok, detail)`.
   Use the injected `httpx.Client` + a shared `RateLimiter`, and refuse
   `bulk=True` and disabled state with `CompliancePolicyError`. Use
   `RobotsPolicy` before any HTML fetch.
2. Add the source to `config/sources.yaml` (start `enabled: false`).
3. Register a factory in `connectors/registry.py` → `CONNECTOR_FACTORIES`.
4. Add a unit test using `httpx.MockTransport` (see
   `tests/python/unit/test_discovery_connectors.py`) — no live network in tests.

## Tests

```bash
python3 -m pytest tests/python/unit/test_discovery_*.py
```

Covers the scorecard worked example, confidence, every hard gate, the rate
limiter, robots (allow/deny/cache/fail-closed), both connectors via mock
transport, the registry, and the inbox dedup. The new code sits at ~94% line
coverage, well above the repo's 55% gate.
