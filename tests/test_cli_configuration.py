from __future__ import annotations

from pathlib import Path

import pytest

from homelab_cli.configuration import is_secret, mask, read_env, write_env_value


def test_config_write_is_atomic_and_creates_ignored_backup(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("A=one\nSECRET_KEY=old\n", encoding="utf-8")
    backup = write_env_value(tmp_path, "SECRET_KEY", "new-value")
    assert read_env(tmp_path / ".env")["SECRET_KEY"] == "new-value"
    assert backup is not None and backup.parent == tmp_path / ".local-state" / "config-backups"
    assert "SECRET_KEY=old" in backup.read_text(encoding="utf-8")


def test_config_unset_preserves_comments(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("# heading\nA=one\nB=two\n", encoding="utf-8")
    write_env_value(tmp_path, "A", None)
    content = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "# heading" in content
    assert "A=" not in content
    assert "B=two" in content


def test_config_rejects_unsafe_keys_and_masks_secrets(tmp_path: Path) -> None:
    assert is_secret("DATABASE_PASSWORD")
    assert mask("abcdefgh") != "abcdefgh"
    with pytest.raises(ValueError):
        write_env_value(tmp_path, "bad-key", "value")
