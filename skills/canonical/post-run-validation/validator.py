"""post-run-validation — pure-Python validator.

Final gate on every task result the control plane accepts. Each lane
declares a YAML contract in ``contracts/<lane>.yaml`` describing the
artifacts and events a completed task must emit, plus failure codes
that are never allowed in structured completion evidence.

Fail-closed: any exception is converted to ``verdict=fail`` with a
``failure_code`` the caller can persist and count.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # stdlib-only fallback if yaml is unavailable in sandbox
    import yaml  # type: ignore
except Exception:  # pragma: no cover - exercised on stripped envs
    yaml = None  # type: ignore


_CONTRACT_DIR = Path(__file__).parent / "contracts"
_SUPPORTED_LANES = {
    "engineering",
    "ios",
    "appstore",
    "gtm",
    "outreach",
    "skill_evolution",
}


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
                current_list = []
                out[key] = current_list
                pending_dict = None
            else:
                out[key] = rest
                current_list = None
                pending_dict = None
    return out


def run(payload: dict) -> dict:
    try:
        lane = payload["lane"]
        result: dict[str, Any] = payload.get("result") or {}
        if lane not in _SUPPORTED_LANES:
            return _fail(lane, "lane_unknown", f"no contract registered for lane={lane}")
        if not isinstance(result, dict):
            return _fail(lane, "result_malformed", "result must be a mapping")
        repo_root = Path(payload.get("repo_root") or ".")
        payload_task_id = payload.get("task_id") or ""
        task_id = result.get("task_id") or payload_task_id
        if not isinstance(task_id, str) or not task_id:
            return _fail(lane, "task_id_missing", "result must identify its task")
        if payload_task_id and result.get("task_id") and result["task_id"] != payload_task_id:
            return _fail(lane, "task_id_mismatch", "result task id does not match payload")
        if result.get("status") != "completed":
            return _fail(lane, "result_status_invalid", "result status must be completed")
        if (
            not isinstance(result.get("artifacts") or [], list)
            or not isinstance(result.get("events") or [], list)
            or not isinstance(result.get("failure_codes") or [], list)
        ):
            return _fail(lane, "result_malformed", "result evidence lists must be lists")

        contract = _load_contract(lane)
        if contract is None:
            return _fail(lane, "contract_missing", f"contracts/{lane}.yaml not found")

        required_artifacts = contract.get("required_artifacts") or []
        validated_artifacts: list[Path] = []
        for entry in required_artifacts:
            rel = entry.get("path") if isinstance(entry, dict) else str(entry)
            rel_glob = entry.get("path_glob") if isinstance(entry, dict) else None
            if rel_glob:
                rel_glob = str(rel_glob).replace("{task_id}", task_id)
                matches = [
                    path.resolve()
                    for path in repo_root.glob(rel_glob)
                    if path.is_file() and path.stat().st_size > 0
                ]
                listed_paths = {
                    _resolve_artifact_path(repo_root, artifact)
                    for artifact in (result.get("artifacts") or [])
                }
                if not any(match in listed_paths for match in matches):
                    return _fail(
                        lane,
                        "required_artifact_missing",
                        f"missing artifact matching {rel_glob}",
                    )
                validated_artifacts.extend(match for match in matches if match in listed_paths)
                continue
            if not rel:
                return _fail(
                    lane,
                    "contract_invalid",
                    "required artifact entry needs path or path_glob",
                )
            rel = str(rel)
            rel = rel.replace("{task_id}", task_id)
            expected = (repo_root / rel).resolve()
            listed = any(
                _resolve_artifact_path(repo_root, artifact) == expected
                for artifact in (result.get("artifacts") or [])
            )
            # A worker cannot satisfy the gate by naming a future or stale
            # path. The required evidence must both be declared in its result
            # and exist on disk at validation time.
            on_disk = expected.is_file() and expected.stat().st_size > 0
            if not listed or not on_disk:
                return _fail(
                    lane,
                    "required_artifact_missing",
                    f"missing artifact {rel}",
                )
            validated_artifacts.append(expected)

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

        semantic_failure = _validate_lane_evidence(lane, task_id, validated_artifacts)
        if semantic_failure:
            return _fail(
                lane, semantic_failure, "artifact does not identify successful task evidence"
            )

        failure_codes = set(result.get("failure_codes") or [])
        for forbidden in contract.get("forbidden_failure_codes") or []:
            code = forbidden if isinstance(forbidden, str) else str(forbidden)
            if code in failure_codes:
                return _fail(
                    lane,
                    "forbidden_failure_code_present",
                    f"completion evidence includes forbidden code {code}",
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


def _resolve_artifact_path(repo_root: Path, artifact: object) -> Path | None:
    if not isinstance(artifact, str) or not artifact:
        return None
    candidate = Path(artifact)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def _validate_lane_evidence(lane: str, task_id: str, paths: list[Path]) -> str:
    if lane == "appstore":
        return _validate_json(
            next((path for path in paths if path.name == "submission_summary.json"), None),
            task_id,
            {"status": "completed"},
        )
    if lane == "outreach":
        receipt = next(
            (
                path
                for path in paths
                if path.name == f"{task_id}.json" and path.parent.name == "receipts"
            ),
            None,
        )
        return _validate_json(
            receipt,
            task_id,
            {"status": "completed", "performed_operation": "OUTREACH_LEDGER_REFRESH"},
        )
    if lane == "skill_evolution":
        return _validate_json(
            next((path for path in paths if path.name == "applied.flag"), None),
            task_id,
            {"status": "completed"},
            ("approval_id", "approved_at"),
        )
    return ""


def _validate_json(
    path: Path | None, task_id: str, expected: dict[str, str], nonempty: tuple[str, ...] = ()
) -> str:
    if path is None:
        return "semantic_artifact_missing"
    try:
        payload = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return "semantic_artifact_malformed"
    if not isinstance(payload, dict) or payload.get("task_id") != task_id:
        return "semantic_artifact_task_mismatch"
    if any(payload.get(key) != value for key, value in expected.items()):
        return "semantic_artifact_status_invalid"
    if any(not isinstance(payload.get(key), str) or not payload[key] for key in nonempty):
        return "semantic_artifact_incomplete"
    return ""
