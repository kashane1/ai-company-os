#!/bin/sh
# Daily price refresh for the Pokemon TCG screener. Driven by
# com.ai-company-os.tcg-app-daily-refresh.plist at 06:00 local time.
#
# This runs `ingest refresh` + `ingest metrics` rather than `ingest daily`.
# `daily` first retries every missing archive day, and tcgcsv withdrew the price
# archive in 2026 (HTTP 403 on /archive/, all dates). That retry list grows by one
# day every day and every request in it is doomed, so a scheduled `daily` would
# send an ever-larger pile of failing requests to a host that explicitly asked
# callers to reduce bandwidth. `refresh` + `metrics` is what `daily` does minus
# that catch-up. If the archive ever comes back, switch this to `ingest daily`.
#
# Every run now matters more than it used to: with the archive gone, a day that is
# not captured live is lost permanently, so failures exit non-zero and say why.
set -eu

PRODUCT_DIR=/Users/kashane/dev/ai-company-os/products/pokemon-tcg-search
PYTHON="$PRODUCT_DIR/.venv/bin/python"

cd "$PRODUCT_DIR"

echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') daily refresh starting ==="

if [ ! -x "$PYTHON" ]; then
  echo "FATAL: no venv interpreter at $PYTHON - run 'make setup' in $PRODUCT_DIR" >&2
  exit 1
fi

# A venv broken by a Homebrew Python upgrade segfaults on import rather than
# raising, which is silent in a log full of successful-looking lines. Prove the
# package loads before believing anything else this script reports.
if ! "$PYTHON" -c 'import ingest, py7zr, httpx' >/dev/null 2>&1; then
  echo "FATAL: the venv at $PYTHON cannot import its dependencies (it may be" >&2
  echo "       segfaulting after an OS or Homebrew Python upgrade)." >&2
  echo "       Fix: rm -rf '$PRODUCT_DIR/.venv' && make -C '$PRODUCT_DIR' setup" >&2
  exit 1
fi

status=0
"$PYTHON" -m ingest refresh || status=$?
if [ "$status" -ne 0 ]; then
  echo "FATAL: live price refresh failed (exit $status) - no prices recorded for today," >&2
  echo "       and with the archive gone this day cannot be backfilled later." >&2
  exit "$status"
fi

"$PYTHON" -m ingest metrics || status=$?
if [ "$status" -ne 0 ]; then
  echo "FATAL: metrics rebuild failed (exit $status) - today's prices are stored," >&2
  echo "       but the screener still serves yesterday's numbers." >&2
  exit "$status"
fi

echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') daily refresh complete ==="
