from __future__ import annotations

import os
import shutil
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .context import AppState

MAX_CAPTURE_BYTES = 1_048_576


@dataclass(frozen=True)
class RunResult:
    args: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    dry_run: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


class Runner:
    def __init__(self, state: AppState):
        self.state = state

    def run(
        self,
        args: Sequence[str],
        *,
        timeout: float = 60,
        stream: bool = False,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        mutate: bool = False,
    ) -> RunResult:
        command = [str(arg) for arg in args]
        if mutate and self.state.dry_run:
            return RunResult(command, 0, stdout="DRY RUN: " + " ".join(command), dry_run=True)
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        try:
            process = subprocess.Popen(
                command,
                cwd=str(cwd or self.state.root),
                env=merged_env,
                stdin=None if stream else subprocess.DEVNULL,
                stdout=None if stream else subprocess.PIPE,
                stderr=None if stream else subprocess.PIPE,
                text=False,
                start_new_session=True,
            )
        except OSError as exc:
            return RunResult(command, 127, stderr=str(exc))
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._terminate(process)
            stdout, stderr = process.communicate()
            return RunResult(command, process.returncode or -signal.SIGTERM, self._decode(stdout), self._decode(stderr), True)
        return RunResult(command, process.returncode, self._decode(stdout), self._decode(stderr))

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    @staticmethod
    def _decode(value: bytes | None) -> str:
        if not value:
            return ""
        if len(value) > MAX_CAPTURE_BYTES:
            value = value[-MAX_CAPTURE_BYTES:]
        return value.decode(errors="replace").strip()


def docker_command(state: AppState) -> list[str] | None:
    docker = shutil.which("docker")
    if not docker:
        return None
    runner = Runner(state)
    direct = runner.run([docker, "ps"], timeout=5)
    if direct.ok:
        return [docker]
    sudo = shutil.which("sudo")
    if sudo and runner.run([sudo, "-n", docker, "ps"], timeout=5).ok:
        return [sudo, "-n", docker]
    return [docker]


def compose_command(state: AppState, *, extras: bool = False) -> list[str]:
    docker = docker_command(state)
    if docker is None:
        state.fail("docker", "Docker is not installed.", 3)
    command = [*docker, "compose"]
    if extras:
        command.extend(["--profile", "extras"])
    return command
