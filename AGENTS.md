# AGENTS.md

The full agent model lives in [`docs/agent-model.md`](docs/agent-model.md). Read it for worker responsibilities, role boundaries, approval rules, testing contract, and runtime/state rules.

## TL;DR

- The **platform** owns orchestration, persistence, queueing, approvals, and policy.
- The **supervisor** decomposes goals and routes work; it does not deliver.
- **Workers** specialize: engineering, iOS, App Store, and future lanes (support, growth, research, ops). Each is narrow, schema-driven, policy-bound.
- **Codex** is the engineering engine. It writes code; it does not decide what code matters.
- **OpenClaw** (if used) is an interface, not an orchestrator.
- The **discovery layer** (`packages/discovery/`) is the front of the loop — find → score → validate *what* to build, gated (`packages/policies/discovery_gates.py`) before anything reaches a build lane. The analyst that scores opportunities sits behind a `SignalProvider` interface; see [`docs/founder/discovery-guide.md`](docs/founder/discovery-guide.md).
- Logic-bearing changes ship with lane-matching tests. Irreversible actions require approval. Runtime state lives under `state/`.

When the architecture changes materially, update `README.md`, this stub, `docs/agent-model.md`, and `docs/architecture.md`.
