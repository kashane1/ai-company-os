# Evaluator Walkthrough

This is the shortest practical path for evaluating `ai-company-os` as an
hiring signal without reading the whole repo.

## If you have 5 minutes

1. Read [`FOR-EMPLOYERS.md`](FOR-EMPLOYERS.md).
2. Run:

   ```bash
   ./scripts/evaluator_check.sh
   ```

3. Open these files:
   - [`../packages/schemas/`](../packages/schemas/)
   - [`../packages/policies/approvals.py`](../packages/policies/approvals.py)
   - [`../apps/api/approval_endpoint.py`](../apps/api/approval_endpoint.py)
   - [`examples/sample-task-run.json`](examples/sample-task-run.json)

Expected outcome:

- the demo runs locally with no external services
- `docs/examples/` is refreshed with schema-faithful artifacts
- the approval gate is explicit in code, not only described in prose

## If you have 20 minutes

1. Follow the 5-minute path.
2. Inspect the recurring approval workflow:
   - [`recurring-approval-sweep.md`](recurring-approval-sweep.md)
   - [`../scripts/scheduled/approval_sweep_session.md`](../scripts/scheduled/approval_sweep_session.md)
3. Inspect the product outputs:
   - [`../products/life-clock-ios/README.md`](../products/life-clock-ios/README.md)
   - [`../products/catchbook-ios/README.md`](../products/catchbook-ios/README.md)
   - [`../products/after-plans-ios/README.md`](../products/after-plans-ios/README.md)
4. Run:

   ```bash
   git log --oneline | head
   ```

Expected outcome:

- the repo reads as a control plane plus real product outputs
- the recurring approval story is concrete but not overclaimed
- commit history looks like an active parallel-agent workflow, not padded prose

## If you have 60 minutes

1. Follow the 20-minute path.
2. Run the full verified Python suite:

   ```bash
   ./scripts/test_python.sh
   ```

3. Inspect a full traced workflow and reliability evidence:
   - [`flagship-simulator-driven-polish.md`](flagship-simulator-driven-polish.md)
   - [`reliability-lessons.md`](reliability-lessons.md)
4. Inspect the architecture and operating model:
   - [`architecture.md`](architecture.md)
   - [`agent-model.md`](agent-model.md)
   - [`operating-model.md`](operating-model.md)

Expected outcome:

- the platform boundaries are visible in code and docs
- tests back the main control-plane claims
- the product roots and workflow artifacts make the repo feel like a working
  system rather than a prompt experiment

## Exact commands

Zero-setup check:

```bash
./scripts/evaluator_check.sh
```

Zero-setup demo only:

```bash
make demo
```

Optional fast test subset (requires test dependencies):

```bash
./scripts/evaluator_check.sh --with-tests
```

Full Python suite:

```bash
./scripts/test_python.sh
```
