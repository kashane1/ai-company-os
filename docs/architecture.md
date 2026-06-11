# Architecture

## Purpose

`ai-company-os` is a local-first operating system for running an AI-first or AI-only software company from an always-on Mac.

It is designed to support:

- persistent workers
- explicit task state
- policy-driven execution
- repo-based engineering workflows
- iOS development and release handling
- outreach operations with human-gated outbound contact
- human approval at high-risk boundaries
- optional remote control surfaces such as OpenClaw

This system is not a single all-powerful agent. It is a platform with orchestration, specialist workers, shared policies, and durable state.

## Core Philosophy

The architecture is built around a few key principles:

- the platform is the brain
- Codex is the engineering engine
- workers execute but do not define policy
- state is explicit and durable
- runtime data is separate from source code
- OpenClaw is optional interface only
- iOS engineering and App Store operations are separate lanes
- outreach drafting/tracking is separate from outbound sending
- synthetic-audience conversion reports are advisory agency artifacts, not launch authority

The system should remain understandable to a human engineer without prompt archaeology.

## High-Level System Model

The system has five main layers:

1. control plane
2. workers
3. managed product workspaces
4. shared platform packages
5. runtime state
6. optional interface layer

### 1. Control Plane

The control plane is responsible for coordination and visibility.

Typical components:

- API
- approvals
- task creation
- task inspection
- health checks
- release status
- webhooks
- dashboard

This is where founder intent enters the system and where oversight happens. The current repo now includes a minimal real control-plane slice for persisted goals, tasks, approvals, events, and task claims. The dashboard remains a documented future surface.

### 2. Workers

Workers are specialist execution lanes.

Each worker should:

- accept structured task input
- perform bounded work
- produce structured output
- obey shared policy rules
- leave logs and artifacts behind

Workers should not:

- invent their own authority
- own approval policy
- silently mutate unrelated parts of the system

### 3. Managed Product Workspaces

The platform can manage one or more products without turning the repo into an unstructured monolith.

For the current phase, product source lives under `products/` and product planning artifacts live under `docs/products/`.

Each product should have:

- a product registry record
- a managed source path
- durable founder-brief-to-spec artifacts
- any product-specific architecture inputs needed before implementation

### 4. Shared Platform Packages

Shared packages provide the reusable platform foundation.

Current v1 packages:

- `packages/policies`
- `packages/tools`
- `packages/schemas`
- `packages/db`
- `packages/queue`
- `packages/config`

Within `packages/tools/`, the current intended v1 namespaces are:

- `codex_tools/`
- `github_tools/`
- `ios_tools/`
- `appstore_tools/`

Likely later additions:

- memory helpers
- event routing
- observability helpers

This is the layer that prevents the platform from turning into a pile of disconnected workers.

Shared policy now also includes the tests-with-code contract. That policy is encoded in shared schema and policy modules so workers, review artifacts, and CI all evaluate the same rule instead of drifting into prompt-only enforcement.

### 5. Runtime State

Runtime state is the live operational footprint of the company OS.

Examples:

- cloned repos
- worktrees
- generated artifacts
- logs
- checkpoints
- cached context

Runtime state belongs in `state/`, not mixed into implementation folders.
Conversion Lab client run output follows the same rule:
`state/clients/<product_id>/conversion_lab/<run_id>/`.

### 6. Optional Interface Layer

An interface layer may later expose the system through chat or remote commands.

Examples:

- OpenClaw
- Telegram
- Slack
- Discord
- remote approval actions

This layer should adapt into the platform, not replace it.

## Main Components

### API

The API is the entry point for:

- goals
- tasks
- approvals
- release state
- metrics
- webhooks
- system inspection

The API should remain thin and delegate business logic to services and workers.

### Supervisor Worker

The supervisor is the coordination layer for ongoing company activity.

Responsibilities:

