# AGENTS.md

The full agent model lives in [`docs/agent-model.md`](docs/agent-model.md). Read it for worker responsibilities, role boundaries, approval rules, testing contract, and runtime/state rules.

## TL;DR

- **Current HomeFromWorking priority (2026-09-02):** use the [repeatable shirt workflow](docs/founder/printify-shirt-workflow.md): native Printify Duplicate once, then `scripts/pod_draft.py` for artwork/copy updates and preservation checks. Reuse the command instead of per-shirt scripts or full browser setup. Broader product research is deferred. Etsy payload automation remains planned; publishing requires separate explicit approval.
- For transparent POD, shirt, mug, merchandise, or Printify artwork requests,
  read `skills/adapters/codex/pod-artwork-generator.md` before proposing style
  directions or generating artwork.

- The **platform** owns orchestration, persistence, queueing, approvals, and policy.
- The **supervisor** decomposes goals and routes work; it does not deliver.
- **Active workers** consume engineering, iOS, App Store preparation, outreach operations, and skill-evolution tasks. Other lane enums do not imply a queue consumer; `packages/policies/worker_capabilities.py` makes acceptance explicit. Each worker is narrow, schema-driven, and policy-bound.
- **Outreach** is an operations lane for drafts, ledgers, follow-ups, and CRM sync; it does not send cold emails, texts, or DMs without a future explicit gate.
- **Conversion Lab** is an agency capability for advisory synthetic-audience preflight reports; it does not predict revenue, launch ads, or bypass approval gates.
- **Codex** is the engineering engine. It writes code; it does not decide what code matters.
- **OpenClaw** (if used) is an interface, not an orchestrator.
- The **discovery layer** (`packages/discovery/`) supports find → score → validate *what* to build; its handoffs remain gated by `packages/policies/discovery_gates.py`. It is not a prerequisite for HomeFromWorking's owner-selected listing workflow. Operator commands: [`docs/founder/operator-guide.md`](docs/founder/operator-guide.md). Deep dive: [`docs/founder/discovery-guide.md`](docs/founder/discovery-guide.md).
- Engineering and iOS review require executed registry-configured verification and complete staged, unstaged, and new-file evidence. Worker infrastructure errors retry with bounded backoff, then exit visibly. The LaunchAgent owns the foreground supervisor and preserves fail-stop recovery.
- Completion requires persisted evidence and a passing post-run validator. Database lifecycle writes share a transaction; Redis dispatch has separate, explicit recovery limits.
- Logic-bearing changes ship with lane-matching tests. Irreversible actions require approval. Runtime state lives under ignored `state/` paths.

When the architecture changes materially, update `README.md`, this stub, `docs/agent-model.md`, and `docs/architecture.md`.
