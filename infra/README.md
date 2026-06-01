# Infra

This directory is reserved for local infrastructure and machine-level setup.

Likely future contents:

- Postgres and Redis local development setup
- launchd configuration for always-on workers on macOS
- machine bootstrap notes for a dedicated MacBook Air
- deployment helpers for external control surfaces

Local Postgres and Redis can be started with:

```bash
docker compose -f infra/compose.yaml up -d postgres redis
```

The API/dashboard still run without them; SQLite and the database queue remain
the default fallback.
