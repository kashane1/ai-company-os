from packages.schemas.task_packet import RiskLevel, TaskPacket, WorkerLane


APPROVAL_KEYWORDS = {
    "merge",
    "deploy",
    "submit",
    "release",
    "billing",
    "dns",
    "pricing",
    "production",
}

SAFE_RELEASE_ACTIONS = {"prepare_testflight"}
APPROVAL_REQUIRED_RELEASE_ACTIONS = {
    "submit_testflight",
    "submit_appstore",
    "release_to_store",
}


def requires_human_approval(task: TaskPacket) -> bool:
    if task.risk_level is RiskLevel.HIGH:
        return True

    summary = f"{task.title} {task.summary}".lower()
    if any(keyword in summary for keyword in APPROVAL_KEYWORDS):
        return True

    return task.lane is WorkerLane.APPSTORE and "submit" in summary


def requires_release_action_approval(action: str) -> bool:
    if action in SAFE_RELEASE_ACTIONS:
        return False
    return action in APPROVAL_REQUIRED_RELEASE_ACTIONS
