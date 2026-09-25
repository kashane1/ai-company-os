# Employer experience audit

Date: September 8, 2026.

## Scope

Reviewed the path from the repository README to the employer guide, evaluator
walkthrough, fixtures, approval/schema code, linked reliability/product guides,
and three product READMEs. Ran the documented commands in isolated copies.
An independent reviewer checked claims against source; focused workers handled
executable-check and App Store evidence fixes.

The starting checkout was `789e9c6` on `codex/homefromworking-days-1-21`.
Remote `main` was `61fb9dc`; the initial employer guide, walkthrough, and
executable evaluator matched that revision. Existing local work, including
HomeFromWorking changes, was preserved. Verification copies excluded local
credentials and unrelated uncommitted implementation.

This is an audit of the employer evaluation path, not a complete security,
privacy, production-readiness, or iOS release audit.

## Findings addressed

| Finding | Change |
|---|---|
| Entry pages led with old counts, an obsolete two-month timeline, and unsupported claims that all products shipped | Replaced with stable project context, explicit author/agent roles, and source-backed product descriptions |
| Reviewers had to install software before seeing the engineering | Added a five-minute GitHub-only path with specific code, tests, and questions to assess |
| Fixture construction was described as executing an agent and obtaining human approval | Labeled fixtures in prose, demo output, and test comments; separated illustration from policy/endpoint testing |
| Evaluator checked a few JSON keys and regenerated before validating, masking drift | Added real-schema round trips before and after regeneration, with regression coverage |
| Broken links outside the old five-doc path check were invisible | Added curated employer/product Markdown-link checks; fixed the Life Clock source link and seven archived document references |
| Test commands depended on the caller's working directory and inconsistent interpreter selection | Made scripts honor `PYTHON_BIN`, quote paths, use the repository root, and report prerequisites |
| Package metadata allowed Python 3.10 while platform imports require `datetime.UTC` | Raised the application minimum to 3.11; documented that the standalone fixture can still use 3.10 |
| Fast check tested fixtures/enum parsing without actual approval behavior | Included approval rules, token/API integration, and audit write-failure tests |
| Full baseline suite had five failures | Updated worker-list expectations and the landing form's component location while retaining behavior assertions |
| Blocked App Store actions wrote completed artifacts; artifacts depended on process cwd | Persist actual status under configured runtime paths and use completion metadata only for completed work |
| A release action could accept an unrelated approved record or silently accept an unknown action | Bind approvals to type, subject, release, and action; reject missing/mismatched approvals and unknown actions; preserve the approval ID in successful results |
| Supporting guides overstated release automation, replay, redaction, scheduler evidence, and independent MFA | Narrowed each claim to implementation evidence and documented remaining limits |
| Life Clock and After Plans READMEs contained stale navigation/status | Linked reviewable source/tests and described After Plans' implemented optional Supabase adapter and offline default |
| CI did not run the employer command without installed dependencies | Added the default evaluator command before package installation in Python CI |

## Verification

Baseline, isolated committed snapshot with the existing Python environment:
`5 failed, 1838 passed, 1 skipped`. All five failures were reproduced and traced
to stale test assumptions before correction.

Integrated verification used a fresh Python 3.12 virtual environment installed
with `.venv/bin/python -m pip install -e ".[test]"`:

- Default evaluator before package installation: passed; 108 local links and
  three schema round trips, with no third-party dependencies.
- `./scripts/evaluator_check.sh --with-tests`: 21 passed.
- Full check with `PYTHON_COVERAGE_MIN=55` and a fresh `COVERAGE_FILE`:
  **1852 passed, 1 skipped, 3 warnings; 85.31% coverage; exit 0.**
- Shell syntax, the existing root-doc path check (173 references), employer
  validator, examples-index freshness, and `git diff --check`: passed.
- A nested evaluator regression test initially caused incompatible coverage
  shards. It now strips inherited pytest-cov auto-start settings; the final
  full run includes the regression and completes coverage successfully.
- The final independent review found no additional blocking issues within the
  audited path. Dependency deprecation warnings and an existing pytest
  collection warning remain; no iOS build was run.

The clean verification snapshot includes committed files plus the audit edits,
not unrelated uncommitted application changes. This result therefore does not
claim that every in-progress change in the shared checkout was tested.

## Publication checks

The publication checkout starts from remote `main` (`61fb9dc`) and excludes the
unrelated local HomeFromWorking planning commit and work in progress. After
adding the approved license exception, the default evaluator passes with 109
local links; the root-doc path check passes with 166 references. The Python
change includes matching tests under the repository's tests-with-code policy.

Additional maintenance checks expose existing repository debt: 220 oversized
tracked-state files, six large documents missing a summary, and six plans
missing from the plans index. The affected state, plan, and agent-model files
are unchanged by this publication. These checks remain failing; passing Python
tests and employer-path validation do not mean every CI job is green.

## License resolution and remaining implementation gaps

- **License conflict resolved with author approval.** `LICENSE` now permits
  prospective employers to clone the repository and run the documented
  evaluator, demo, and tests locally for evaluation. Deployment, redistribution,
  and product reuse remain outside that permission.
- **External App Store release remains manual.** The worker models local state;
  it does not call App Store Connect or the existing release-readiness policy.
  The evaluator documents this rather than treating local success as shipment.
- **Trusted local API boundary.** The code has direct approval-decision routes;
  the P0 second confirmation is not independent MFA. No internet-facing security
  claim is made.
- **Tracked operator artifacts remain.** The existing tree mixes runtime paths
  with tracked HomeFromWorking artifacts. Broadly moving or untracking them would
  affect active workflows; this audit documents the inconsistency rather than
  silently deleting evidence or assets.
- **Verification scope.** iOS builds, live services, model execution, scheduler
  activity, release status, and raw runtime-log redaction were not verified.
  The evaluator's local-link check covers file targets, not remote availability
  or Markdown fragments.

## Publication

The author approved the local-evaluation license exception and publication to
GitHub. The publication commit contains the employer audit changes and license
resolution; unrelated HomeFromWorking work is excluded.
