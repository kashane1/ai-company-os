from __future__ import annotations

from packages.db.control_plane_db import ControlPlaneDatabase, ControlPlaneDatabaseConfig


def test_database_config_redacts_postgres_password() -> None:
    config = ControlPlaneDatabaseConfig(
        backend="postgres",
        dsn="postgresql://ai_company:secret@localhost:5432/ai_company_os",
    )

    assert config.redacted_dsn == "postgresql://ai_company:***@localhost:5432/ai_company_os"


def test_database_health_info_initializes_sqlite_schema(isolated_repo_root) -> None:
    info = ControlPlaneDatabase().health_info()

    assert info["backend"] == "sqlite"
    assert info["schema"] == "ok"

