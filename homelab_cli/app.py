from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import socket
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Annotated

import click
import typer
from typer._completion_shared import get_completion_script, install as install_completion

from .backups import BackupError, create_backup, list_backups, prune_backups, restore_backup, validate_archive
from .configuration import is_secret, mask, read_env, write_env_value
from .context import AppState, EXIT_OPERATION, EXIT_PARTIAL, EXIT_PREREQUISITE, EXIT_USAGE
from .guided import run_guided
from .registry import Registry, RegistryError, Service, load_registry, validate_compose_contract
from .runner import RunResult, Runner, compose_command, docker_command
from .tunnels import TunnelError, start_tunnel, stop_tunnel, tunnel_status

app = typer.Typer(name="homelab", invoke_without_command=True, no_args_is_help=False, help="Administer Pi Dev Stack.")
stack_app = typer.Typer(help="Manage the complete Compose stack.")
service_app = typer.Typer(help="Manage individual services.")
tunnel_app = typer.Typer(help="Manage Cloudflare quick tunnels.")
backup_app = typer.Typer(help="Create, verify, restore, and prune backups.")
config_app = typer.Typer(help="Manage .env configuration safely.")
system_app = typer.Typer(help="Inspect and validate the host and stack.")
pihole_app = typer.Typer(help="Manage Pi-hole.")
update_app = typer.Typer(help="Update the repository and container images.")
data_app = typer.Typer(help="Explicitly purge runtime data.")
completion_app = typer.Typer(help="Show or install shell completion.")

for name, group in (
    ("stack", stack_app), ("service", service_app), ("tunnel", tunnel_app),
    ("backup", backup_app), ("config", config_app), ("system", system_app),
    ("pihole", pihole_app), ("update", update_app), ("data", data_app),
    ("completion", completion_app),
):
    app.add_typer(group, name=name)


class Profile(str, Enum):
    core = "core"
    extras = "extras"
    all = "all"


def _state(ctx: typer.Context) -> AppState:
    return ctx.find_root().obj


def _registry(state: AppState, command: str) -> Registry:
    try:
        return load_registry(state.root / "config" / "services.tsv")
    except RegistryError as exc:
        state.fail(command, str(exc), EXIT_PREREQUISITE)


def _services(state: AppState, names: list[str], command: str) -> list[Service]:
    registry = _registry(state, command)
    selected: list[Service] = []
    try:
        for name in names:
            selected.append(registry.get(name))
    except RegistryError as exc:
        state.fail(command, str(exc), EXIT_USAGE)
    return selected


def _result_data(result: RunResult) -> dict[str, object]:
    return {
        "args": result.args,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "timed_out": result.timed_out,
        "dry_run": result.dry_run,
    }


def _execute(
    state: AppState,
    label: str,
    args: list[str],
    *,
    mutate: bool = False,
    stream: bool = False,
    timeout: float = 60,
) -> RunResult:
    result = Runner(state).run(args, mutate=mutate, stream=stream and not state.json_output, timeout=timeout)
    if not result.ok:
        detail = result.stderr or result.stdout or "Command failed"
        if result.timed_out:
            detail = f"Command timed out after {timeout:g}s. {detail}".strip()
        state.fail(label, detail, EXIT_OPERATION)
    return result


def _emit_result(state: AppState, label: str, result: RunResult, success: str) -> None:
    text = result.stdout or (result.stderr if state.verbose else "") or success
    state.emit(ok=True, command=label, data=_result_data(result), text=text)


def _compose_for(state: AppState, services: list[Service]) -> list[str]:
    return compose_command(state, extras=any(item.is_extra for item in services))


