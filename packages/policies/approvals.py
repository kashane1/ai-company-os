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


def requires_human_approval(task: TaskPacket) -> bool:
    if task.risk_level is RiskLevel.HIGH:
        return True

    summary = f"{task.title} {task.summary}".lower()
    if any(keyword in summary for keyword in APPROVAL_KEYWORDS):
        return True

    return task.lane is WorkerLane.APPSTORE and "submit" in summary
