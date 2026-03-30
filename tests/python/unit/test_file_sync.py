from pathlib import Path

from engineering.file_sync import clear_directory, sync_tree


def test_sync_tree_copies_regular_files_and_nested_directories(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    (source_root / "nested").mkdir(parents=True)
    (source_root / "nested" / "notes.txt").write_text("hello")
    (source_root / "README.md").write_text("docs")

    sync_tree(source_root, destination_root)

    assert (destination_root / "nested" / "notes.txt").read_text() == "hello"
    assert (destination_root / "README.md").read_text() == "docs"


def test_sync_tree_skips_excluded_names_at_any_depth(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    (source_root / ".git").mkdir(parents=True)
    (source_root / ".git" / "config").write_text("ignore")
    (source_root / "nested" / "__pycache__").mkdir(parents=True)
    (source_root / "nested" / "__pycache__" / "cache.pyc").write_text("ignore")
    (source_root / "nested" / "keep.txt").parent.mkdir(parents=True, exist_ok=True)
    (source_root / "nested" / "keep.txt").write_text("keep")

    sync_tree(source_root, destination_root)

    assert not (destination_root / ".git").exists()
    assert not (destination_root / "nested" / "__pycache__").exists()
    assert (destination_root / "nested" / "keep.txt").read_text() == "keep"


def test_clear_directory_removes_existing_files_and_directories(tmp_path: Path) -> None:
    directory = tmp_path / "workspace"
    (directory / "nested").mkdir(parents=True)
    (directory / "nested" / "artifact.txt").write_text("remove")
    (directory / "top.txt").write_text("remove")

    clear_directory(directory)

    assert directory.exists()
    assert list(directory.iterdir()) == []


def test_clear_directory_is_a_no_op_for_missing_path(tmp_path: Path) -> None:
    clear_directory(tmp_path / "missing")

