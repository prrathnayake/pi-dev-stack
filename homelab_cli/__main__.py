from __future__ import annotations

import json
import sys

import click

from .app import app
from .context import EXIT_USAGE
from .registry import RegistryError, load_registry


LEGACY = {
    "up": "stack start",
    "down": "stack stop",
    "restart": "stack restart",
    "status": "stack status",
    "logs": "service logs <service>",
    "doctor": "system doctor",
    "validate": "system validate",
    "install": "setup",
}

PUBLIC_GROUPS = {
    "overview", "setup", "stack", "service", "tunnel", "backup", "config",
    "system", "pihole", "update", "data", "completion",
}
SERVICE_ACTIONS = {"start", "stop", "restart", "status", "logs", "inspect", "shell", "url"}


def _legacy_message(argv: list[str]) -> str | None:
    tokens = [arg for arg in argv if arg not in {"--json", "--no-color", "--verbose", "-v", "--dry-run", "--yes", "-y"}]
    if not tokens:
        return None
    first = tokens[0]
    if first in LEGACY:
        return f"Legacy command '{first}' was removed. Use: homelab {LEGACY[first]}"
    if first == "pihole" and len(tokens) > 1 and tokens[1] in SERVICE_ACTIONS:
        return f"Service lifecycle commands moved. Use: homelab service {tokens[1]} pihole"
    try:
        if first not in PUBLIC_GROUPS and first in load_registry().names:
            action = tokens[1] if len(tokens) > 1 else "status"
            return f"Direct service aliases were removed. Use: homelab service {action} {first}"
    except RegistryError:
        pass
    return None


def main() -> None:
    argv = sys.argv[1:]
    message = _legacy_message(argv)
    if message:
        if "--json" in argv:
            print(json.dumps({"ok": False, "command": " ".join(argv), "data": None, "warnings": [], "errors": [message]}))
        else:
            print(message, file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    try:
        result = app(standalone_mode=False)
        if isinstance(result, int) and result:
            raise SystemExit(result)
    except click.ClickException as exc:
        if "--json" in argv:
            print(json.dumps({"ok": False, "command": " ".join(argv), "data": None, "warnings": [], "errors": [exc.format_message()]}))
        else:
            exc.show()
        raise SystemExit(EXIT_USAGE)
    except click.exceptions.Exit as exc:
        raise SystemExit(exc.exit_code)


if __name__ == "__main__":
    main()
