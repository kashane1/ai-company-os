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

    assert len(specs) == 4
    assert specs[-1].lane == "api"
    assert specs[-1].worker_id == "worker-api"
    assert str(specs[-1].script_path).endswith("apps/api/server.py")
