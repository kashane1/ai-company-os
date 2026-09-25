# Etsy credentials and OAuth

This is the current credential contract for every Etsy API, OAuth, and Etsy
read-only diagnostic operation in this repository.

## Source of truth

Load Etsy secrets only from the repository-root `.etsy.env` file. The file is
ignored by git and may be updated when the founder provides refreshed values.
It is the sole supported source for the Etsy composite API credential, OAuth
access token, OAuth refresh token, and expiry metadata.

The approved keys are:

- `ETSY_API_CREDENTIAL` — composite `keystring:shared_secret`
- `ETSY_OAUTH_ACCESS_TOKEN` — current OAuth access token
- `ETSY_OAUTH_REFRESH_TOKEN` — OAuth refresh token
- `ETSY_OAUTH_EXPIRES_AT` — expiry timestamp for the access token

The founder has authorized agents to maintain these approved keys in
`.etsy.env` when an Etsy OAuth flow refreshes or replaces them; agents should
not ask again for permission to perform that local secret-file maintenance.

Do not read, write, or probe macOS Keychain for Etsy credentials. Do not invoke
the `security` command for Etsy. Do not fall back to the process environment,
the root `.env`, or any other secret file. Missing or malformed credentials
must report the missing key names and safe status only; never print values,
tokens, composite credentials, or the contents of `.etsy.env`.

The Keychain rule here is intentionally scoped to Etsy. Existing Printify
credentials and approval-signing material have separate contracts and remain
unchanged unless their own documentation is explicitly revised.

## Diagnostic

Run the read-only readiness check from the repository root:

```sh
.venv/bin/python scripts/etsy_readonly.py
```

The check may report key names, presence, format, and expiry status. It must
not make an Etsy write, persist OAuth material elsewhere, or expose secret
values. Confirm the command's `--help` output before using additional options.

## OAuth and live actions

OAuth authorization-code and PKCE handling may use the values loaded from
`.etsy.env`, keeping transient codes and verifiers in memory. Refresh tokens
must be written back only to the approved keys in `.etsy.env` when a refresh
is required. Updates must use a restrictive temporary file, atomic
replacement, and final mode `0600`; the resulting file remains ignored and
local. Never rewrite the file through shell interpolation or print its
contents while updating it.

Credential availability does not authorize Etsy mutations. Listing creation,
updates, activation, publication, and other irreversible external actions
still require the existing action-specific founder approval and revision
checks. Read-only inspection may proceed within the lane's existing scope.

Historical Etsy plans that mention Keychain or `.env` are superseded by this
document for credential loading. They remain useful as historical records of
the earlier implementation and approval decisions.
