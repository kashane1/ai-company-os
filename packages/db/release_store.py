from packages.config.settings import ensure_runtime_directories
from packages.db.json_store import JsonStore
from packages.schemas.release import BuildCandidate, MetadataDraft, ReleaseRecord, ScreenshotSet


class ReleaseStore:
    def __init__(self) -> None:
        paths = ensure_runtime_directories()
        self.builds = JsonStore(paths.build_candidates_root)
        self.metadata = JsonStore(paths.metadata_drafts_root)
        self.screenshots = JsonStore(paths.screenshot_sets_root)
        self.releases = JsonStore(paths.release_records_root)

    def save_build_candidate(self, build_candidate: BuildCandidate) -> str:
        return str(self.builds.save(build_candidate.id, build_candidate.to_dict()))

    def load_build_candidate(self, build_candidate_id: str) -> BuildCandidate:
        return BuildCandidate.from_dict(self.builds.load(build_candidate_id))

    def save_metadata_draft(self, metadata_draft: MetadataDraft) -> str:
        return str(self.metadata.save(metadata_draft.id, metadata_draft.to_dict()))

    def load_metadata_draft(self, metadata_draft_id: str) -> MetadataDraft:
        return MetadataDraft.from_dict(self.metadata.load(metadata_draft_id))

    def save_screenshot_set(self, screenshot_set: ScreenshotSet) -> str:
        return str(self.screenshots.save(screenshot_set.id, screenshot_set.to_dict()))

    def load_screenshot_set(self, screenshot_set_id: str) -> ScreenshotSet:
        return ScreenshotSet.from_dict(self.screenshots.load(screenshot_set_id))

    def save_release_record(self, release_record: ReleaseRecord) -> str:
        return str(self.releases.save(release_record.id, release_record.to_dict()))

    def load_release_record(self, release_record_id: str) -> ReleaseRecord:
        return ReleaseRecord.from_dict(self.releases.load(release_record_id))
