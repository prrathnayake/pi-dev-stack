from __future__ import annotations

import os
import shutil
import tarfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath

ALLOWED_ROOTS = {
    ".env",
    "data",
    "homepage",
    "cloudflared",
    "local",
    "docker-compose.override.yml",
    "media",
}


class BackupError(RuntimeError):
    pass


def _archive_sources(root: Path, include_media: bool) -> list[Path]:
    required = [root / "data", root / ".env"]
    missing = [path.name for path in required if not path.exists()]
    if missing:
        raise BackupError("Required backup inputs are missing: " + ", ".join(missing))
    sources = list(required)
    optional = [root / "homepage", root / "cloudflared" / "config.yml", root / "local", root / "docker-compose.override.yml"]
    sources.extend(path for path in optional if path.exists())
    if include_media:
        media = root / "media"
        if not media.exists():
            raise BackupError("Cannot include media: media/ does not exist")
        sources.append(media)
    return sources


def validate_archive(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        with tarfile.open(path, "r:gz") as archive:
            names: set[str] = set()
            for member in archive.getmembers():
                item = PurePosixPath(member.name)
                if item.is_absolute() or ".." in item.parts or not item.parts:
                    errors.append(f"Unsafe archive path: {member.name}")
                    continue
                if item.parts[0] not in ALLOWED_ROOTS:
                    errors.append(f"Unexpected archive path: {member.name}")
                if not (member.isfile() or member.isdir()):
                    errors.append(f"Unsupported archive entry type: {member.name}")
                names.add(item.parts[0])
            for required in ("data", ".env"):
                if required not in names:
                    errors.append(f"Archive is missing required entry: {required}")
    except (OSError, tarfile.TarError) as exc:
        errors.append(f"Cannot read archive: {exc}")
    return errors


def create_backup(root: Path, *, include_media: bool = False) -> Path:
    sources = _archive_sources(root, include_media)
    destination = root / "backups"
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    final = destination / f"pi-dev-stack-{stamp}.tar.gz"
    temporary = destination / f".{final.name}.partial"
    try:
        with tarfile.open(temporary, "w:gz") as archive:
            for source in sources:
                archive.add(source, arcname=source.relative_to(root), recursive=True)
        errors = validate_archive(temporary)
        if errors:
            raise BackupError("; ".join(errors))
        os.replace(temporary, final)
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        if isinstance(exc, BackupError):
            raise
        raise BackupError(str(exc)) from exc
    return final


def list_backups(root: Path) -> list[Path]:
    directory = root / "backups"
    if not directory.exists():
        return []
    return sorted(directory.glob("pi-dev-stack-*.tar.gz"), reverse=True)


def prune_backups(root: Path, days: int) -> list[Path]:
    cutoff = datetime.now().timestamp() - timedelta(days=days).total_seconds()
    selected = [path for path in list_backups(root) if path.stat().st_mtime < cutoff]
    for path in selected:
        path.unlink()
    return selected


def restore_backup(root: Path, path: Path) -> Path:
    errors = validate_archive(path)
    if errors:
        raise BackupError("; ".join(errors))
    staging_parent = root / ".local-state"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="restore-stage-", dir=staging_parent))
    rollback = staging_parent / "restore-backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    moved: list[tuple[Path, Path]] = []
    installed: list[Path] = []
    try:
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                target = staging / member.name
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise BackupError(f"Unable to extract {member.name}")
                with source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(member.mode & 0o777)
        rollback.mkdir(parents=True, exist_ok=True)
        for staged in staging.iterdir():
            target = root / staged.name
            if target.exists():
                old = rollback / staged.name
                target.rename(old)
                moved.append((old, target))
            staged.rename(target)
            installed.append(target)
    except Exception as exc:
        for target in reversed(installed):
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            else:
                target.unlink(missing_ok=True)
        for old, target in reversed(moved):
            if old.exists():
                old.rename(target)
        if isinstance(exc, BackupError):
            raise
        raise BackupError(str(exc)) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return rollback
