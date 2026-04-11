"""post-run-validation — pure-Python validator.

Final gate on every task result the control plane accepts. Each lane
declares a YAML contract in ``contracts/<lane>.yaml`` describing the
artifacts and events a completed task must emit, plus failure codes
that are never allowed to leak into the summary line.

Fail-closed: any exception is converted to ``verdict=fail`` with a
``failure_code`` the caller can persist and count.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:  # stdlib-only fallback if yaml is unavailable in sandbox
    import yaml  # type: ignore
except Exception:  # pragma: no cover - exercised on stripped envs
    yaml = None  # type: ignore


_CONTRACT_DIR = Path(__file__).parent / "contracts"
_SUPPORTED_LANES = {"engineering", "ios", "appstore", "gtm"}


def _load_contract(lane: str) -> dict[str, Any] | None:
    path = _CONTRACT_DIR / f"{lane}.yaml"
    if not path.exists():
        return None
    raw = path.read_text()
    if yaml is not None:
        return yaml.safe_load(raw) or {}
    # Minimal fallback parser sufficient for the flat contract shape.
    return _tiny_yaml(raw)


def _tiny_yaml(raw: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    current_list_key: str | None = None
    current_list: list[Any] | None = None
    pending_dict: dict[str, Any] | None = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - "):
            item = line[4:].strip()
            if ":" in item:
                pending_dict = {}
                k, v = item.split(":", 1)
                pending_dict[k.strip()] = v.strip()
                if current_list is not None:
                    current_list.append(pending_dict)
            else:
                if current_list is not None:
                    current_list.append(item)
                pending_dict = None
        elif line.startswith("    ") and pending_dict is not None:
            k, v = line.strip().split(":", 1)
            pending_dict[k.strip()] = v.strip()
        elif ":" in line and not line.startswith(" "):
            key, rest = line.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            if rest == "":
                current_list_key = key
                current_list = []
                out[key] = current_list
                pending_dict = None
            else:
                out[key] = rest
                current_list_key = None
                current_list = None
                pending_dict = None
    return out


def run(payload: dict) -> dict:
    try:
        lane = payload["lane"]
        task_type = payload.get("task_type", "")
        result: dict[str, Any] = payload.get("result") or {}
        repo_root = Path(payload.get("repo_root") or ".")
        task_id = result.get("task_id") or payload.get("task_id") or ""

        if lane not in _SUPPORTED_LANES:
            return _fail(lane, "lane_unknown", f"no contract registered for lane={lane}")

        contract = _load_contract(lane)
        if contract is None:
            return _fail(lane, "contract_missing", f"contracts/{lane}.yaml not found")

        required_artifacts = contract.get("required_artifacts") or []
        for entry in required_artifacts:
            rel = entry["path"] if isinstance(entry, dict) else str(entry)
            rel = rel.replace("{task_id}", task_id)
            # Consider the artifact "present" if the worker listed it OR
            # if the file exists at repo_root/rel.
            listed = rel in (result.get("artifacts") or [])
            on_disk = (repo_root / rel).exists()
            if not (listed or on_disk):
                return _fail(
                    lane,
                    "required_artifact_missing",
                    f"missing artifact {rel}",
                )

        required_events = contract.get("required_events") or []
        emitted_events = set(result.get("events") or [])
        for event_name in required_events:
            name = event_name if isinstance(event_name, str) else str(event_name)
            if name not in emitted_events:
                return _fail(
                    lane,
                    "required_event_missing",
                    f"missing event {name}",
                )

        summary = (result.get("summary") or "").lower()
        for forbidden in contract.get("forbidden_failure_codes") or []:
            code = forbidden if isinstance(forbidden, str) else str(forbidden)
            if code.lower() in summary:
                return _fail(
                    lane,
                    "forbidden_failure_code_present",
                    f"summary mentions forbidden code {code}",
                )

        return {
            "verdict": "ok",
            "failure_code": "",
            "reason": "",
            "lane": lane,
        }
    except Exception as exc:  # fail-closed
        return _fail(
            payload.get("lane", "unknown"),
            f"exception:{type(exc).__name__}",
            str(exc),
        )


def _fail(lane: str, failure_code: str, reason: str) -> dict:
    return {
        "verdict": "fail",
        "failure_code": failure_code,
        "reason": reason,
        "lane": lane,
    }
