#!/usr/bin/env bash
# Scheduled lead-pipeline monitor (hosting "contact-form monitoring" SLA + the
# agency's own funnel). Drains the Netlify Blobs lead stores, then runs the
# combined health check. Wired by infra/launchd/com.ai-company-os.lead-health.plist.
#
# Usage:
#   infra/scripts/check-lead-health.sh
#
# Exit code mirrors the worst verdict (0 ok, 1 warn, 2 alert) so launchd logs it.
# Drains are best-effort (|| true): a transport hiccup must not skip the check on
# already-drained data.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "${REPO_ROOT}"

TODAY="$(date +%F)"

echo "[lead-health] $(date -u +%FT%TZ) draining funnel + client lead stores"
node scripts/web/pull-inbound.mjs || echo "[lead-health] pull-inbound failed (continuing)"
node scripts/web/pull-leads.mjs || echo "[lead-health] pull-leads failed (continuing)"

echo "[lead-health] assessing as-of ${TODAY}"
python3 scripts/agency/check_all_lead_health.py --as-of "${TODAY}"
