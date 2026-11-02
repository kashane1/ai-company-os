PYTHON := python3

.PHONY: init test demo status clean-db

# Creates data/inventory.db and seeds reference data. Safe to re-run.
init:
	$(PYTHON) -m inventory init

test:
	$(PYTHON) -m pytest -q

status:
	$(PYTHON) -m inventory status

# Drops the INVENTORY database only — this is your source of truth and nothing
# can rebuild it. The catalog in ../pokemon-tcg-search is untouched.
clean-db:
	@echo "This deletes what you own, what you paid and where it is."
	@read -p "Type 'delete' to confirm: " ok && [ "$$ok" = "delete" ]
	rm -f data/inventory.db data/inventory.db-wal data/inventory.db-shm

# Phone-as-camera capture. Open the printed LAN address on your phone.
CAPTURE_PORT ?= 8788
capture:
	@$(PYTHON) -c "from inventory.capture_app import _lan_url; print('Open on your phone: ' + _lan_url($(CAPTURE_PORT)))"
	$(PYTHON) -m uvicorn inventory.capture_app:app --host 0.0.0.0 --port $(CAPTURE_PORT)
