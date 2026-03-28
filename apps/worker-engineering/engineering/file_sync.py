import shutil
from pathlib import Path


EXCLUDED_NAMES = {
    ".DS_Store",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "state",
}


def sync_tree(source_root: Path, destination_root: Path) -> None:
    for source_path in source_root.rglob("*"):
        relative_path = source_path.relative_to(source_root)
        if any(part in EXCLUDED_NAMES for part in relative_path.parts):
            continue

        destination_path = destination_root / relative_path
        if source_path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            continue

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)


def clear_directory(directory: Path) -> None:
    if not directory.exists():
        return

    for child in directory.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
