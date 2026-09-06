from __future__ import annotations

import subprocess
import sys

from rich.prompt import IntPrompt, Prompt

from .context import AppState
from .registry import load_registry


def run_guided(state: AppState) -> None:
    choices = {
        1: ("Overview", ["overview"]),
        2: ("List services", ["service", "list"]),
        3: ("Manage a service", None),
        4: ("System doctor", ["system", "doctor"]),
        5: ("Backups", None),
        6: ("Configuration", ["config", "list"]),
        7: ("Quit", []),
    }
    while True:
        state.console.print("\n[bold cyan]Pi Dev Stack[/] guided administration")
        for number, (label, _) in choices.items():
            state.console.print(f"  {number}. {label}")
        selected = IntPrompt.ask("Choose", choices=[str(number) for number in choices], default=1)
        if selected == 7:
            return
        command = choices[selected][1]
        if selected == 3:
            service = Prompt.ask("Service", choices=list(load_registry().names))
            action = Prompt.ask("Action", choices=["status", "start", "stop", "restart", "logs", "url"], default="status")
            command = ["service", action, service]
        elif selected == 5:
            action = Prompt.ask("Backup action", choices=["list", "create", "verify", "restore"], default="list")
            command = ["backup", action]
            if action in {"verify", "restore"}:
                command.append(Prompt.ask("Archive path"))
        assert command is not None
        subprocess.run([sys.executable, "-m", "homelab_cli", *command], cwd=state.root, check=False)