@app.callback()
def main_callback(
    ctx: typer.Context,
    json_output: Annotated[bool, typer.Option("--json", help="Emit one structured JSON result.")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable terminal colors.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show diagnostic details.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print state changes without applying them.")] = False,
    assume_yes: Annotated[bool, typer.Option("--yes", "-y", help="Confirm destructive actions non-interactively.")] = False,
) -> None:
    state = AppState(json_output, no_color, verbose, dry_run, assume_yes)
    ctx.obj = state
    if ctx.invoked_subcommand is None:
        if state.interactive:
            run_guided(state)
        else:
            typer.echo(ctx.get_help())


def _parse_compose_ps(output: str) -> list[dict[str, object]]:
    if not output.strip():
        return []
    try:
        parsed = json.loads(output)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError:
        pass
    rows: list[dict[str, object]] = []
    for line in output.splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        except json.JSONDecodeError:
            continue
    return rows


def _memory_info() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            if key in {"MemTotal", "MemAvailable"}:
                values[key] = int(raw.strip().split()[0]) * 1024
    except (OSError, ValueError):
        pass
    return values


@app.command()
def overview(ctx: typer.Context) -> None:
    """Show a one-shot host and service summary."""
    state = _state(ctx)
    disk = shutil.disk_usage(state.root)
    memory = _memory_info()
    system = {
        "hostname": socket.gethostname(), "os": platform.platform(), "architecture": platform.machine(),
        "load": list(os.getloadavg()) if hasattr(os, "getloadavg") else [],
        "disk": {"total": disk.total, "used": disk.used, "free": disk.free}, "memory": memory,
    }
    docker = docker_command(state)
    containers: list[dict[str, object]] = []
    warnings: list[str] = []
    if docker:
        result = Runner(state).run([*docker, "compose", "--profile", "extras", "ps", "--format", "json"], timeout=15)
        if result.ok:
            containers = _parse_compose_ps(result.stdout)
        else:
            warnings.append(result.stderr or "Docker is not accessible")
    else:
        warnings.append("Docker is not installed")
    running = sum(1 for item in containers if str(item.get("State", item.get("state", ""))) == "running")
    text = (
        f"[bold]Host:[/] {system['hostname']} ({system['architecture']})\n"
        f"[bold]Services:[/] {running} running / {len(containers)} present\n"
        f"[bold]Disk free:[/] {disk.free / (1024 ** 3):.1f} GiB"
    )
    state.emit(ok=True, command="overview", data={"system": system, "containers": containers}, warnings=warnings, text=text)


@app.command("setup")
def setup_command(
    ctx: typer.Context,
    install_system: Annotated[bool, typer.Option("--install-system", help="Install missing host packages.")] = False,
) -> None:
    """Prepare configuration and runtime directories."""
    state = _state(ctx)
    runner = Runner(state)
    actions: list[str] = []
    if install_system:
        packages = ["curl", "git", "ca-certificates", "python3-venv"]
        result = runner.run(["sudo", "apt-get", "update"], timeout=300, mutate=True)
        if not result.ok:
            state.fail("setup", result.stderr or "apt-get update failed")
        result = runner.run(["sudo", "apt-get", "install", "-y", *packages], timeout=600, mutate=True)
        if not result.ok:
            state.fail("setup", result.stderr or "Package installation failed")
        actions.append("installed host packages")
        if not shutil.which("docker"):
            install_script = state.root / ".local-state" / "get-docker.sh"
            if not state.dry_run:
                install_script.parent.mkdir(parents=True, exist_ok=True)
            for args in (
                ["curl", "-fsSL", "https://get.docker.com", "-o", str(install_script)],
                ["sudo", "sh", str(install_script)],
            ):
                result = runner.run(args, timeout=600, mutate=True)
                if not result.ok:
                    state.fail("setup", result.stderr or f"Failed: {' '.join(args)}")
            user = os.environ.get("USER")
            if user:
                result = runner.run(["sudo", "usermod", "-aG", "docker", user], timeout=30, mutate=True)
                if not result.ok:
                    state.fail("setup", result.stderr or "Unable to add the current user to the docker group")
            actions.append("installed Docker Engine and Compose")
        if not shutil.which("cloudflared"):
            architecture = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64", "amd64": "amd64"}.get(platform.machine().lower())
            if not architecture:
                state.fail("setup", f"Unsupported cloudflared architecture: {platform.machine()}", EXIT_PREREQUISITE)
            package = state.root / ".local-state" / f"cloudflared-linux-{architecture}.deb"
            if not state.dry_run:
                package.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{architecture}.deb"
            for args in (["curl", "-fL", url, "-o", str(package)], ["sudo", "dpkg", "-i", str(package)]):
                result = runner.run(args, timeout=300, mutate=True)
                if not result.ok:
                    state.fail("setup", result.stderr or f"Failed: {' '.join(args)}")
            actions.append(f"installed cloudflared for {architecture}")
    runtime_directories = ["logs", "state", ".local-state", "backups", "media"]
    runtime_directories.extend(f"data/{item.name}" for item in _registry(state, "setup").services)
    runtime_directories.extend(
        [
            "data/plex/config", "data/dockge/stacks", "data/filebrowser/database",
            "data/filebrowser/config", "data/gitea-config", "data/netdata/config",
            "data/netdata/lib", "data/netdata/cache", "data/mosquitto/data", "data/mosquitto/log",
        ]
    )
    for directory in runtime_directories:
        path = state.root / directory
        if not state.dry_run:
            path.mkdir(parents=True, exist_ok=True)
        actions.append(f"ensured {directory}/")
    env_path = state.root / ".env"
    if not env_path.exists():
        example = state.root / ".env.example"
        if not example.exists():
            state.fail("setup", ".env.example is missing", EXIT_PREREQUISITE)
        if not state.dry_run:
            shutil.copy2(example, env_path)
        actions.append("created .env from .env.example")
    state.emit(ok=True, command="setup", data={"actions": actions, "dry_run": state.dry_run}, text="Setup complete.\n" + "\n".join(f"- {item}" for item in actions))


def _profile_services(registry: Registry, profile: Profile) -> list[Service]:
    return registry.select(profile=profile.value)


def _stack_action(state: AppState, action: str, profile: Profile, volumes: bool = False) -> None:
    registry = _registry(state, f"stack {action}")
    selected = _profile_services(registry, profile)
    compose = compose_command(state, extras=profile in {Profile.extras, Profile.all})
    names = [item.name for item in selected]
    if action == "start":
        args = [*compose, "up", "-d", *([] if profile is Profile.all else names)]
    elif action == "restart":
        args = [*compose, "restart", *names]
    elif action == "status":
        args = [*compose, "ps", *names]
    elif profile is Profile.all:
        args = [*compose, "down", "--remove-orphans"]
        if volumes:
            if not state.dry_run:
                state.confirm("stack stop", "Stop all services and remove Compose volumes?")
            args.insert(-1, "--volumes")
    else:
        args = [*compose, "stop", *names]
    result = _execute(state, f"stack {action}", args, mutate=action != "status", timeout=180)
    _emit_result(state, f"stack {action}", result, f"Stack {action} completed for {profile.value}.")


@stack_app.command("start")
def stack_start(ctx: typer.Context, profile: Annotated[Profile, typer.Option()] = Profile.core) -> None:
    _stack_action(_state(ctx), "start", profile)


@stack_app.command("stop")
def stack_stop(ctx: typer.Context, profile: Annotated[Profile, typer.Option()] = Profile.all, volumes: Annotated[bool, typer.Option("--volumes")] = False) -> None:
    _stack_action(_state(ctx), "stop", profile, volumes)


@stack_app.command("restart")
def stack_restart(ctx: typer.Context, profile: Annotated[Profile, typer.Option()] = Profile.core) -> None:
    _stack_action(_state(ctx), "restart", profile)


@stack_app.command("status")
def stack_status(ctx: typer.Context, profile: Annotated[Profile, typer.Option()] = Profile.all) -> None:
    _stack_action(_state(ctx), "status", profile)


@service_app.command("list")
def service_list(ctx: typer.Context, profile: Annotated[Profile, typer.Option()] = Profile.all, group: Annotated[str | None, typer.Option()] = None) -> None:
    state = _state(ctx)
    rows = [{"name": item.name, "profile": item.profile, "group": item.group, "url": item.url} for item in _registry(state, "service list").select(profile=profile.value, group=group)]
    text = "\n".join(f"{row['name']:<18} {row['profile']:<7} {row['group']:<12} {row['url']}" for row in rows)
    state.emit(ok=True, command="service list", data=rows, text=text or "No matching services.")


def _service_action(state: AppState, action: str, names: list[str]) -> None:
    if not names:
        state.fail(f"service {action}", "At least one service is required.", EXIT_USAGE)
    services = _services(state, names, f"service {action}")
    if action == "start":
        args = [*_compose_for(state, services), "up", "-d", *[item.name for item in services]]
    elif action == "status":
        args = [*_compose_for(state, services), "ps", *[item.name for item in services]]
    else:
        args = [*_compose_for(state, services), action, *[item.name for item in services]]
    result = _execute(state, f"service {action}", args, mutate=action != "status", timeout=180)
    _emit_result(state, f"service {action}", result, f"Service {action} completed: {', '.join(names)}")


@service_app.command("start")
def service_start(ctx: typer.Context, services: list[str] = typer.Argument(...)) -> None:
    _service_action(_state(ctx), "start", services)


@service_app.command("stop")
def service_stop(ctx: typer.Context, services: list[str] = typer.Argument(...)) -> None:
    _service_action(_state(ctx), "stop", services)


@service_app.command("restart")
def service_restart(ctx: typer.Context, services: list[str] = typer.Argument(...)) -> None:
    _service_action(_state(ctx), "restart", services)


@service_app.command("status")
def service_status(ctx: typer.Context, services: list[str] = typer.Argument(...)) -> None:
    _service_action(_state(ctx), "status", services)


@service_app.command("logs")
def service_logs(
    ctx: typer.Context,
    service: str,
    tail: Annotated[int, typer.Option(min=1, max=10000)] = 100,
    since: Annotated[str | None, typer.Option()] = None,
    follow: Annotated[bool, typer.Option("--follow", "-f")] = False,
) -> None:
    state = _state(ctx)
    selected = _services(state, [service], "service logs")
    if follow and state.json_output:
        state.fail("service logs", "--follow cannot be combined with --json.", EXIT_USAGE)
    args = [*_compose_for(state, selected), "logs", "--tail", str(tail)]
    if since:
        args.extend(["--since", since])
    if follow:
        args.append("--follow")
    args.append(selected[0].name)
    result = _execute(state, "service logs", args, stream=follow, timeout=86400 if follow else 60)
    if not follow:
        _emit_result(state, "service logs", result, "No logs returned.")


@service_app.command("inspect")
def service_inspect(ctx: typer.Context, service: str) -> None:
    state = _state(ctx)
    selected = _services(state, [service], "service inspect")[0]
    docker = docker_command(state)
    if not docker:
        state.fail("service inspect", "Docker is not installed.", EXIT_PREREQUISITE)
    result = _execute(state, "service inspect", [*docker, "inspect", f"pi-{selected.name}"])
    _emit_result(state, "service inspect", result, "")


@service_app.command("shell")
def service_shell(ctx: typer.Context, service: str) -> None:
    state = _state(ctx)
    selected = _services(state, [service], "service shell")[0]
    if state.json_output:
        state.fail("service shell", "Interactive shells cannot use --json.", EXIT_USAGE)
    docker = docker_command(state)
    if not docker:
        state.fail("service shell", "Docker is not installed.", EXIT_PREREQUISITE)
    _execute(state, "service shell", [*docker, "exec", "-it", f"pi-{selected.name}", "sh"], stream=True)


@service_app.command("url")
def service_url(ctx: typer.Context, service: str) -> None:
    state = _state(ctx)
    selected = _services(state, [service], "service url")[0]
    state.emit(ok=True, command="service url", data={"service": selected.name, "url": selected.url}, text=selected.url)


@backup_app.command("create")
def backup_create(ctx: typer.Context, include_media: Annotated[bool, typer.Option("--include-media")] = False) -> None:
    state = _state(ctx)
    if state.dry_run:
        state.emit(ok=True, command="backup create", data={"include_media": include_media, "dry_run": True}, text="DRY RUN: create and verify backup")
        return
    try:
        path = create_backup(state.root, include_media=include_media)
    except BackupError as exc:
        state.fail("backup create", str(exc))
    state.emit(ok=True, command="backup create", data={"path": str(path), "include_media": include_media}, text=f"Backup created and verified: {path}")


@backup_app.command("list")
def backup_list(ctx: typer.Context) -> None:
    state = _state(ctx)
    rows = [{"path": str(path), "size": path.stat().st_size, "modified": path.stat().st_mtime} for path in list_backups(state.root)]
    state.emit(ok=True, command="backup list", data=rows, text="\n".join(item["path"] for item in rows) or "No backups found.")


@backup_app.command("verify")
def backup_verify(ctx: typer.Context, archive: Path) -> None:
    state = _state(ctx)
    errors = validate_archive(archive.resolve())
    if errors:
        state.fail("backup verify", "; ".join(errors))
    state.emit(ok=True, command="backup verify", data={"path": str(archive)}, text=f"Backup is valid: {archive}")


@backup_app.command("restore")
def backup_restore(ctx: typer.Context, archive: Path) -> None:
    state = _state(ctx)
    archive = archive.resolve()
    errors = validate_archive(archive)
    if errors:
        state.fail("backup restore", "; ".join(errors))
    if state.dry_run:
        state.emit(ok=True, command="backup restore", data={"path": str(archive), "dry_run": True}, text=f"DRY RUN: restore {archive}")
        return
    state.confirm("backup restore", f"Restore {archive} and replace matching runtime paths?")
    try:
        rollback = restore_backup(state.root, archive)
    except BackupError as exc:
        state.fail("backup restore", str(exc))
    state.emit(ok=True, command="backup restore", data={"path": str(archive), "rollback": str(rollback)}, text=f"Restore complete. Previous files: {rollback}")


@backup_app.command("prune")
def backup_prune(ctx: typer.Context, days: Annotated[int, typer.Option(min=1, max=3650)] = 30) -> None:
    state = _state(ctx)
    cutoff = time.time() - days * 86400
    targets = [path for path in list_backups(state.root) if path.stat().st_mtime < cutoff]
    if state.dry_run:
        state.emit(ok=True, command="backup prune", data={"paths": [str(path) for path in targets], "dry_run": True}, text=f"Would delete {len(targets)} backup(s).")
        return
    if targets:
        state.confirm("backup prune", f"Delete {len(targets)} backup(s) older than {days} days?")
    shown = prune_backups(state.root, days)
    state.emit(ok=True, command="backup prune", data={"paths": [str(path) for path in shown], "dry_run": state.dry_run}, text=f"{'Would delete' if state.dry_run else 'Deleted'} {len(shown)} backup(s).")


@config_app.command("init")
def config_init(ctx: typer.Context) -> None:
    state = _state(ctx)
    target, source = state.root / ".env", state.root / ".env.example"
    if target.exists():
        state.fail("config init", ".env already exists.", EXIT_USAGE)
    if not source.exists():
        state.fail("config init", ".env.example is missing.", EXIT_PREREQUISITE)
    if not state.dry_run:
        shutil.copy2(source, target)
    state.emit(ok=True, command="config init", data={"path": str(target), "dry_run": state.dry_run}, text=f"{'Would create' if state.dry_run else 'Created'} {target}")


@config_app.command("list")
def config_list(ctx: typer.Context, show_secrets: Annotated[bool, typer.Option("--show-secrets")] = False) -> None:
    state = _state(ctx)
    if show_secrets:
        state.confirm("config list", "Reveal all configuration secrets?")
    values = read_env(state.root / ".env")
    shown = {key: value if show_secrets or not is_secret(key) else mask(value) for key, value in values.items()}
    state.emit(ok=True, command="config list", data=shown, text="\n".join(f"{key}={value}" for key, value in shown.items()) or ".env is empty or missing.")


@config_app.command("get")
def config_get(ctx: typer.Context, key: str, show_secrets: Annotated[bool, typer.Option("--show-secrets")] = False) -> None:
    state = _state(ctx)
    values = read_env(state.root / ".env")
    if key not in values:
        state.fail("config get", f"Configuration key not found: {key}", EXIT_USAGE)
    if show_secrets and is_secret(key):
        state.confirm("config get", f"Reveal secret value for {key}?")
    value = values[key] if show_secrets or not is_secret(key) else mask(values[key])
    state.emit(ok=True, command="config get", data={"key": key, "value": value}, text=value)


@config_app.command("set")
def config_set(ctx: typer.Context, key: str, value: Annotated[str | None, typer.Option("--value")] = None, stdin: Annotated[bool, typer.Option("--stdin")] = False) -> None:
    state = _state(ctx)
    if value is not None and stdin:
        state.fail("config set", "Use either --value or --stdin, not both.", EXIT_USAGE)
    if stdin:
        value = sys.stdin.read().rstrip("\n")
    elif value is None:
        if not state.interactive:
            state.fail("config set", "Provide --value or --stdin in non-interactive mode.", EXIT_USAGE)
        value = typer.prompt(f"Value for {key}", hide_input=is_secret(key))
    if state.dry_run:
        backup = None
    else:
        try:
            backup = write_env_value(state.root, key, value)
        except (OSError, ValueError) as exc:
            state.fail("config set", str(exc))
    state.emit(ok=True, command="config set", data={"key": key, "value": mask(value) if is_secret(key) else value, "backup": str(backup) if backup else None, "dry_run": state.dry_run}, text=f"{'Would update' if state.dry_run else 'Updated'} {key}.")


@config_app.command("unset")
def config_unset(ctx: typer.Context, key: str) -> None:
    state = _state(ctx)
    if not state.dry_run:
        state.confirm("config unset", f"Remove {key} from .env?")
    backup = None if state.dry_run else write_env_value(state.root, key, None)
    state.emit(ok=True, command="config unset", data={"key": key, "backup": str(backup) if backup else None, "dry_run": state.dry_run}, text=f"{'Would remove' if state.dry_run else 'Removed'} {key}.")


@config_app.command("edit")
def config_edit(ctx: typer.Context) -> None:
    state = _state(ctx)
    if state.json_output:
        state.fail("config edit", "Interactive editing cannot use --json.", EXIT_USAGE)
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        state.fail("config edit", "Set VISUAL or EDITOR first.", EXIT_PREREQUISITE)
    target = state.root / ".env"
    if not target.exists():
        state.fail("config edit", "Run 'homelab config init' first.", EXIT_PREREQUISITE)
    result = _execute(state, "config edit", [*shlex.split(editor), str(target)], stream=True, mutate=True, timeout=86400)
    _emit_result(state, "config edit", result, "Configuration updated.")


@config_app.command("validate")
def config_validate(ctx: typer.Context) -> None:
    state = _state(ctx)
    example, current = read_env(state.root / ".env.example"), read_env(state.root / ".env")
    errors = [f"Missing configuration key: {key}" for key in example if key not in current]
    warnings = [f"Default placeholder remains: {key}" for key, value in current.items() if "change_this" in value or value == "change_me_now"]
    if errors:
        state.emit(ok=False, command="config validate", data={"keys": sorted(current)}, warnings=warnings, errors=errors)
        raise typer.Exit(EXIT_OPERATION)
    state.emit(ok=True, command="config validate", data={"keys": sorted(current)}, warnings=warnings, text="Configuration is structurally valid.")


def _system_checks(state: AppState) -> tuple[dict[str, object], list[str]]:
    registry = _registry(state, "system validate")
    contract = validate_compose_contract(registry, state.root / "docker-compose.yml")
    docker = docker_command(state)
    checks: dict[str, object] = {
        "python": platform.python_version(), "architecture": platform.machine(),
        "env": (state.root / ".env").exists(), "registry_services": len(registry.services),
        "docker_installed": docker is not None, "compose_contract": not contract,
    }
    errors = list(contract)
    if docker:
        result = Runner(state).run([*docker, "compose", "--profile", "extras", "config"], timeout=30)
        checks["compose_config"] = result.ok
        if not result.ok:
            errors.append(result.stderr or "Docker Compose configuration is invalid")
    else:
        checks["compose_config"] = False
        errors.append("Docker is not installed")
    if not checks["env"]:
        errors.append(".env is missing")
    return checks, errors


@system_app.command("info")
def system_info(ctx: typer.Context) -> None:
    state = _state(ctx)
    data = {"hostname": socket.gethostname(), "os": platform.platform(), "architecture": platform.machine(), "python": platform.python_version(), "user": os.environ.get("USER", "")}
    state.emit(ok=True, command="system info", data=data, text="\n".join(f"{key}: {value}" for key, value in data.items()))


@system_app.command("validate")
def system_validate(ctx: typer.Context) -> None:
    state = _state(ctx)
    checks, errors = _system_checks(state)
    if errors:
        state.emit(ok=False, command="system validate", data=checks, errors=errors)
        raise typer.Exit(EXIT_OPERATION)
    state.emit(ok=True, command="system validate", data=checks, text="System and Compose configuration are valid.")


@system_app.command("doctor")
def system_doctor(ctx: typer.Context, fix: Annotated[bool, typer.Option("--fix")] = False) -> None:
    state = _state(ctx)
    fixed: list[str] = []
    if fix:
        for directory in ("data", "logs", "state", ".local-state", "backups", "media"):
            path = state.root / directory
            if not state.dry_run:
                path.mkdir(parents=True, exist_ok=True)
            fixed.append(f"ensured {directory}/")
        if not (state.root / ".env").exists() and (state.root / ".env.example").exists():
            if not state.dry_run:
                shutil.copy2(state.root / ".env.example", state.root / ".env")
            fixed.append("created .env")
    checks, errors = _system_checks(state)
    if errors:
        state.emit(ok=False, command="system doctor", data={"checks": checks, "fixed": fixed}, errors=errors)
        raise typer.Exit(EXIT_PARTIAL if fixed else EXIT_OPERATION)
    state.emit(ok=True, command="system doctor", data={"checks": checks, "fixed": fixed}, text="No system issues found.")


def _pihole(ctx: typer.Context, args: list[str], *, mutate: bool = True, label: str) -> None:
    state = _state(ctx)
    _services(state, ["pihole"], label)
    docker = docker_command(state)
    if not docker:
        state.fail(label, "Docker is not installed.", EXIT_PREREQUISITE)
    result = _execute(state, label, [*docker, "exec", "pi-pihole", "pihole", *args], mutate=mutate, timeout=180)
    _emit_result(state, label, result, f"{label} completed.")


@pihole_app.command("allow")
def pihole_allow(ctx: typer.Context, domain: str) -> None:
    _pihole(ctx, ["allow", domain], label="pihole allow")


@pihole_app.command("block")
def pihole_block(ctx: typer.Context, domain: str) -> None:
    _pihole(ctx, ["deny", domain], label="pihole block")


@pihole_app.command("disable")
def pihole_disable(ctx: typer.Context, seconds: Annotated[int, typer.Argument(min=1)] = 60) -> None:
    _pihole(ctx, ["disable", str(seconds)], label="pihole disable")


@pihole_app.command("enable")
def pihole_enable(ctx: typer.Context) -> None:
    _pihole(ctx, ["enable"], label="pihole enable")


@pihole_app.command("gravity")
def pihole_gravity(ctx: typer.Context) -> None:
    _pihole(ctx, ["-g"], label="pihole gravity")


@pihole_app.command("stats")
def pihole_stats(ctx: typer.Context) -> None:
    _pihole(ctx, ["-c"], mutate=False, label="pihole stats")


@pihole_app.command("password")
def pihole_password(ctx: typer.Context, value: Annotated[str | None, typer.Option("--value")] = None, stdin: Annotated[bool, typer.Option("--stdin")] = False) -> None:
    state = _state(ctx)
    if value is not None and stdin:
        state.fail("pihole password", "Use either --value or --stdin.", EXIT_USAGE)
    if stdin:
        value = sys.stdin.read().rstrip("\n")
    elif value is None:
        if not state.interactive:
            state.fail("pihole password", "Provide --value or --stdin.", EXIT_USAGE)
        value = typer.prompt("New Pi-hole password", hide_input=True, confirmation_prompt=True)
    _pihole(ctx, ["setpassword", value], label="pihole password")


def _tunnel_action(state: AppState, action: str, target: str) -> None:
    registry = _registry(state, f"tunnel {action}")
    try:
        services = registry.tunnel_targets(target)
    except RegistryError as exc:
        state.fail(f"tunnel {action}", str(exc), EXIT_USAGE)
    if state.dry_run:
        state.emit(ok=True, command=f"tunnel {action}", data={"services": [item.name for item in services], "dry_run": True}, text=f"DRY RUN: {action} tunnels for {', '.join(item.name for item in services)}")
        return
    results: dict[str, object] = {}
    errors: list[str] = []
    for service in services:
        try:
            if action in {"start", "stop", "restart"}:
                results[service.name] = {"stopped": stop_tunnel(state.root, service.name)}
            if action in {"start", "restart"}:
                compose = _compose_for(state, [service])
                started = Runner(state).run([*compose, "up", "-d", service.name], mutate=True, timeout=180)
                if not started.ok:
                    raise TunnelError(started.stderr or f"Unable to start {service.name}")
                record = start_tunnel(state, service)
                results[service.name] = record
                if service.name == "n8n":
                    write_env_value(state.root, "N8N_WEBHOOK_URL", str(record["url"]) + "/")
                    restarted = Runner(state).run([*compose, "up", "-d", "n8n"], mutate=True, timeout=180)
                    if not restarted.ok:
                        raise TunnelError(restarted.stderr or "Unable to refresh n8n")
        except (TunnelError, OSError, ValueError) as exc:
            errors.append(f"{service.name}: {exc}")
    if errors:
        state.emit(ok=False, command=f"tunnel {action}", data=results, errors=errors)
        raise typer.Exit(EXIT_PARTIAL if results else EXIT_OPERATION)
    state.emit(ok=True, command=f"tunnel {action}", data=results, text=f"Tunnel {action} completed for {len(services)} service(s).")


@tunnel_app.command("start")
def tunnel_start(ctx: typer.Context, target: str = "core") -> None:
    _tunnel_action(_state(ctx), "start", target)


@tunnel_app.command("stop")
def tunnel_stop(ctx: typer.Context, target: str = "core") -> None:
    _tunnel_action(_state(ctx), "stop", target)


@tunnel_app.command("restart")
def tunnel_restart(ctx: typer.Context, target: str = "core") -> None:
    _tunnel_action(_state(ctx), "restart", target)


@tunnel_app.command("status")
def tunnel_status_command(ctx: typer.Context) -> None:
    state = _state(ctx)
    data = tunnel_status(state.root)
    state.emit(ok=True, command="tunnel status", data=data, text="\n".join(f"{name}: {'running' if record.get('running') else 'stopped'} {record.get('url', '')}" for name, record in data.items()) or "No saved tunnels.")


@tunnel_app.command("urls")
def tunnel_urls(ctx: typer.Context) -> None:
    state = _state(ctx)
    data = {name: record.get("url") for name, record in tunnel_status(state.root).items()}
    state.emit(ok=True, command="tunnel urls", data=data, text="\n".join(f"{name}: {url}" for name, url in data.items()) or "No saved tunnel URLs.")


@update_app.command("check")
def update_check(ctx: typer.Context) -> None:
    state = _state(ctx)
    local = _execute(state, "update check", ["git", "rev-parse", "HEAD"])
    remote = _execute(state, "update check", ["git", "ls-remote", "origin", "HEAD"], timeout=30)
    remote_head = remote.stdout.split()[0] if remote.stdout else ""
    data = {"local": local.stdout, "remote": remote_head, "update_available": bool(remote_head and remote_head != local.stdout)}
    state.emit(ok=True, command="update check", data=data, text="Update available." if data["update_available"] else "Repository is current.")


@update_app.command("repo")
def update_repo(ctx: typer.Context) -> None:
    state = _state(ctx)
    result = _execute(state, "update repo", ["git", "pull", "--ff-only"], mutate=True, timeout=180)
    _emit_result(state, "update repo", result, "Repository updated.")


@update_app.command("images")
def update_images(ctx: typer.Context, services: list[str] = typer.Argument(None), restart: Annotated[bool, typer.Option("--restart")] = False) -> None:
    state = _state(ctx)
    registry = _registry(state, "update images")
    selected = _services(state, services, "update images") if services else list(registry.services)
    names = [item.name for item in selected]
    compose = _compose_for(state, selected)
    pull = _execute(state, "update images", [*compose, "pull", *names], mutate=True, timeout=1800)
    data: dict[str, object] = {"pull": _result_data(pull)}
    if restart:
        recreate = _execute(state, "update images", [*compose, "up", "-d", *names], mutate=True, timeout=600)
        data["restart"] = _result_data(recreate)
    state.emit(ok=True, command="update images", data=data, text=f"Updated {len(names)} image(s){' and recreated services' if restart else ''}.")


@data_app.command("purge")
def data_purge(
    ctx: typer.Context,
    data_files: Annotated[bool, typer.Option("--data", help="Delete data/.")] = False,
    logs: Annotated[bool, typer.Option("--logs", help="Delete logs/.")] = False,
    volumes: Annotated[bool, typer.Option("--volumes", help="Delete Compose volumes.")] = False,
    media: Annotated[bool, typer.Option("--media", help="Delete media/ explicitly.")] = False,
) -> None:
    state = _state(ctx)
    targets = [name for enabled, name in ((data_files, "data/"), (logs, "logs/"), (volumes, "Compose volumes"), (media, "media/")) if enabled]
    if not targets:
        state.fail("data purge", "Select at least one of --data, --logs, --volumes, or --media.", EXIT_USAGE)
    if state.dry_run:
        state.emit(ok=True, command="data purge", data={"targets": targets, "dry_run": True}, text="DRY RUN: delete " + ", ".join(targets))
        return
    state.confirm("data purge", "Permanently delete: " + ", ".join(targets) + "?")
    if volumes:
        compose = compose_command(state, extras=True)
        _execute(state, "data purge", [*compose, "down", "--volumes", "--remove-orphans"], mutate=True, timeout=180)
    for enabled, name in ((data_files, "data"), (logs, "logs"), (media, "media")):
        if enabled:
            path = (state.root / name).resolve()
            if path.parent != state.root.resolve():
                state.fail("data purge", f"Refusing unsafe path: {path}")
            try:
                if path.exists():
                    shutil.rmtree(path)
                path.mkdir()
            except OSError as exc:
                state.fail("data purge", str(exc))
    state.emit(ok=True, command="data purge", data={"targets": targets}, text="Purged: " + ", ".join(targets))


def _completion(ctx: typer.Context, shell: str, install: bool) -> None:
    state = _state(ctx)
    if shell not in {"bash", "zsh", "fish"}:
        state.fail("completion", "Shell must be bash, zsh, or fish.", EXIT_USAGE)
    if not install:
        script = get_completion_script(prog_name="homelab", complete_var="_HOMELAB_COMPLETE", shell=shell)
        state.emit(ok=True, command="completion show", data={"shell": shell, "script": script}, text=script)
        return
    if state.dry_run:
        state.emit(ok=True, command="completion install", data={"shell": shell, "dry_run": True}, text=f"DRY RUN: install {shell} completion")
        return
    try:
        installed_shell, path = install_completion(shell=shell, prog_name="homelab", complete_var="_HOMELAB_COMPLETE")
    except (OSError, click.ClickException) as exc:
        state.fail("completion install", str(exc))
    state.emit(ok=True, command="completion install", data={"shell": installed_shell, "path": str(path)}, text=f"Installed {installed_shell} completion at {path}")


@completion_app.command("show")
def completion_show(ctx: typer.Context, shell: Annotated[str, typer.Argument()] = "bash") -> None:
    _completion(ctx, shell, False)


@completion_app.command("install")
def completion_install(ctx: typer.Context, shell: Annotated[str, typer.Argument()] = "bash") -> None:
    _completion(ctx, shell, True)
