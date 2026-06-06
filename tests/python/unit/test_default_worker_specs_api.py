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

    # Specs are appended in order so the launchd config stays stable for existing
    # workers. G1 appended the billing-event poller last (a supervised periodic
    # loop, not a task-claiming worker).
    assert len(specs) == 6
    lanes = [spec.lane for spec in specs]
    assert lanes == [
        "engineering",
        "ios",
        "appstore",
        "api",
        "skill_evolution",
        "billing_poller",
    ]

    by_lane = {spec.lane: spec for spec in specs}
    assert by_lane["api"].worker_id == "worker-api"
    assert str(by_lane["api"].script_path).endswith("apps/api/server.py")
    assert by_lane["skill_evolution"].worker_id == "worker-skill-evolution"
    assert str(by_lane["skill_evolution"].script_path).endswith(
        "apps/worker-skill-evolution/main.py"
    )

    poller = specs[-1]
    assert poller.lane == "billing_poller"
    assert poller.worker_id == "worker-billing-poller"
    assert str(poller.script_path).endswith("apps/worker-billing-poller/main.py")
