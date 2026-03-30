# Local Development

`ai-company-os` is designed for an always-on Mac, not a generic cloud runtime.

This document captures the local assumptions that matter for v1.

## Host Assumptions

Primary target:

- MacBook Air M1
- macOS as the host runtime
- long-lived local processes
- local Codex CLI usage

Why macOS matters:

- iOS development requires Xcode and simulator tooling
- App Store automation is easier when Apple tooling stays local
- the operating model assumes local worktrees and local state directories

## Python Setup

V1 is Python-first.

Recommended baseline:

- Python 3.12+
- a local virtual environment

Example:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[test]"
```

Run the Python test lane with:

```bash
./scripts/test_python.sh
```

The Python test harness isolates runtime state by setting `AI_COMPANY_OS_REPO_ROOT` to a temporary repo root. That keeps test writes out of the real `state/` tree while preserving production defaults.

## Postgres And Redis

The intended runtime uses:

- Postgres for durable memory and state
- Redis for queueing and coordination

V1 does not fully wire them yet, but future implementation should assume both are local development dependencies.

## Codex CLI

Assumptions:

- Codex CLI runs locally on the Mac
- authentication is handled through ChatGPT
- engineering workers invoke Codex rather than embedding repo mutation logic in prompts alone

The platform should prepare task packets and constraints before invoking Codex.

## Apple Tooling

If you are working on the iOS or App Store lanes, local tooling will eventually include:

- Xcode
- iOS Simulator
- Apple developer credentials
- App Store Connect access
- Fastlane or equivalent release helpers if the project later adopts them

Keep iOS engineering and App Store release automation as separate concerns even when both depend on Apple tooling.

Run the iOS test lane with:

```bash
./scripts/test_ios.sh
```

This regenerates the Xcode project from `products/fishing-logbook-ios/project.yml`, runs `xcodebuild test`, and reports target coverage with `xccov`.

## Local State Directories

Runtime state belongs under `state/`.

Important paths:

- `state/repos/`
- `state/worktrees/`
- `state/artifacts/`
- `state/checkpoints/`
- `state/logs/`

Do not treat these as source directories.

## Current Scaffold Checks

The current repo is still in scaffold mode, but these entrypoints should run:

```bash
python3 apps/api/main.py
python3 apps/worker-supervisor/main.py
```

These are verification hooks, not the final runtime model.

## Testing And Coverage

The staged rollout works like this:

- Stage 0: test failures fail locally and in CI, coverage is reported, thresholds are advisory
- Active now: `PYTHON_COVERAGE_MIN=55` is enforced in CI
- Current iOS status: coverage is still advisory while the lane builds headroom above the soft floor
- Stage 1 target: enable `IOS_COVERAGE_MIN=20` once repeated local runs show stable coverage with comfortable margin
- Stage 2: ratchet to `PYTHON_COVERAGE_MIN=70` and `IOS_COVERAGE_MIN=35`

Coverage failures should be interpreted as a signal to add tests for deterministic logic and persistence/orchestration flows first. UI-heavy snapshot and automation suites are intentionally deferred in this repo's first testing phase.
