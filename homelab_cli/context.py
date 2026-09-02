from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn

import typer
from rich.console import Console

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PREREQUISITE = 3
EXIT_OPERATION = 4
EXIT_PARTIAL = 5


def repo_root() -> Path:
    configured = os.environ.get("PI_DEV_STACK_ROOT")
    if configured:
        return Path(configured).resolve()
    current = Path.cwd()
    if (current / "docker-compose.yml").is_file() and (current / "config" / "services.tsv").is_file():
        return current
    return Path(__file__).resolve().parent.parent


@dataclass
class AppState:
    json_output: bool = False
    no_color: bool = False
    verbose: bool = False
    dry_run: bool = False
    assume_yes: bool = False
    root: Path = field(default_factory=repo_root)

    @property
    def console(self) -> Console:
        return Console(no_color=self.no_color, stderr=False)

    @property
    def error_console(self) -> Console:
        return Console(no_color=self.no_color, stderr=True)

    @property
    def interactive(self) -> bool:
        return sys.stdin.isatty() and sys.stdout.isatty()

    def emit(
        self,
        *,
        ok: bool,
        command: str,
        data: Any = None,
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
        text: str | None = None,
    ) -> None:
        warnings = warnings or []
        errors = errors or []
        if self.json_output:
            typer.echo(json.dumps({"ok": ok, "command": command, "data": data, "warnings": warnings, "errors": errors}, default=str))
            return
        if text:
            self.console.print(text)
        for warning in warnings:
            self.error_console.print(f"[yellow]Warning:[/] {warning}")
        for error in errors:
            self.error_console.print(f"[red]Error:[/] {error}")

    def fail(self, command: str, message: str, code: int = EXIT_OPERATION) -> NoReturn:
        self.emit(ok=False, command=command, errors=[message])
        raise typer.Exit(code)

    def confirm(self, command: str, message: str) -> None:
        if self.assume_yes:
            return
        if self.json_output or not self.interactive:
            self.fail(command, f"Confirmation required: {message}. Re-run with --yes.", EXIT_USAGE)
        if not typer.confirm(message, default=False):
            self.fail(command, "Operation cancelled.", EXIT_OPERATION)
