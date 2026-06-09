from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

TEST_REPO_ROOT_ENV_VAR = "AI_COMPANY_OS_REPO_ROOT"
DATABASE_URL_ENV_VAR = "AI_COMPANY_OS_DATABASE_URL"
QUEUE_BACKEND_ENV_VAR = "AI_COMPANY_OS_QUEUE_BACKEND"
REDIS_URL_ENV_VAR = "AI_COMPANY_OS_REDIS_URL"


# ── API Key Environment Variables ────────────────────────────
GEMINI_API_KEY_ENV_VAR = "GEMINI_API_KEY"
# Design-engine authoring lane — external design tools (used sparingly, at authoring
# time only, to grow the block library; never called on a fleet build).
STITCH_API_KEY_ENV_VAR = "STITCH_API_KEY"  # Google Stitch MCP API (X-Goog-Api-Key)
FIGMA_API_KEY_ENV_VAR = "FIGMA_API_KEY"  # Figma REST (X-Figma-Token)
POSTIZ_API_KEY_ENV_VAR = "POSTIZ_API_KEY"
REVENUECAT_API_KEY_ENV_VAR = "REVENUECAT_API_KEY"
OPENROUTER_API_KEY_ENV_VAR = "OPENROUTER_API_KEY"
NVIDIA_API_KEY_ENV_VAR = "NVIDIA_API_KEY"
GITHUB_TOKEN_ENV_VAR = "GITHUB_TOKEN"
# Server-side Places API (New) key — prospecting/enrichment, never in a browser.
GOOGLE_PLACES_API_KEY_ENV_VAR = "GOOGLE_PLACES_API_KEY"
# Browser-side Maps key for embedding maps on demo/prospect sites we ship. Kept
# separate from the Places key so it can be HTTP-referrer-restricted and exposed
# in client-side markup without leaking the server key. See packages/agency/demo_maps.py.
GOOGLE_MAPS_DEMO_API_KEY_ENV_VAR = "GOOGLE_MAPS_DEMO_API_KEY"
REDDIT_CLIENT_ID_ENV_VAR = "REDDIT_CLIENT_ID"
REDDIT_CLIENT_SECRET_ENV_VAR = "REDDIT_CLIENT_SECRET"
# Section F — web deploy lane (Netlify) + Stripe monetization.
NETLIFY_AUTH_TOKEN_ENV_VAR = "NETLIFY_AUTH_TOKEN"
STRIPE_SECRET_KEY_ENV_VAR = "STRIPE_SECRET_KEY"
STRIPE_WEBHOOK_SECRET_ENV_VAR = "STRIPE_WEBHOOK_SECRET"
# Bundle → Stripe price-id map, as a JSON string. Price ids are environment-
# scoped (test vs live), so they live in config/env, NOT in catalog.yaml. Shape:
#   {"package_c": {"test": {"setup": "price_…", "monthly": "price_…"}, "live": {…}}}
STRIPE_PRICE_MAP_ENV_VAR = "STRIPE_PRICE_MAP"
# Shared secret the Netlify webhook forwarder sends as x-agency-forward-secret;
# the local receiver (apps/api /stripe/forward) verifies it before reconciling.
AGENCY_STRIPE_EVENT_FORWARD_SECRET_ENV_VAR = "AGENCY_STRIPE_EVENT_FORWARD_SECRET"
# Plausible Stats API — real visit/lead numbers for the monthly report (G10).
# Base URL is config so a self-hosted instance just swaps the host.
PLAUSIBLE_API_KEY_ENV_VAR = "PLAUSIBLE_API_KEY"
PLAUSIBLE_BASE_URL_ENV_VAR = "PLAUSIBLE_BASE_URL"
# Section G — agency transaction loop: inbound lead notification (Resend).
# Server-side only (set in Netlify env / .env). NEVER a PUBLIC_/VITE_ prefix and
# never shipped in dist/ — see packages/web/deploy.assert_no_secret_leak.
RESEND_API_KEY_ENV_VAR = "RESEND_API_KEY"
# Where new-lead notifications are sent. Swappable to a business inbox later
# without a source redeploy — it's a single Netlify env var.
LEAD_NOTIFY_EMAIL_ENV_VAR = "LEAD_NOTIFY_EMAIL"
# Verified Resend sending address (defaults applied in the function if unset).
LEAD_FROM_EMAIL_ENV_VAR = "LEAD_FROM_EMAIL"


