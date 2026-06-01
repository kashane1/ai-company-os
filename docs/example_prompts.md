# Example Prompts

A menu of prompts you can drop into a session to get real work done in this repo,
grouped by area. Each entry gives the **prompt** (copy/paste, edit the bracketed
bits) and a one-line **Activates** note of which parts of the repo it touches so
you know what you're pointing the agent at.

These are starting points, not magic words — phrase things your own way. The
*Activates* line is the value: it tells you the blast radius before you run it.

---

## Discovery (find → score → validate *what* to build)

**Terminal commands (fastest path):**

```bash
python3 scripts/discovery_run.py start --query "[your niche query]"
python3 scripts/discovery_score.py --provider llm --top 5
```

Full reference: [docs/founder/operator-guide.md](docs/founder/operator-guide.md).

> Run a discovery sweep over Hacker News and GitHub for the queries
> "[automate invoicing]" and "[etsy photo resize]". Pull the signals into the
> opportunity inbox, then score the new ones with the LLM analyst and show
> me the ranked top 5 with the advance/hold reason for each.

**Activates:** `scripts/discovery_run.py` → `inbox.py` → `scripts/discovery_score.py`
→ `scoring_pass.py` + `analyst.py` → `policies/discovery_gates.py`.

> Score the opportunity "[paste a problem + audience + 2–3 evidence links]"
> against the 12-signal scorecard, apply the validate gate, and tell me whether
> it should advance and what evidence is missing.

**Activates:** `schemas/opportunity.py`, `packages/discovery/scoring.py`, `policies/discovery_gates.py`, `docs/founder/opportunity-scorecard.md`.

> I think opportunity [opp_id] is validated — the waitlist hit [N] signups.
> Record the experiment as passed and hand it off to a build goal.

**Activates:** `schemas/experiment.py`, `db/experiment_store.py` (lifecycle), `policies/discovery_gates.py` (`assert_ready_to_build`), `packages/discovery/handoff.py` → supervisor goal.

> Generate the dossier for opportunity [opp_id] so engineering has a brief to
> work from.

**Activates:** `packages/discovery/dossier.py`, `schemas/dossier.py`.

> Run the analyst calibration eval against the heuristic provider and flag any
> drift.

**Activates:** `packages/discovery/calibration.py`, `scoring.py`, `policies/discovery_gates.py`.

---

## Web validation & deploy (fastest path to real customers)

> Opportunity `[opp_id]` cleared the validate gate. Use `web_handoff` to create a
> landing-page validation experiment and a WEB build goal. Scaffold with Astro,
> deploy a Netlify preview, and stop at production deploy approval.

**Activates:** `packages/discovery/web_handoff.py`, `apps/worker-web/`,
`apps/worker-webdeploy/`, `packages/policies/deploy_readiness.py`. Skill:
`landing-page-build`.

> Run a web UX audit on the landing page scaffold and list responsive, a11y, and
> SEO gaps before deploy.

**Activates:** `packages/web/ux_audit.py`. Skill: `web-ux-audit`.

> Wire Stripe Checkout on the validation landing page (test mode) and define paid
> validation success criteria before launch.

**Activates:** `packages/web/stripe_monetization.py`, `schemas/experiment.py`.

---

## Engineering (implement / fix code)

> Implement [feature] in [product or package]. Use a bounded Codex task packet,
> work in an isolated worktree, run lint + tests, and prepare a PR-ready diff.
> Logic changes must ship with tests.

**Activates:** `apps/worker-engineering/`, `packages/tools/codex_tools/`, worktree lifecycle, `packages/policies/testing.py`, `tests/python/`. Skills: `bounded-codex-implementation`, `codex-task-packet-library`.

> There's a bug: [describe symptom + repro]. Find the cause, fix it, add a
> regression test, and show me the diff before anything is committed.

**Activates:** engineering lane + `packages/policies/verification_loop.py`, `tests/python/`. Skill: `verification-loop`.

> Audit test coverage for [package/module] and tell me where the gaps are.

**Activates:** `tests/python/`, coverage tooling. Skill: `test-coverage-audit`.

---

## iOS (build / polish a product)

> Build and sign [product]-ios for the simulator, run the test suite, and report
> failures.

**Activates:** `apps/worker-ios/`, `packages/tools/ios_tools/xcode.py`, `products/[product]-ios/`, `infra/fastlane/`. Skill: `ios-build-and-sign`.

> Do a simulator-driven UX polish pass on [product]-ios's [screen] — capture
> screenshots, find rough edges, and propose specific fixes.

