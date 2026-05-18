.PHONY: demo test test-python

# Zero-dependency end-to-end demo: goal -> task -> execute -> validate
# -> human approval gate -> structured audit artifact. No Postgres,
# Redis, Codex, network, or Mac runtime required.
demo:
	./scripts/demo.sh

test: test-python

test-python:
	./scripts/test_python.sh
