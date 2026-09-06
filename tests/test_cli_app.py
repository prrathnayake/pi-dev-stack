from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from homelab_cli.__main__ import _legacy_message
from homelab_cli.app import app
from homelab_cli.runner import RunResult


ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def _project(tmp_path: Path, monkeypatch) -> Path:
    (tmp_path / "config").mkdir()
    shutil.copy2(ROOT / "config" / "services.tsv", tmp_path / "config" / "services.tsv")
    shutil.copy2(ROOT / "docker-compose.yml", tmp_path / "docker-compose.yml")
    shutil.copy2(ROOT / ".env.example", tmp_path / ".env.example")
    monkeypatch.setenv("PI_DEV_STACK_ROOT", str(tmp_path))
    return tmp_path


def test_help_and_all_command_groups_are_discoverable() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("overview", "setup", "stack", "service", "tunnel", "backup", "config", "system", "pihole", "update", "data", "completion"):
        assert command in result.stdout


def test_service_list_json_is_one_valid_document(tmp_path: Path, monkeypatch) -> None:
    _project(tmp_path, monkeypatch)
    result = runner.invoke(app, ["--json", "service", "list"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert any(item["name"] == "n8n" for item in payload["data"])


def test_config_set_masks_secret_and_writes_value(tmp_path: Path, monkeypatch) -> None:
    _project(tmp_path, monkeypatch)
    result = runner.invoke(app, ["--json", "config", "set", "API_TOKEN", "--value", "super-secret"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["value"] != "super-secret"
    assert "API_TOKEN=super-secret" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_json_never_bypasses_confirmation(tmp_path: Path, monkeypatch) -> None:
    _project(tmp_path, monkeypatch)
    (tmp_path / "media").mkdir()
    result = runner.invoke(app, ["--json", "data", "purge", "--media"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert (tmp_path / "media").exists()


def test_dry_run_does_not_delete_data(tmp_path: Path, monkeypatch) -> None:
    _project(tmp_path, monkeypatch)
    (tmp_path / "data").mkdir()
    marker = tmp_path / "data" / "marker"
    marker.write_text("keep", encoding="utf-8")
    result = runner.invoke(app, ["--dry-run", "data", "purge", "--data"])
    assert result.exit_code == 0
    assert marker.exists()


def test_docker_failure_is_not_reported_as_success(tmp_path: Path, monkeypatch) -> None:
    _project(tmp_path, monkeypatch)
    monkeypatch.setattr("homelab_cli.app.compose_command", lambda state, extras=False: ["docker", "compose"])
    monkeypatch.setattr("homelab_cli.app.Runner.run", lambda self, args, **kwargs: RunResult(list(args), 9, stderr="boom"))
    result = runner.invoke(app, ["--json", "service", "start", "n8n"])
    assert result.exit_code == 4
    assert json.loads(result.stdout)["ok"] is False


def test_service_status_uses_compose_ps(tmp_path: Path, monkeypatch) -> None:
    _project(tmp_path, monkeypatch)
    monkeypatch.setattr("homelab_cli.app.compose_command", lambda state, extras=False: ["docker", "compose"])
    monkeypatch.setattr("homelab_cli.app.Runner.run", lambda self, args, **kwargs: RunResult(list(args), 0, stdout="ok"))
    result = runner.invoke(app, ["--json", "service", "status", "n8n"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert "ps" in payload["data"]["args"]


def test_legacy_commands_get_migration_messages(monkeypatch) -> None:
    monkeypatch.setenv("PI_DEV_STACK_ROOT", str(ROOT))
    assert "stack start" in (_legacy_message(["up"]) or "")
    assert "stack start" in (_legacy_message(["--json", "up"]) or "")
    assert "service restart n8n" in (_legacy_message(["n8n", "restart"]) or "")
    assert _legacy_message(["pihole", "stats"]) is None
    assert "service start pihole" in (_legacy_message(["pihole", "start"]) or "")


def test_completion_shell_is_a_positional_argument(tmp_path: Path, monkeypatch) -> None:
    _project(tmp_path, monkeypatch)
    result = runner.invoke(app, ["completion", "show", "bash"])
    assert result.exit_code == 0
    assert "_HOMELAB_COMPLETE" in result.stdout
