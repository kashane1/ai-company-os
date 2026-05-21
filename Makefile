.PHONY: demo test test-python doctor audit handoff

# Zero-dependency end-to-end demo: goal -> task -> execute -> validate
# -> human approval gate -> structured audit artifact. No Postgres,
# Redis, Codex, network, or Mac runtime required.
demo:
	./scripts/demo.sh

test: test-python

test-python:
	./scripts/test_python.sh

# Local-dev preflight checklist. Read-only; points at REPO_MAP.md.
doctor:
	@echo "ai-company-os — local preflight"
	@echo
	@echo "Read first:"
	@echo "  - REPO_MAP.md"
	@echo "  - docs/preflight-for-agents.md"
	@echo "  - CLAUDE.md / AGENTS.md"
	@echo "  - docs/skills-index.md"
	@echo
	@echo "Local checks (run manually):"
	@echo "  - python3 --version            (expect 3.12+)"
	@echo "  - test -d .venv                 (recreate if missing)"
	@echo "  - .venv/bin/python -c 'import yaml'   (pyyaml needed for enqueue scripts)"
	@echo "  - which codex                   (for Codex CLI integration)"
	@echo "  - launchctl list | grep ai-company-os.runtime-supervisor   (optional)"
	@echo
	@echo "Demo + tests:"
	@echo "  make demo"
	@echo "  make test"
	@echo
	@echo "Doc-path audit:"
	@echo "  make audit"

# Read-only doc-path drift check across the docs an agent reads first.
audit:
	./scripts/ci/check_doc_paths.sh

# Print the handoff convention. Read-only.
handoff:
	@echo "Session handoff convention"
	@echo
	@echo "  docs/handoffs/YYYY-MM-DD-<short-slug>.md"
	@echo
	@echo "Required sections:"
	@echo "  - What changed"
	@echo "  - What is open"
	@echo "  - What is blocked"
	@echo "  - What is stale"
	@echo "  - Files touched"
	@echo "  - Validation run"
	@echo "  - Exact next action"
	@echo "  - Resume prompt (optional)"
	@echo
	@echo "Full convention: docs/handoffs/INDEX.md"
