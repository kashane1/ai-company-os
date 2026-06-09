.PHONY: demo test test-python doctor audit handoff archive-plans doc-index tokens-check skills-sync premium

# Zero-dependency end-to-end demo: goal -> task -> execute -> validate
# -> human approval gate -> structured audit artifact. No Postgres,
# Redis, Codex, network, or Mac runtime required.
demo:
	./scripts/demo.sh

test: test-python

test-python:
	./scripts/test_python.sh

# Premium website factory — run the autonomous design loop for a niche.
#   make premium NICHE="med spa" [TARGET=products/better-business-web/portfolio/flagship]
# Needs npm (build) + GEMINI_API_KEY (independent judge). The loop builds → shoots →
# judges → revises until the visual gate passes or it halts to the best build; a pass
# still needs founder sign-off (it never auto-ships).
PREMIUM_PY ?= $(if $(wildcard .venv/bin/python3),.venv/bin/python3,python3)
premium:
	@test -n "$(NICHE)" || { echo "usage: make premium NICHE=\"med spa\" [TARGET=...]"; exit 2; }
	@$(PREMIUM_PY) -c "import json; from packages.web.niches import niche_to_spec; print(json.dumps(niche_to_spec('$(NICHE)')))" \
	  | $(PREMIUM_PY) scripts/agency/design_loop.py run \
	      --target $(or $(TARGET),products/better-business-web/portfolio/flagship) --spec -

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
	@echo "Discovery (operator-triggered):"
	@echo "  python3 scripts/discovery_demo.py"
	@echo "  python3 scripts/discovery_run.py start --query \"<niche>\""
	@echo "  python3 scripts/discovery_score.py --top 10"
	@echo "  See docs/founder/operator-guide.md"
	@echo
	@echo "Doc-path audit:"
	@echo "  make audit"

# Read-only doc-path drift check across the docs an agent reads first.
audit:
	./scripts/ci/check_doc_paths.sh

# Token-efficiency maintenance. Move finished plans (status: completed/shipped/
# superseded/...) into docs/plans/archive/ so the working set stays small.
archive-plans:
	python3 scripts/docs/archive_plans.py

# Regenerate every auto-indexed docs directory.
doc-index:
	python3 scripts/docs/gen_doc_index.py \
	  docs/adr docs/decisions docs/founder docs/brainstorms \
	  docs/failure-modes docs/security docs/runbooks docs/skills \
	  docs/architecture docs/examples
	python3 scripts/docs/gen_doc_index.py --recursive docs/solutions docs/agency docs/research

# Aggregate token-efficiency gate (mirrors CI). Nonzero on any violation.
tokens-check:
	python3 scripts/ci/token_efficiency_check.py

# Regenerate .claude/skills/ pointers from their adapters (single source).
skills-sync:
	python3 scripts/skills/gen_project_skills.py

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