- inspect goals
- inspect metrics and current state
- decompose goals into tasks
- prioritize work
- route work to specialist workers
- escalate risky actions
- summarize progress and blockers

The supervisor is not a general-purpose execution worker. It coordinates, routes, and reviews.

### Engineering Worker

The engineering worker is the generic software implementation lane.

Responsibilities:

- prepare task packets
- sync repos
- create worktrees
- call Codex CLI
- validate diffs
- run tests, lint, and builds
- create commits and PRs
- report structured results

The engineering worker is responsible for controlled software execution, not product strategy or policy.

The lane also owns test execution and tests-with-code enforcement for Python-facing logic changes. That enforcement is structured, lane-aware, and persisted into task-run data.

### iOS Worker

The iOS worker is the platform-specific engineering lane for iOS work.

Responsibilities:

- perform iOS feature and bugfix implementation
- run Xcode-related tasks
- manage simulator and build workflows
- prepare release-ready artifacts
- hand off distribution-ready outputs to the App Store lane

This lane exists separately because iOS work requires platform-specific handling that should not be buried inside a general worker.

The iOS lane uses the same structured tests-with-code policy as the engineering lane, but it maps relevant code and tests to the iOS product paths instead of the Python paths.

### App Store Worker

The App Store worker handles app distribution and release operations.

Responsibilities:

- TestFlight preparation
- metadata handling
- screenshot handling
- App Store Connect workflows
- release notes drafts
- review response drafts
- submission coordination
- release-state tracking

The App Store worker is separate from the iOS worker because building an app and shipping an app are different operational concerns.

### Outreach Worker

The outreach worker is the operations lane for cold outreach around local-SMB
demo sites.

Responsibilities:

- refresh the prospect client-status ledger
- organize draft outreach artifacts
- log manual touches and follow-up dates
- reconcile replies through future approved CRM or inbox adapters

It does not send cold email, SMS, Instagram DMs, or Facebook DMs. Sending stays
human-gated until a dedicated CRM adapter and policy gate exist.

### Agency Conversion Lab

Conversion Lab is a Better Business Web capability under `packages/agency/`.
It prepares persona-backed synthetic-audience prompts, renders operator-reviewed
reports, and passes optional preflight summaries into Package C Google/Meta ad
drafts.

This is deliberately not a new orchestrator or worker lane. The reports are
advisory artifacts for conversion review: objections, trust gaps, rewrite ideas,
and recommended angles. They do not guarantee revenue and do not replace live
analytics, real customer interviews, or controlled ad experiments.

Hard boundaries remain unchanged:

- ad campaigns stay draft-only until `ad_campaign_go_live` approval passes
- spend and budget changes remain human-gated
- private customer data requires client permission before entering persona packs
- run output lives in `state/`, while reusable templates live in `docs/agency/`

## Product Registry And Artifact Chain

Products are first-class records, not implied folders.

The current platform now expects:

- a registry entry in `infra/products.json`
- a checkpoint-backed product record
- a durable artifact chain such as founder brief, product brief, MVP spec, backlog, iOS architecture, and App Store positioning
- optional product-specific contracts such as deterministic insight rules

That artifact chain is what turns founder intent into implementation-ready platform inputs.

## How Codex Fits

Codex is the engineering engine inside implementation lanes.

Codex is used for:

- code editing
- bugfixes
- feature implementation
- test changes
- refactors
- implementation summaries

Codex is not used as:

- the orchestrator
- the policy engine
- the memory store
- the task router

Codex is expected to respond inside a structured worker contract. In addition to code changes, worker runs now require explicit testing metadata so validators can determine whether lane-matching tests were added or whether a machine-readable no-test exception applies.

## Shared Testing Policy

The repo now treats testing requirements as a first-class contract.

Structured task packets include:

- `tests_required`
- `test_lane`
- `allowed_no_test_reason_codes`

Structured validator and task-run outputs include:

