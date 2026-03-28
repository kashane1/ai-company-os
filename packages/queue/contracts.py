from packages.schemas.task_packet import WorkerLane


QUEUE_BY_LANE = {
    WorkerLane.SUPERVISOR: "supervisor.tasks",
    WorkerLane.ENGINEERING: "engineering.tasks",
    WorkerLane.IOS: "ios.tasks",
    WorkerLane.APPSTORE: "appstore.tasks",
}
