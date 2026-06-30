"""Data sources for the homelab TUI.

All Docker interactions go through subprocess calls — no docker SDK dependency.
System stats use psutil. The service registry is read directly from
config/services.tsv, mirroring the semantics of lib/registry.sh.
"""
from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
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


def action(service: str, action_name: str) -> tuple[int, str, str]:
    return run_homelab(service, action_name, timeout=60)


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