def load_dotenv() -> None:
    """Load .env file from repo root if it exists. No external dependencies."""
    root = Path(__file__).resolve().parents[2]
    env_file = root / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        # Don't overwrite existing env vars (explicit env takes precedence)
        if key and key not in os.environ:
            os.environ[key] = value


def get_api_key(env_var: str) -> str | None:
    """Get an API key, loading .env first if needed."""
    load_dotenv()
    return os.environ.get(env_var)


@dataclass(frozen=True)
class RuntimePaths:
    repo_root: Path
    state_root: Path
    repos_root: Path
    worktrees_root: Path
    artifacts_root: Path
    checkpoints_root: Path
    logs_root: Path
    cache_root: Path
    platform_state_root: Path
    tasks_root: Path
    task_runs_root: Path
    approvals_root: Path
    products_root: Path
    releases_root: Path
    repo_records_root: Path
    worktree_records_root: Path
    build_candidates_root: Path
    metadata_drafts_root: Path
    screenshot_sets_root: Path
    release_records_root: Path
    engineering_artifacts_root: Path
    ios_artifacts_root: Path
    engineering_logs_root: Path
    ios_logs_root: Path
    postmortems_root: Path
    postmortem_audit_log_path: Path
    control_plane_db_path: Path


def load_runtime_paths(repo_root: Path | None = None) -> RuntimePaths:
    override_root = os.environ.get(TEST_REPO_ROOT_ENV_VAR)
    root = repo_root or (Path(override_root).resolve() if override_root else Path(__file__).resolve().parents[2])
    state_root = root / "state"
    checkpoints_root = state_root / "checkpoints"
    platform_state_root = checkpoints_root / "platform"
    artifacts_root = state_root / "artifacts"
    logs_root = state_root / "logs"
    return RuntimePaths(
        repo_root=root,
        state_root=state_root,
        repos_root=state_root / "repos",
        worktrees_root=state_root / "worktrees",
        artifacts_root=artifacts_root,
        checkpoints_root=checkpoints_root,
        logs_root=logs_root,
        cache_root=state_root / "cache",
        platform_state_root=platform_state_root,
        tasks_root=platform_state_root / "tasks",
        task_runs_root=platform_state_root / "task_runs",
        approvals_root=platform_state_root / "approvals",
        products_root=platform_state_root / "products",
        releases_root=platform_state_root / "releases",
        repo_records_root=platform_state_root / "repos",
        worktree_records_root=platform_state_root / "worktrees",
        build_candidates_root=platform_state_root / "releases" / "build_candidates",
        metadata_drafts_root=platform_state_root / "releases" / "metadata_drafts",
        screenshot_sets_root=platform_state_root / "releases" / "screenshot_sets",
        release_records_root=platform_state_root / "releases" / "release_records",
        engineering_artifacts_root=artifacts_root / "engineering",
        ios_artifacts_root=artifacts_root / "ios",
        engineering_logs_root=logs_root / "engineering",
        ios_logs_root=logs_root / "ios",
        postmortems_root=state_root / "postmortems",
        postmortem_audit_log_path=logs_root / "postmortems" / "audit.jsonl",
        control_plane_db_path=platform_state_root / "control_plane.sqlite3",
    )


def ensure_runtime_directories(repo_root: Path | None = None) -> RuntimePaths:
    paths = load_runtime_paths(repo_root)
    directories = [
        paths.repos_root,
        paths.worktrees_root,
        paths.artifacts_root,
        paths.checkpoints_root,
        paths.logs_root,
        paths.cache_root,
        paths.platform_state_root,
        paths.tasks_root,
        paths.task_runs_root,
        paths.approvals_root,
        paths.products_root,
        paths.releases_root,
        paths.repo_records_root,
        paths.worktree_records_root,
        paths.build_candidates_root,
        paths.metadata_drafts_root,
        paths.screenshot_sets_root,
        paths.release_records_root,
        paths.engineering_artifacts_root,
        paths.ios_artifacts_root,
        paths.engineering_logs_root,
        paths.ios_logs_root,
        paths.postmortems_root,
        paths.postmortem_audit_log_path.parent,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    return paths
