"""Data sources for the homelab TUI.

All Docker interactions go through subprocess calls — no docker SDK dependency.
System stats use psutil. The service registry is read directly from
config/services.tsv, mirroring the semantics of lib/registry.sh.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


def _repo_root() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent


def _docker_cmd() -> list[str]:
    docker = shutil.which("docker")
    if docker is None:
        return ["docker"]
    if subprocess.run(
        [docker, "ps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode == 0:
        return [docker]
    if subprocess.run(
        ["sudo", "docker", "ps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode == 0:
        return ["sudo", "docker"]
    return [docker]


_DOCKER: list[str] | None = None


def docker_cmd() -> list[str]:
    global _DOCKER
    if _DOCKER is None:
        _DOCKER = _docker_cmd()
    return _DOCKER


def docker_available() -> bool:
    try:
        r = subprocess.run(
            docker_cmd() + ["ps"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return r.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


# ---------------------------------------------------------------------------
# Service registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ServiceInfo:
    name: str
    profile: str
    group: str
    port: str
    scheme: str
    path: str
    aliases: str
    tunnel: str
    tunnel_groups: str
    url_note: str

    @property
    def has_web(self) -> bool:
        return bool(self.port) or bool(self.url_note)

    @property
    def url(self) -> str:
        if self.url_note:
            return self.url_note
        if not self.port:
            return f"{self.name} has no web UI"
        return f"{self.name}: {self.scheme}://localhost:{self.port}{self.path}"

    @property
    def is_tunnable(self) -> bool:
        return self.tunnel == "yes"


_REGISTRY: list[ServiceInfo] | None = None


def load_registry() -> list[ServiceInfo]:
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY
    path = _repo_root() / "config" / "services.tsv"
    services: list[ServiceInfo] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter="|")
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            while len(row) < 10:
                row.append("")
            services.append(ServiceInfo(*row[:10]))
    _REGISTRY = services
    return services


def service_names() -> list[str]:
    return [s.name for s in load_registry()]


def core_services() -> list[str]:
    return [s.name for s in load_registry() if s.profile == "core"]


def extra_services() -> list[str]:
    return [s.name for s in load_registry() if s.profile == "extras"]


# ---------------------------------------------------------------------------
# Container status
# ---------------------------------------------------------------------------

@dataclass
class ContainerStatus:
    name: str
    service: str
    state: str
    status: str
    image: str
    uptime: str = ""
    health: str = ""
    ports: str = ""


def _match_service(container_name: str, image: str) -> str:
    if container_name.startswith("pi-"):
        suffix = container_name[3:]
        for svc in load_registry():
            if svc.name == suffix:
                return svc.name
        return suffix
    return container_name


def containers() -> list[ContainerStatus]:
    if not docker_available():
        return []
    try:
        result = subprocess.run(
            docker_cmd() + ["compose", "--profile", "extras", "ps", "--format", "json"],
            capture_output=True, text=True, timeout=10,
        )
    except subprocess.SubprocessError:
        return []
    if result.returncode != 0:
        return []
    containers_list: list[ContainerStatus] = []
    import json
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        c = ContainerStatus(
            name=obj.get("Name", obj.get("name", "")),
            service=_match_service(
                obj.get("Name", obj.get("name", "")),
                obj.get("Image", obj.get("image", "")),
            ),
            state=obj.get("State", obj.get("state", "")),
            status=obj.get("Status", obj.get("status", "")),
            image=obj.get("Image", obj.get("image", "")),
            ports=obj.get("Ports", obj.get("ports", "")),
        )
        if c.status and c.status != c.state:
            c.uptime = c.status
        containers_list.append(c)
    return containers_list


# ---------------------------------------------------------------------------
# Container resource usage
# ---------------------------------------------------------------------------

@dataclass
class ContainerStats:
    name: str
    cpu_percent: str
    mem_usage: str
    mem_percent: str
    net_io: str
    block_io: str


def container_stats() -> dict[str, ContainerStats]:
    if not docker_available():
        return {}
    try:
        result = subprocess.run(
            docker_cmd() + ["stats", "--no-stream", "--format",
                            "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"],
            capture_output=True, text=True, timeout=15,
        )
    except subprocess.SubprocessError:
        return {}
    if result.returncode != 0:
        return {}
    stats: dict[str, ContainerStats] = {}
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        name = parts[0].lstrip("/")
        stats[_match_service(name, "")] = ContainerStats(
            name=name,
            cpu_percent=parts[1],
            mem_usage=parts[2],
            mem_percent=parts[3],
            net_io=parts[4],
            block_io=parts[5],
        )
    return stats


# ---------------------------------------------------------------------------
# System stats
# ---------------------------------------------------------------------------

@dataclass
class SystemStats:
    cpu_percent: float
    cpu_count: int
    cpu_per_core: list[float] = field(default_factory=list)
    mem_total: int = 0
    mem_used: int = 0
    mem_percent: float = 0.0
    swap_total: int = 0
    swap_used: int = 0
    swap_percent: float = 0.0
    disk_total: int = 0
    disk_used: int = 0
    disk_percent: float = 0.0
    load_avg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    uptime_seconds: int = 0
    net_sent: int = 0
    net_recv: int = 0
    temp_celsius: float | None = None
    hostname: str = ""
    os_name: str = ""


def system_stats() -> SystemStats:
    try:
        import psutil
    except ImportError:
        return SystemStats(cpu_percent=0.0, cpu_count=0, hostname=os.uname().nodename)

    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count() or 0
    try:
        cpu_per_core = psutil.cpu_percent(interval=0.3, percpu=True)
    except Exception:
        cpu_per_core = []

    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()

    try:
        disk = psutil.disk_usage("/")
    except Exception:
        disk = None

    load_avg = (0.0, 0.0, 0.0)
    try:
        load_avg = tuple(float(x) for x in os.getloadavg())  # type: ignore[arg-type]
    except (AttributeError, OSError):
        pass

    uptime_seconds = 0
    try:
        uptime_seconds = int(psutil.boot_time() > 0 and (time.time() - psutil.boot_time()))
    except Exception:
        pass

    net_sent = net_recv = 0
    try:
        net = psutil.net_io_counters()
        net_sent, net_recv = net.bytes_sent, net.bytes_recv
    except Exception:
        pass

    temp_celsius = None
    try:
        temps = psutil.sensors_temperatures()
        for key in ("cpu_thermal", "cpu-thermal", "coretemp", "soc_thermal"):
            if key in temps and temps[key]:
                temp_celsius = temps[key][0].current
                break
    except Exception:
        pass

    hostname = os.uname().nodename
    os_name = ""
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    os_name = line.split("=", 1)[1].strip().strip('"')
                    break
    except (FileNotFoundError, OSError):
        pass

    return SystemStats(
        cpu_percent=cpu_percent,
        cpu_count=cpu_count,
        cpu_per_core=cpu_per_core,
        mem_total=vm.total,
        mem_used=vm.used,
        mem_percent=vm.percent,
        swap_total=sm.total,
        swap_used=sm.used,
        swap_percent=sm.percent,
        disk_total=disk.total if disk else 0,
        disk_used=disk.used if disk else 0,
        disk_percent=disk.percent if disk else 0.0,
        load_avg=load_avg,
        uptime_seconds=uptime_seconds,
        net_sent=net_sent,
        net_recv=net_recv,
        temp_celsius=temp_celsius,
        hostname=hostname,
        os_name=os_name,
    )


# ---------------------------------------------------------------------------
# Actions — call homelab CLI under the hood
# ---------------------------------------------------------------------------

def run_homelab(*args: str, timeout: int = 30) -> tuple[int, str, str]:
    root = _repo_root()
    homelab = str(root / "homelab")
    try:
        result = subprocess.run(
            [homelab, *args],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(root),
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.SubprocessError as e:
        return 1, "", str(e)


def action(service: str, action_name: str, timeout: int = 60) -> tuple[int, str, str]:
    return run_homelab(service, action_name, timeout=timeout)


# ---------------------------------------------------------------------------
# Log streaming
# ---------------------------------------------------------------------------

def log_stream(service: str, tail: int = 100) -> Iterator[str]:
    root = _repo_root()
    compose = docker_cmd() + ["compose"]
    for svc in load_registry():
        if svc.name == service and svc.profile == "extras":
            compose = docker_cmd() + ["compose", "--profile", "extras"]
            break
    try:
        proc = subprocess.Popen(
            compose + ["logs", "-f", "--tail", str(tail), service],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            cwd=str(root),
        )
    except subprocess.SubprocessError:
        return
    assert proc.stdout is not None
    for line in proc.stdout:
        yield line.rstrip("\n")
    proc.wait()


# ---------------------------------------------------------------------------
# Docker event stream — real-time container state changes
# ---------------------------------------------------------------------------

@dataclass
class DockerEvent:
    type: str
    action: str
    container: str
    service: str
    status: str
    timestamp: str

    @property
    def is_state_change(self) -> bool:
        return self.action in ("start", "stop", "die", "pause", "unpause", "create", "destroy")


def docker_events() -> Iterator[DockerEvent]:
    """Stream docker events in real-time. Blocks until interrupted."""
    if not docker_available():
        return
    try:
        proc = subprocess.Popen(
            docker_cmd() + ["events", "--format", "{{json .}}"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
    except subprocess.SubprocessError:
        return
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        container_name = obj.get("Actor", {}).get("Attributes", {}).get("name", "")
        yield DockerEvent(
            type=obj.get("Type", ""),
            action=obj.get("Action", ""),
            container=container_name,
            service=_match_service(container_name, ""),
            status=obj.get("Actor", {}).get("Attributes", {}).get("state", ""),
            timestamp=obj.get("Time", ""),
        )
    proc.wait()


# ---------------------------------------------------------------------------
# Image pull progress — parse docker pull output for layer progress
# ---------------------------------------------------------------------------

@dataclass
class PullLayer:
    layer_id: str
    status: str
    current: int = 0
    total: int = 0
    completed: bool = False

    @property
    def percent(self) -> float | None:
        if self.total > 0:
            return (self.current / self.total) * 100
        return None


def pull_progress(service: str) -> Iterator[dict[str, PullLayer]]:
    """Stream docker compose pull progress, yielding layer states."""
    root = _repo_root()
    compose = docker_cmd() + ["compose"]
    for svc in load_registry():
        if svc.name == service and svc.profile == "extras":
            compose = docker_cmd() + ["compose", "--profile", "extras"]
            break
    try:
        proc = subprocess.Popen(
            compose + ["pull", service],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            cwd=str(root),
        )
    except subprocess.SubprocessError:
        return
    assert proc.stdout is not None
    layers: dict[str, PullLayer] = {}
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        _parse_pull_line(line, layers)
        yield dict(layers)
    proc.wait()


def _parse_pull_line(line: str, layers: dict[str, PullLayer]) -> None:
    if "Pulling from" in line or "Digest:" in line or "Status:" in line:
        return
    parts = line.split(":", 1)
    if len(parts) < 2:
        return
    layer_id = parts[0].strip()
    rest = parts[1].strip()
    if "Pulling fs layer" in rest:
        layers[layer_id] = PullLayer(layer_id=layer_id, status="Pulling fs layer")
    elif "Waiting" in rest:
        layers[layer_id] = PullLayer(layer_id=layer_id, status="Waiting")
    elif "Downloading" in rest:
        layers.setdefault(layer_id, PullLayer(layer_id=layer_id, status="Downloading"))
        layers[layer_id].status = "Downloading"
        _extract_progress(rest, layers[layer_id])
    elif "Extracting" in rest:
        layers.setdefault(layer_id, PullLayer(layer_id=layer_id, status="Extracting"))
        layers[layer_id].status = "Extracting"
        _extract_progress(rest, layers[layer_id])
    elif "Download complete" in rest:
        layers.setdefault(layer_id, PullLayer(layer_id=layer_id, status="Download complete"))
        layers[layer_id].completed = True
        layers[layer_id].status = "Download complete"
    elif "Pull complete" in rest:
        layers.setdefault(layer_id, PullLayer(layer_id=layer_id, status="Pull complete"))
        layers[layer_id].completed = True
        layers[layer_id].status = "Pull complete"
    elif "Already exists" in rest:
        layers[layer_id] = PullLayer(layer_id=layer_id, status="Already exists", completed=True)


def _extract_progress(text: str, layer: PullLayer) -> None:
    m = re.search(r'(\d+(?:\.\d+)?)\s*(B|kB|MB|GB)/(\d+(?:\.\d+)?)\s*(B|kB|MB|GB)', text)
    if m:
        current_val = float(m.group(1))
        current_unit = m.group(2)
        total_val = float(m.group(3))
        total_unit = m.group(4)
        multipliers = {"B": 1, "kB": 1024, "MB": 1024**2, "GB": 1024**3}
        layer.current = int(current_val * multipliers.get(current_unit, 1))
        layer.total = int(total_val * multipliers.get(total_unit, 1))


# ---------------------------------------------------------------------------
# Wait for container to reach running state
# ---------------------------------------------------------------------------

def wait_for_running(service: str, timeout: int = 60) -> bool:
    """Poll until the service container is running. Returns True if running."""
    container = f"pi-{service}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = subprocess.run(
                docker_cmd() + ["inspect", "-f", "{{.State.Status}}", container],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip() == "running":
                return True
        except subprocess.SubprocessError:
            pass
        time.sleep(0.5)
    return False


def container_state(service: str) -> str:
    """Get the state of a single service container."""
    container = f"pi-{service}"
    try:
        result = subprocess.run(
            docker_cmd() + ["inspect", "-f", "{{.State.Status}}", container],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except subprocess.SubprocessError:
        pass
    return "missing"


# ---------------------------------------------------------------------------
# Action with pull progress — start a service, handling image downloads
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    success: bool
    message: str
    pulled: bool = False


def start_service(service: str) -> ActionResult:
    """Start a service, pulling images if needed. Returns result."""
    if not is_service(service):
        return ActionResult(False, f"Unknown service: {service}")
    compose = docker_cmd() + ["compose"]
    for svc in load_registry():
        if svc.name == service and svc.profile == "extras":
            compose = docker_cmd() + ["compose", "--profile", "extras"]
            break
    root = _repo_root()
    try:
        result = subprocess.run(
            compose + ["up", "-d", service],
            capture_output=True, text=True, timeout=120,
            cwd=str(root),
        )
        if result.returncode == 0:
            return ActionResult(True, f"Started {service}")
        return ActionResult(False, f"Failed: {result.stderr.strip()[:200]}")
    except subprocess.SubprocessError as e:
        return ActionResult(False, f"Error: {e}")
