from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def load_runtime_supervisor_main():
    module_path = Path(__file__).resolve().parents[3] / "apps" / "runtime-supervisor" / "main.py"
    spec = importlib.util.spec_from_file_location("runtime_supervisor_main_api_spec", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_default_worker_specs_includes_api_worker() -> None:
    runtime_supervisor_main = load_runtime_supervisor_main()

    specs = runtime_supervisor_main.default_worker_specs()

    # Phase 3 appended the skill_evolution worker as the fifth spec,
    # keeping the first four in the same order so the launchd config
    # is stable for existing workers. The api worker is now specs[-2].
    assert len(specs) == 5
    lanes = [spec.lane for spec in specs]
    assert lanes == [
        "engineering",
        "ios",
        "appstore",
        "api",
        "skill_evolution",
    ]

    api_spec = specs[-2]
    assert api_spec.worker_id == "worker-api"
    assert str(api_spec.script_path).endswith("apps/api/server.py")

    evolution_spec = specs[-1]
    assert evolution_spec.lane == "skill_evolution"
    assert evolution_spec.worker_id == "worker-skill-evolution"
    assert str(evolution_spec.script_path).endswith(
        "apps/worker-skill-evolution/main.py"
    )
