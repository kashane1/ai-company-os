# Claude Cowork — Founder's Reference

*Last updated: 2026-06-01*

> **Operator commands first.** For terminal commands to run discovery, scoring,
> runtime, and validation workflows, read
> [`operator-guide.md`](operator-guide.md). This doc covers Cowork-specific
> capabilities and example prompts.

This is the one file you need for Cowork sessions. It explains what Claude Cowork
can do for `ai-company-os`, shows you the prompts that actually move the business
forward, and names the goals we are steering toward.

---

## 1. What Cowork actually is

Cowork is Claude with three things bolted on that a plain chat does not have:

1. **A workspace folder on your Mac.** Cowork can read, write, and edit any file inside `ai-company-os`. It can also create new files (Word docs, spreadsheets, slide decks, PDFs, markdown, code) and put them directly into your folders.
2. **A sandboxed Linux shell.** Cowork can run scripts, execute tests, transform data, check things with Python, and verify its own work before handing it to you.
3. **Connectors and a desktop it can see and click.** Cowork can drive Gmail, Chrome, your desktop apps, schedule recurring tasks, and hand off to specialized agents. It can also install MCP plugins so new tools become available on demand.

The important shift in mindset: you are not typing questions into a chatbot. You are directing a small company of agents that already know your repo, your products, and your goals.

## 2. What Cowork is most capable of

The short list of where Cowork earns its keep:

**Running the orchestration layer of ai-company-os.** Cowork understands `AGENTS.md`, the worker boundaries, the policies in `packages/policies/`, and the scheduled sessions under `scripts/scheduled/`. It can open a `SupervisorSession`, enqueue engineering, iOS, and GTM tasks, request approvals, and close the session with a clean audit trail.

**Running the discovery loop.** Cowork can drive the full find→score→validate path:
live discovery sweeps (`scripts/discovery_run.py`), LLM scoring
(`scripts/discovery_score.py --provider llm`), validate/build gate review, web-first
validation handoffs (`web_handoff.py`), and dossier generation. See
[`operator-guide.md`](operator-guide.md) for commands and
[`../example_prompts.md`](../example_prompts.md) for agent prompts.

**Building and shipping iOS apps.** From founder brief all the way to App Store
submission artifacts. It can also build **web landing pages** via the WEB lane
(Astro + Netlify) for faster demand validation before committing to an app.

**Executing the GTM lane autonomously.** Content drafts, voice guardrail checks, social post safety validation, ASO keyword refresh, creator outreach drafts, and Postiz scheduling once connected. Your preference here is already on file: agents should make the marketing decisions and surface summaries, not ask you to choose.

**Writing high-quality documents on demand.** Founder briefs, product briefs, MVP specs, App Store positioning packs, one-pagers, internal memos, spreadsheets for budgets or models, slide decks for pitches, PDFs for contracts. The skills in `/mnt/.claude/skills/` (`docx`, `xlsx`, `pptx`, `pdf`) kick in automatically when the format is right.

**Observing the platform and catching failures.** The observability rollup redacts credentials and surfaces lane health. The failure-mode-regression skill turns every failure into a reusable fixture so the same bug does not bite twice.

**Scheduled, unattended work.** Morning briefing at 07:30, approval sweep every 15 minutes, evening close at 19:00, Friday weekly digest. You wake up to a summary. You do not babysit the machine.

**Reading your inbox, calendar, and Slack.** Via Gmail MCP and other connectors. Cowork can draft replies, file things, and tell you what is actually urgent.

## 3. Example prompts you can send right now

Copy any of these. They are written the way the agents expect and will usually produce something useful without clarification.

### Discovery and niche research prompts

- "Run `discovery_run.py start --query '<niche>'` then score with the LLM analyst and show me the top 5 wedges with advance/hold reasons."
- "Opportunity `[opp_id]` cleared the validate gate — create a web-first validation handoff and scaffold a landing page."
- "Research the niche '[niche]' for a new product and produce a structured brief under `docs/products/[product-id]/gtm/`."
- "Score this wedge by hand against the 12-signal scorecard and tell me what's missing before it can advance."

### Day-to-day operating prompts

- "Run the morning briefing now and save it to `state/logs/briefings/`."
- "Show me pending approvals older than 30 minutes and their P0 status."
- "Close out today's session — summarize what the engineering, iOS, and GTM lanes did and append it to today's log."
- "Sweep approvals and auto-approve anything non-P0 that is stale and low risk."
- "Rebuild the observability rollup and tell me if any lane is blocked."

### Product and strategy prompts (strategic tasks)

- "Validate the full product-artifact chain for `catchbook` and list any missing parent references."
- "Refresh the App Store positioning pack for catchbook based on the latest mvp-spec and monetization strategy."
- "Draft a founder-brief intake for a new product idea: a private journaling app for runners. Put it under `docs/products/runner-journal/`."
- "Review my latest product brief and tell me the three weakest assumptions."
- "Decompose this goal into worker tasks: launch catchbook to TestFlight by end of April 2026."