- `testing_policy`
- `failure_codes`
- validation checks with specific codes such as `missing_tests_for_logic_change`

The shared rule is:

- logic-bearing Python changes under `apps/` or `packages/` require created or modified tests under `tests/python/`
- logic-bearing iOS changes under `products/catchbook-ios/Sources/` require created or modified tests under `products/catchbook-ios/Tests/`
- docs-only, generated-file, visual-only non-logic, comments-only, and config-no-behavior-change cases must use explicit machine-readable exceptions when no tests are added
- `approved_followup_test_task` is valid only when the referenced task already exists in persisted task state, remains open, and matches the same lane and affected area

CI uses the same shared policy through a required `tests-with-code` job. That job always reports on the latest commit SHA and uses the GitHub event SHAs for pull-request and push diffs instead of path-filtered required workflows.
- the approval owner

The intended relationship is simple:

- the platform decides what should be built
- workers decide how to prepare and validate work
- Codex performs the coding step inside the worker boundary

## How Tasks Move Through The System

The system should operate through explicit task flow.

A typical flow looks like this:

1. A founder or system process creates a goal.
2. The supervisor inspects the goal and decomposes it into tasks.
3. Tasks are stored in the database and placed on the queue.
4. A worker claims a task based on type and priority.
5. The worker executes within policy constraints.
6. The worker stores results, logs, and artifacts.
7. If needed, the worker requests approval.
8. The control plane exposes current state to the founder.
9. The supervisor reacts to outputs and schedules follow-up work.

This explicit lifecycle is preferred over hidden autonomous loops.

## Example Engineering Flow

1. Supervisor creates an engineering task.
2. Engineering worker syncs the target repo.
3. Engineering worker creates an isolated worktree.
4. Worker renders a structured task packet.
5. Worker invokes Codex CLI.
6. Worker inspects the resulting diff.
7. Worker runs lint, tests, and builds.
8. Worker commits and opens a PR if validation passes.
9. Worker reports structured results to the platform.

## Example iOS Release Flow

1. Supervisor creates an `ios_release` or `appstore_submission` task.
2. iOS worker prepares release candidate artifacts.
3. App Store worker selects build state and prepares metadata.
4. App Store worker drafts release notes and review-facing content.
5. Approval is requested before final submission or public release.
6. App Store worker tracks review status and reports outcomes.

This separation keeps engineering and release operations from collapsing into the same lane.

## Approval Model

The system should support meaningful autonomy without becoming reckless.

Usually safe to automate:

- creating tasks
- generating drafts
- creating worktrees
- running tests
- opening PRs
- drafting release notes
- preparing metadata drafts
- preparing screenshots
- drafting review responses
- internal artifact generation

Usually requires approval:

- merging to protected branches
- production deploys
- destructive migrations
- pricing changes
- billing changes
- App Store submission
- App Review replies
- security-sensitive config changes
- bulk outbound communication
- high-spend changes
- domain or DNS modifications

These rules should be encoded in shared policy modules and enforced consistently.

## Data And State Model

The system should keep state explicit and queryable.

Important persistent concepts include:

- goals
- tasks
- task runs
- approvals
- events
- repos
- worktrees
- artifacts
- release candidates
- App Store submissions
- incidents
- memories
- metric snapshots

The system should be debuggable by reading state, not by guessing what an agent probably did.

## Repo And Worktree Strategy

All code-modifying work should happen against managed local repos and isolated worktrees.

Why:

- prevents repo contamination
- improves reproducibility
- makes task-level execution easier to audit
- reduces collisions between concurrent tasks

Suggested runtime layout:

- `state/repos/`
- `state/worktrees/`
- `state/artifacts/`
- `state/logs/`

## macOS As A First-Class Runtime

This system is designed with macOS in mind because:

- Codex CLI is expected to run locally
- iOS development requires macOS tooling
- Xcode and simulator workflows live on the host machine
- App Store automation is simpler when release tooling stays on macOS

