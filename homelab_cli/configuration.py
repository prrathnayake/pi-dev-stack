from __future__ import annotations

import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
SECRET_MARKERS = ("PASSWORD", "SECRET", "TOKEN", "KEY", "CLAIM")


def is_secret(key: str) -> bool:
    return any(marker in key.upper() for marker in SECRET_MARKERS)


def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return value[:2] + "*" * min(12, len(value) - 4) + value[-2:]


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def write_env_value(root: Path, key: str, value: str | None) -> Path | None:
    if not KEY_PATTERN.fullmatch(key):
        raise ValueError("Configuration keys must use uppercase letters, numbers, and underscores.")
    path = root / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    updated: list[str] = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            found = True
            if value is not None:
                updated.append(f"{key}={value}")
        else:
            updated.append(line)
    if not found and value is not None:
        updated.append(f"{key}={value}")
    backup: Path | None = None
    if path.exists():
        backup_dir = root / ".local-state" / "config-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = backup_dir / f"env-{stamp}.bak"
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".env.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(updated).rstrip() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return backup