### Engineering and iOS prompts

- "Run a bounded Codex implementation task to fix the insight-rules bug I described in the backlog item #42. Open a worktree, run tests, and request review."
- "Review the catchbook iOS code for UI polish issues using the `ios-ui-polish-review` skill. Focus on CatchEntryView."
- "Prepare the iOS-to-App-Store handoff for the current build and check the submission checklist for gaps."
- "Run the full test suite for catchbook-ios and show me just the failures, grouped by failure_code."
- "Find every TODO in the catchbook repo that references monetization and group them by file."

### GTM and marketing prompts

- "Generate a week of TikTok content drafts for catchbook, run them through the voice guardrail, and schedule the safe ones via Postiz. Surface only a summary."
- "Refresh the ASO keywords for catchbook, pick the top 20 by estimated impact, and update the metadata draft."
- "Draft creator outreach emails to five fishing-niche TikTok creators under 100k followers and save them as Gmail drafts."
- "Review the last 14 days of GTM activity and tell me what is working, what is not, and what to change — no questions, just a decision."

### Document and deliverable prompts

- "Create a one-page pitch deck for an investor meeting about ai-company-os. Save it as a .pptx in the workspace folder."
- "Turn `docs/products/catchbook/founder-brief.md` into a polished Word doc with a cover page and table of contents."
- "Build a spreadsheet that models catchbook ARR at $4.99/month with churn scenarios of 5%, 8%, and 12%."
- "Read this contract PDF and summarize the parts I should push back on."
- "Write a weekly investor update email based on this week's activity and save it as a Gmail draft."

### Research and knowledge prompts

- "Research current App Store guidelines for fishing apps and note anything that might trigger a rejection on catchbook."
- "Find the three most successful solo-indie iOS launches of the last 12 months and tell me what they did for their first 100 users."
- "Summarize the Apple `StoreKit 2` best practices and flag anything our current implementation misses."

### Inbox and calendar prompts

- "Scan my Gmail for anything that looks like it needs a reply today, rank by urgency, and draft replies for the top five."
- "What meetings do I have this week that I should prep for? For each, draft a one-paragraph agenda."
- "Search my email for every message from Apple Developer Relations in the last 90 days and summarize."

### Self-improvement prompts for the platform

- "Audit `skills/registry.yaml` and tell me which skills still have `fixture_status: missing`."
- "Run the skill-intake validator on every canonical skill and list any that fail the ten-item checklist."
- "Look at the last week of `task_result_rejected` events and tell me which failure code is the most common. Then write a regression fixture for it."

## 4. Recommended goals for the AI company

These are the goals I think we should be aiming at. They are ordered so that each one unlocks the next.

**Goal 1 — Catchbook on the App Store, earning money.** The whole system exists to prove that one founder plus Cowork can ship and sell an iOS product. Until catchbook is live with paying users, nothing else really matters. Success looks like: approved by App Store review, monetization wired through RevenueCat, first 100 paying subscribers.

**Goal 2 — Unattended weekday operation.** Morning briefing, approval sweep, evening close, and weekly digest all run without you having to step in. You read the briefing with coffee, approve one or two things, and the agents do the rest. Success looks like: five consecutive workdays where your only action is reviewing summaries and pressing approve.

**Goal 3 — Failure learning loop closing itself.** Every production failure becomes a fixture, every fixture becomes a test, and the same class of failure never happens twice. Success looks like: `capture_pipeline_self_failure` stays at zero for a month, and the failure-mode fixture index grows but repeat counts stay flat.

**Goal 4 — Second product via discovery.** Point the discovery loop at a new niche,
validate with a web landing page, and only commit to a full iOS build for wedges
that convert. Success looks like: discover → score → validate → build using the
operator CLIs and agent prompts, with materially less founder input than catchbook
needed.

**Goal 5 — GTM agents that make decisions on their own.** The marketing lane should run as a closed loop: decide, post, measure, adjust. You should not be choosing which TikTok script to publish. Success looks like: a full week of GTM activity where you never answered a "which option do you prefer" question, and the reported metrics are still trending up.

**Goal 6 — Scale infrastructure when needed.** Postgres, Redis, and the operator
dashboard are already available (`docs/local-dev.md`). Wire them when running
multiple products in parallel; keep SQLite for single-product local use until then.

## 5. How to use this doc

When you sit down at the Mac, read the morning briefing first and this doc second (or not at all if you remember the shape of it). When you want to do something and are not sure if Cowork can, come back here and scan the prompts section for the closest match. Copy it, tweak the specifics, send it. If it turns out Cowork cannot do the thing yet, tell me and we will either install a plugin, build a new skill, or write a new strategic task type for it.

The rule I would stick to: if you find yourself doing the same manual thing twice, that is a signal to ask Cowork to automate it. The platform is designed to absorb that work.
