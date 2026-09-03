from __future__ import annotations

import sys
from pathlib import Path

from homelab_cli.context import AppState
from homelab_cli.runner import MAX_CAPTURE_BYTES, Runner


def test_runner_propagates_failure_and_missing_binary(tmp_path: Path) -> None:
    runner = Runner(AppState(root=tmp_path))
    failed = runner.run([sys.executable, "-c", "import sys; print('bad', file=sys.stderr); sys.exit(7)"])
    assert failed.returncode == 7
    assert failed.stderr == "bad"
    missing = runner.run([str(tmp_path / "missing")])
    assert missing.returncode == 127


def test_runner_times_out_process_group(tmp_path: Path) -> None:
    runner = Runner(AppState(root=tmp_path))
    result = runner.run([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.05)
    assert result.timed_out
    assert not result.ok


def test_runner_bounds_captured_output(tmp_path: Path) -> None:
    runner = Runner(AppState(root=tmp_path))
    result = runner.run([sys.executable, "-c", f"print('x' * {MAX_CAPTURE_BYTES + 100})"])
    assert len(result.stdout.encode()) <= MAX_CAPTURE_BYTES


def test_runner_dry_run_skips_mutation(tmp_path: Path) -> None:
    runner = Runner(AppState(root=tmp_path, dry_run=True))
    marker = tmp_path / "created"
    result = runner.run([sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"], mutate=True)
    assert result.ok and result.dry_run
    assert not marker.exists()
