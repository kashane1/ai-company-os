PYTHON := ./.venv/bin/python
PORT   ?= 8787

.PHONY: setup build catalog backfill metrics daily serve test status clean-db

setup:
	python3 -m venv .venv
	./.venv/bin/pip install --quiet --upgrade pip
	./.venv/bin/pip install --quiet httpx py7zr fastapi "uvicorn[standard]" pytest
	@echo "setup complete — next: make build"

# Full cold build. The backfill dominates (~15 minutes) and is resumable.
build: catalog backfill metrics
	@$(PYTHON) -m ingest status

catalog:
	$(PYTHON) -m ingest sync-catalog

backfill:
	$(PYTHON) -m ingest backfill

metrics:
	$(PYTHON) -m ingest metrics

# Nightly refresh: catch up archives, pull live prices, rebuild metrics.
daily:
	$(PYTHON) -m ingest daily

serve:
	./.venv/bin/uvicorn api.main:app --reload --port $(PORT)

test:
	$(PYTHON) -m pytest

status:
	$(PYTHON) -m ingest status

# Drops the database only. The catalog re-syncs in seconds; the backfill does not.
clean-db:
	rm -f data/pokemon.db data/pokemon.db-wal data/pokemon.db-shm
