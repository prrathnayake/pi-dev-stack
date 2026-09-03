from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from homelab_cli.backups import BackupError, create_backup, restore_backup, validate_archive


def _runtime(root: Path) -> None:
    (root / "data" / "app").mkdir(parents=True)
    (root / "data" / "app" / "value.txt").write_text("original", encoding="utf-8")
    (root / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    (root / "media").mkdir()
    (root / "media" / "movie.txt").write_text("large", encoding="utf-8")


def test_backup_create_verify_and_restore_excludes_media(tmp_path: Path) -> None:
    _runtime(tmp_path)
    archive = create_backup(tmp_path)
    assert validate_archive(archive) == []
    with tarfile.open(archive, "r:gz") as handle:
        names = handle.getnames()
    assert any(name.startswith("data/") for name in names)
    assert not any(name.startswith("media/") for name in names)
    (tmp_path / "data" / "app" / "value.txt").write_text("changed", encoding="utf-8")
    rollback = restore_backup(tmp_path, archive)
    assert (tmp_path / "data" / "app" / "value.txt").read_text(encoding="utf-8") == "original"
    assert (rollback / "data" / "app" / "value.txt").read_text(encoding="utf-8") == "changed"


def test_backup_can_include_media_explicitly(tmp_path: Path) -> None:
    _runtime(tmp_path)
    archive = create_backup(tmp_path, include_media=True)
    with tarfile.open(archive, "r:gz") as handle:
        assert "media/movie.txt" in handle.getnames()


def test_backup_requires_env_and_data(tmp_path: Path) -> None:
    with pytest.raises(BackupError, match="Required"):
        create_backup(tmp_path)


def test_archive_rejects_traversal_and_links(tmp_path: Path) -> None:
    archive = tmp_path / "bad.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        traversal = tarfile.TarInfo("../escape")
        traversal.size = 1
        handle.addfile(traversal, io.BytesIO(b"x"))
        link = tarfile.TarInfo("data/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        handle.addfile(link)
    errors = validate_archive(archive)
    assert any("Unsafe" in error for error in errors)
    assert any("Unsupported" in error for error in errors)
