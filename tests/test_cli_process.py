from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PI_DEV_STACK_ROOT"] = str(ROOT)
    return subprocess.run(
        [sys.executable, "-m", "homelab_cli", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_process_preserves_usage_exit_code_and_json_envelope() -> None:
    result = _run("--json", "data", "purge", "--media")
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["errors"]


def test_process_reports_unknown_and_legacy_commands() -> None:
    unknown = _run("--json", "not-a-command")
    assert unknown.returncode == 2
    assert json.loads(unknown.stdout)["ok"] is False
    legacy = _run("n8n", "restart")
    assert legacy.returncode == 2
    assert "service restart n8n" in legacy.stderr
