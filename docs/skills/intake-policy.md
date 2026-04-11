# Skill Intake Policy

*Phase 5.5 of the Claude orchestrator readiness plan.*

Every new skill — whether authored internally or vendored from an
external repo — must pass this ten-item checklist **before** it lands
in `skills/registry.yaml`. External skills carry additional risk
because they may assume a runtime, embed secrets, or invoke tools we
do not wire in. The intake review is non-negotiable.

## Checklist

1. **Canonical definition present.** `skill.md` exists at
   `skills/canonical/<id>/skill.md` with `id`, `name`, `purpose`,
   `owner_agent`, `target_runtimes`, and `kind` front-matter fields.
2. **Contract declared.** `contract.yaml` declares typed `inputs:` and
   `outputs:`. Every input the validator or agent touches is listed.
3. **Validator vs. agentic kind selected correctly.** Synchronous
   hot-path skills are `kind: validator` and expose a pure `run(payload)`
   function; agentic skills are `kind: agentic` and load via
   `load_agentic`.
4. **Fixture suite.** At least three fixtures under `fixtures/`:
   `happy_path`, one `boundary` case, one `adversarial` case. Each
   fixture includes its own `expected` block.
5. **`fixture_status: passing` only after the eval harness proves it.**
   Run `infra/scripts/eval-skills.sh <skill-id>` locally. Do not
   promote the registry entry until it exits 0.
6. **Secret scan.** `gitleaks detect --no-banner --redact --config
   .gitleaks.toml` must pass against the new files. No real
   credentials, tokens, or `.env` fragments.
7. **Redaction contract.** If the skill reads or writes log excerpts,
   it must route them through
   `packages.tools.observability.redaction.redact` before they leave
   the function boundary.
8. **Edit boundaries declared.** For agentic skills, `skill.md` lists
   `allowed_edit_boundaries:` and `forbidden_areas:`. The worker runtime
   refuses to apply edits outside the allowed list.
9. **External-source provenance.** `source:` is either `internal` or
   `external:<repo>@<commit>`. External skills must pin a commit, not a
   branch. The review recorded in `docs/skills/intake-reviews/<id>.md`
   (author, license, date of inspection).
10. **Registry entry added last.** `registry.yaml` gets updated only
    after items 1–9 are green. The registry is the authoritative index
    the loader trusts, so an unvalidated entry here would bypass the
    gate.

## Review log

When intake is complete, append a one-line entry to this file under
the `## Log` section below: `- <date> · <skill-id> · <reviewer> ·
<outcome>`.

## Log

<!-- append entries here -->
