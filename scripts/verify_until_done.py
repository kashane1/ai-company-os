"""Verify all remaining S_source_candidate records via Brave until done or out of credits.

Stops immediately on the first quota/auth wall (HTTP 402/429/401) so a credit
exhaustion does not burn thousands of failing calls. Each record is saved as it
is verified, so the run is fully resumable — re-running picks up where it left off.
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.prospecting.storage import ProspectRepository
from packages.prospecting.web_presence import (
    BraveSearchVerifier,
    SearchProviderError,
    verify_record_web_presence,
)
from packages.schemas.prospect import WebVerifyVerdict

QUOTA_MARKERS = ("402", "429", "401", "Payment Required", "Too Many Requests", "Unauthorized")
COHORT = "S_source_candidate"
PROGRESS_EVERY = 50


def main() -> int:
    repo = ProspectRepository()
    verifier = BraveSearchVerifier(count=10)

    pending = [
        r
        for r in repo.list()
        if r.composite_cohort == COHORT
        and r.web_verify_verdict is WebVerifyVerdict.UNVERIFIED
    ]
    pending.sort(key=lambda r: (-r.priority_score, r.display_name.lower()))
    total = len(pending)
    print(f"Pending unverified {COHORT}: {total}", flush=True)

    counts: Counter[str] = Counter()
    errors = 0
    stopped_reason = "completed"
    started = time.monotonic()

    for i, record in enumerate(pending, 1):
        try:
            updated = verify_record_web_presence(record, verifier)
        except SearchProviderError as exc:
            msg = str(exc)
            if any(m in msg for m in QUOTA_MARKERS):
                stopped_reason = f"quota/auth wall hit at record {i}: {msg[:160]}"
                break
            errors += 1
            if errors <= 10:
                print(f"  transient error [{record.place_id}]: {msg[:120]}", flush=True)
            continue
        except Exception as exc:  # noqa: BLE001
            errors += 1
            if errors <= 10:
                print(f"  unexpected error [{record.place_id}]: {exc}", flush=True)
            continue
        repo.save(updated)
        counts[updated.web_verify_verdict.value] += 1
        if i % PROGRESS_EVERY == 0:
            qualified = counts["social_only"] + counts["marketplace_only"] + counts["none_found"]
            rate = i / max(time.monotonic() - started, 1e-9)
            print(
                f"  [{i}/{total}] verified={sum(counts.values())} "
                f"qualified={qualified} owned={counts['owned_site']} "
                f"errors={errors} ({rate:.1f}/s)",
                flush=True,
            )

    qualified = counts["social_only"] + counts["marketplace_only"] + counts["none_found"]
    print("=== DONE ===", flush=True)
    print(f"stop_reason : {stopped_reason}", flush=True)
    print(f"verified    : {sum(counts.values())}", flush=True)
    print(f"qualified   : {qualified}", flush=True)
    print(f"owned_site  : {counts['owned_site']}", flush=True)
    print(f"counts      : {dict(counts)}", flush=True)
    print(f"errors      : {errors}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
