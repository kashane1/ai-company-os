from packages.config.settings import ensure_runtime_directories
from packages.db.json_store import JsonStore
from packages.schemas.approval import ApprovalRecord


class ApprovalStore:
    def __init__(self) -> None:
        paths = ensure_runtime_directories()
        self.store = JsonStore(paths.approvals_root)

    def save(self, approval: ApprovalRecord) -> str:
        return str(self.store.save(approval.id, approval.to_dict()))

    def load(self, approval_id: str) -> ApprovalRecord:
        return ApprovalRecord.from_dict(self.store.load(approval_id))
