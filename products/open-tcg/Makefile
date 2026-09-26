PYTHON := ./.venv/bin/python

.PHONY: setup test sync calendar events sources backfill stream feed episodes scorecard

setup:
	python3 -m venv .venv
	./.venv/bin/pip install --quiet --upgrade pip
	./.venv/bin/pip install --quiet httpx websockets pytest
	@echo "setup complete — next: make sync"

test:
	$(PYTHON) -m pytest

# Run every enabled poll source once (tcgcsv, Southern Hobby, PokeBeach).
sync:
	$(PYTHON) -m radar sync

calendar:
	$(PYTHON) -m radar calendar

events:
	$(PYTHON) -m radar events

sources:
	$(PYTHON) -m radar sources

backfill:
	$(PYTHON) -m radar backfill

# Follow Bluesky restock accounts live (Ctrl-C to stop).
stream:
	$(PYTHON) -m radar stream

feed:
	$(PYTHON) -m radar feed

episodes:
	$(PYTHON) -m radar episodes

scorecard:
	$(PYTHON) -m radar scorecard
