"""Literal, repository-root storage for Etsy credentials.

This module deliberately does not read process environment variables, ``.env``,
or macOS Keychain. The repository-root ``.etsy.env`` file is the sole Etsy
credential store.
"""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path

ETSY_ENV_FILENAME = ".etsy.env"

_ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class EtsyEnvParseError(ValueError):
    """A literal dotenv assignment could not be parsed safely."""

    def __init__(self) -> None:
        super().__init__("invalid .etsy.env format")


def etsy_env_path() -> Path:
    """Return the Etsy credential file regardless of the process working directory."""
    return Path(__file__).resolve().parents[2] / ETSY_ENV_FILENAME


def _unquoted_value(value: str) -> str:
    comment = re.search(r"\s#", value)
    return (value[: comment.start()] if comment else value).strip()


def _quoted_value(value: str) -> str:
    quote = value[0]
    characters: list[str] = []
    escaped = False
    for index, character in enumerate(value[1:], start=1):
        if escaped:
            characters.append({"n": "\n", "r": "\r", "t": "\t"}.get(character, character))
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == quote:
            trailing = value[index + 1 :].strip()
            if trailing and not trailing.startswith("#"):
                raise EtsyEnvParseError()
            return "".join(characters)
        else:
            characters.append(character)
    raise EtsyEnvParseError()


def _parse_value(value: str) -> str:
    stripped = value.lstrip()
    if stripped.startswith(("'", '"')):
        return _quoted_value(stripped)
    return _unquoted_value(stripped)


def _assignment_key(line: str) -> str | None:
    match = _ASSIGNMENT.match(line.rstrip("\r\n"))
    return match.group(1) if match else None


def load_etsy_env(env_path: Path | None = None) -> dict[str, str]:
    """Read ``.etsy.env`` as literal dotenv assignments with no cache."""
    path = env_path if env_path is not None else etsy_env_path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return {}

    values: dict[str, str] = {}
    for line in lines:
        match = _ASSIGNMENT.match(line)
        if match is not None:
            values[match.group(1)] = _parse_value(match.group(2))
    return values


def _encode_value(value: str) -> str:
    if value and not re.search(r"[\s#'\"\\]", value):
        return value
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def write_etsy_env_values(values: Mapping[str, str], env_path: Path | None = None) -> None:
    """Atomically update named values while retaining unrelated file content.

    Values are written to a mode-0600 temporary file before replacement. A
    failed write removes that temporary file and leaves the original intact.
    """
    path = env_path if env_path is not None else etsy_env_path()
    replacement = dict(values)
    if not replacement:
        return
    if any(not isinstance(name, str) or not _IDENTIFIER.fullmatch(name) for name in replacement):
        raise ValueError("Etsy credential names must be valid dotenv identifiers")
    if any(not isinstance(value, str) for value in replacement.values()):
        raise ValueError("Etsy credential values must be strings")

    try:
        original = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        original = ""

    output: list[str] = []
    seen: set[str] = set()
    for line in original.splitlines(keepends=True):
        name = _assignment_key(line)
        if name in replacement:
            output.append(f"{name}={_encode_value(replacement[name])}\n")
            seen.add(name)
        else:
            output.append(line)
    if output and not output[-1].endswith(("\n", "\r")):
        output.append("\n")
    for name, value in replacement.items():
        if name not in seen:
            output.append(f"{name}={_encode_value(value)}\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".etsy.env.", suffix=".tmp", dir=path.parent, text=True
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write("".join(output))
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