**Activates:** iOS lane + simulator capture. Skills: `simulator-driven-polish`, `ios-ui-polish-review`, `premium-feel-audit`.

---

## App Store (release)

> Prepare [product] for App Store submission: assemble metadata, check the
> release-readiness checklist, and stop at the human approval gate before any
> irreversible submit step.

**Activates:** `apps/worker-appstore/`, `packages/tools/appstore_tools/asc_api.py`, `packages/policies/release_readiness.py`, approval gate. Skills: `app-store-positioning-pack`, `ios-to-appstore-handoff`.

> Draft the App Store positioning pack (name, subtitle, keywords, description)
> for [product] targeting [niche].

**Activates:** `appstore` lane + GTM research. Skill: `app-store-positioning-pack`.

---

## Go-to-market / content

> Research the niche "[niche]" for [product] and produce a structured brief —
> audience, pain points, competitors, content gaps — and accumulate it into the
> product's niche memory.

**Activates:** `apps/worker-gtm/`, `docs/products/[product]/gtm/`. Skill: `niche-research-brief` (+ its `niche-research-memory.yaml`).

> Generate [N] content pieces for [product]'s [niche] backlog from the latest
> brief, and schedule them — everything stays behind the send gate.

**Activates:** `packages/tools/content_tools/` (gemini images, text overlay), `packages/tools/social_tools/postiz_client.py`, `packages/policies/gtm_cooldowns.py`. Skills: `content-factory`, `content-scheduler`, `social-post-safety`.

> Draft personalized creator-outreach messages for [product] — opt-in, with a
> clear unsubscribe — and hold them for review.

**Activates:** GTM lane + outreach compliance. Skill: `creator-outreach-draft`. (For a discovery validation send, this also hits `policies/discovery_gates.py` → `assert_outreach_ready`.)

---

## Goals / supervision

> Here's a founder goal: "[goal]". Decompose it into typed tasks, route each to
> the right lane, and tell me what needs my approval.

**Activates:** `apps/worker-supervisor/`, `packages/tools/supervisor/`, `GoalStore`, the queue. Skill: `supervisor-goal-decomposition`.

> What's the current state of the control plane — open goals, queued tasks,
> pending approvals?

**Activates:** `apps/api/`, `db/` stores, `scripts/runtime status`.

---

## Approvals & safety

> Walk through everything currently waiting on my approval and summarize each
> with its risk and what it unblocks.

**Activates:** `packages/policies/approvals.py`, `apps/approval-reviewer/`, `apps/api/approval_endpoint.py`. Skills: `approval-flow-review`, `approval-token-audit`. See `docs/recurring-approval-sweep.md`.

> A bulk crawl of [source] is needed for discovery. Run the bulk-crawl gate with
> me as approver and record the decision.

**Activates:** `policies/discovery_gates.py` (`assert_bulk_crawl_allowed`), `packages/discovery/gate_audit.py` → approvals store.

---

## Skills & repo hygiene

> Onboard me to [area of the repo] — what's here, the boundaries, and where to
> start.

**Activates:** Skill: `repo-onboarding`. Reads `REPO_MAP.md`, `docs/preflight-for-agents.md`.

> Find stale docs that no longer match the code and list what needs updating.

**Activates:** Skill: `stale-doc-detector`. (This is the audit behind keeping these docs honest.)

> Create a new skill for [repeatable procedure], with a contract and fixtures.

**Activates:** `skills/canonical/`, `skills/registry.yaml`. Skill: `skill-creator`.

> Take a skill stocktake — flag drift between canonical skills, adapters, and the
> registry.

**Activates:** `skills/` + `apps/worker-skill-evolution/`. Skill: `skill-stocktake`.

---

## Runtime & ops

> Start the local runtime supervisor, show status, then stop it cleanly.

**Activates:** `scripts/runtime`, `apps/runtime-supervisor/`.

> Start the control plane API and summarize `/dashboard/data` — DB backend, queue
> backend, lane depths, pending approvals, and recent events.

**Activates:** `apps/api/main.py`, `packages/dashboard/operator.py`,
`GET /dashboard/data`.

> Run the zero-setup control-loop demo end to end and the discovery demo, and
> tell me what each produced.

**Activates:** `make demo` / `scripts/demo.sh`; `scripts/discovery_demo.py`.

---

## Tips

- Name the **product** and **lane** explicitly when you can — it narrows the blast radius.
- For anything irreversible (send, deploy, submit, spend, bulk crawl), the agent should pause at an approval gate; if it doesn't, that's a bug worth flagging.
- If two skills could match your phrasing, the agent will ask which to use (the disambiguation rule in `CLAUDE.md`) — that's expected.