The architecture should respect the host instead of pretending it is generic cloud Linux.

## OpenClaw's Role

OpenClaw is optional and external to orchestration.

OpenClaw may later provide:

- remote commands
- founder chat interface
- notifications
- approvals
- quick status queries

OpenClaw should not provide:

- task routing
- policy ownership
- durable memory
- worker control logic
- repo lifecycle management

The system must remain coherent even if OpenClaw is never added.

## V1 Scope

V1 includes:

- API
- supervisor worker
- engineering worker
- iOS worker
- App Store worker
- shared packages for policies, tools, db, queue, schemas, and config
- runtime state directories
- foundational documentation

The larger mock layout remains a future map, but these stay deliberately out of the first implementation pass:

- support, growth, research, and ops workers
- dashboard implementation
- OpenClaw bridge code
- larger memory and event systems
- eval infrastructure beyond narrow validation needs

V1 does not need to fully implement:

- growth worker
- research worker
- ops worker
- complex memory retrieval systems
- remote chat interface
- advanced event automation
- large evaluation harnesses

The goal of v1 is a clean, durable skeleton with one real end-to-end product delivery path.

## Architecture Boundaries

To keep the system healthy, preserve these boundaries:

1. Workers do not own policy.
2. Codex does not own orchestration.
3. OpenClaw does not own the platform.
4. Runtime state does not live in source directories.
5. iOS implementation and App Store release are separate lanes.

## Success Criteria

The architecture is working when:

- founder goals become structured tasks
- tasks are routed clearly
- workers operate within clear scope
- Codex performs engineering inside bounded flows
- approvals gate irreversible actions
- iOS and App Store work move through separate lanes
- the system remains readable and maintainable by a human engineer

## Discovery layer (front of the loop)

The layers above take a founder *goal* and build/ship it. The discovery layer
(`packages/discovery/`) is the step before the goal exists — finding and
validating *what* to build — added as a shared platform package, not a new
orchestrator:

- **Connectors** (`connectors/`) turn sources (Hacker News, GitHub, Reddit) into
  raw signals behind one contract, with robots.txt + per-domain rate limiting
  enforced in one place.
- The **opportunity inbox** dedups signals into scored `OpportunityRecord`s;
  storage is pluggable (JSON by default, the control-plane DB when configured).
- **Scoring** (the 12-signal scorecard) is pure math; the **validate** and
  **build** gates live in `packages/policies/discovery_gates.py` (policy is owned
  by policies, not tools). The build gate refuses any opportunity that hasn't
  passed a validation experiment.
- Discovery runs are **operator-triggered and stoppable** (`run.py` +
  `scripts/discovery_run.py`), mirroring the runtime supervisor's start/stop
  surface — not a background crawler.
- **Operator cockpit** — unified read-only dashboard at `GET /dashboard` +
  `/dashboard/data` (`packages/dashboard/operator.py`): DB/queue backend health,
  per-lane queue depth, recent tasks, approvals, and events. Discovery has its
  own panel at `/discovery` (`packages/discovery/dashboard.py`).
- **Web-first validation** (`web_handoff.py`) routes a cleared wedge to the WEB
  lane first — a landing page is both the cheapest demand test and the experiment
  the build gate reads. iOS/full-app builds come after conversion.

The durable assets are the schemas, the scoring weights, the playbooks, and the
accumulated outcomes — not any one source. Operator commands:
[`founder/operator-guide.md`](founder/operator-guide.md). Deep dive:
[`founder/discovery-guide.md`](founder/discovery-guide.md),
[`founder/founder-os.md`](founder/founder-os.md).

## Summary

This architecture is intended to produce a company OS that is:

- explicit
- modular
- policy-driven
- locally operable
- safe to extend
- capable of evolving into a real AI-only company runtime

The system should feel like a disciplined operating platform, not a pile of prompts.
