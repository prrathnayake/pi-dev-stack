from __future__ import annotations

import json
import os
import re
import shutil
import signal
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from .context import AppState
from .registry import Service

URL_PATTERN = re.compile(r"https://[-0-9a-z]+\.trycloudflare\.com")


class TunnelError(RuntimeError):
    pass


def state_path(root: Path) -> Path:
    return root / "state" / "tunnels.json"


def load_tunnels(root: Path) -> dict[str, dict[str, object]]:
    path = state_path(root)
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_tunnels(root: Path, value: dict[str, dict[str, object]]) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _pid_is_tunnel(pid: int) -> bool:
    try:
        command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ")
        return b"cloudflared" in command and b"tunnel --url" in command
    except OSError:
        return False


def wait_for_origin(service: Service, timeout: float = 60) -> None:
    if not service.port:
        raise TunnelError(f"Service has no local origin port: {service.name}")
    url = f"{service.scheme}://127.0.0.1:{service.port}"
    context = ssl._create_unverified_context() if service.scheme == "https" else None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3, context=context):
                return
        except urllib.error.HTTPError:
            return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    raise TunnelError(f"Origin did not become reachable: {url}")


def start_tunnel(state: AppState, service: Service, timeout: float = 90) -> dict[str, object]:
    binary = shutil.which("cloudflared")
    if not binary:
        raise TunnelError("cloudflared is not installed")
    wait_for_origin(service)
    logs = state.root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / f"tunnel-{service.name}.log"
    origin = f"{service.scheme}://127.0.0.1:{service.port}"
    with log_path.open("wb") as output:
        process = subprocess.Popen(
            [binary, "tunnel", "--url", origin],
            cwd=state.root,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    deadline = time.monotonic() + timeout
    url = ""
    while time.monotonic() < deadline and process.poll() is None:
        match = URL_PATTERN.search(log_path.read_text(encoding="utf-8", errors="replace"))
        if match:
            url = match.group(0)
            break
        time.sleep(1)
    if not url:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        raise TunnelError(f"Tunnel failed to start; inspect {log_path}")
    record: dict[str, object] = {"pid": process.pid, "url": url, "origin": origin, "log": str(log_path)}
    current = load_tunnels(state.root)
    current[service.name] = record
    save_tunnels(state.root, current)
    return record


def stop_tunnel(root: Path, service_name: str) -> bool:
    current = load_tunnels(root)
    record = current.get(service_name)
    if not record:
        return False
    pid = int(record.get("pid", 0))
    if pid > 0 and _pid_is_tunnel(pid):
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    current.pop(service_name, None)
    save_tunnels(root, current)
    return True


def tunnel_status(root: Path) -> dict[str, dict[str, object]]:
    current = load_tunnels(root)
    for record in current.values():
        record["running"] = _pid_is_tunnel(int(record.get("pid", 0)))
    return current
