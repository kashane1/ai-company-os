# Security and local operation

This repository is a local source-checkout application. Run the control-plane
API on loopback on a machine you control. It is not a hardened service for
untrusted tenants or internet exposure.

## Approval boundary

The platform prepares work and records approval evidence. Consequential actions
must check the stored action, subject, and reviewed inputs before execution.
Signed local confirmations expire and are consumed once; P0 actions require a
second confirmation. These are two confirmations by the local operator, not
independent MFA.

Possession of an operator capability or access to the same user's credential
stores and runtime files carries authority. Keychain storage, device labels,
and a loopback bind do not isolate arbitrary hostile processes running as that
user. External release and deployment effects remain explicitly gated.

## Data and credentials

Runtime state, client/operator records, local environment files, and generated
logs stay outside Git. Only the state contract and empty directory markers are
tracked under state/. Reviewed synthetic examples live in
[docs/examples/](docs/examples/).

The current tree was curated without rewriting history. The September 2026
published-history scan produced twelve individually reviewed matches: deliberate
test inputs, local Supabase demo anon tokens, and an expired approval identifier.
The exact fingerprints in [.gitleaksignore](.gitleaksignore) document those
exceptions. They do not suppress new findings elsewhere. Scanner results do not
prove that all sensitive information or vulnerabilities have been detected.

Never paste credentials into an issue, test log, screenshot, or public report.
If an actual secret is exposed, rotate it first and coordinate any necessary
history remediation while preserving private evidence.

## Checks and reports

Run Gitleaks with redaction enabled and audit the locked Python dependencies.
Review each finding; do not add broad path exclusions or blanket advisory
ignores to obtain a green result.

Use GitHub's private vulnerability reporting if available. Otherwise contact
the repository owner privately before sharing sensitive reproduction details.
