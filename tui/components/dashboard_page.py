"""Dashboard page with compact homelab state graphs."""
from __future__ import annotations

from collections import Counter

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static

from .stat_gauge import StatGauge
from .system_dashboard import _fmt_bytes, _fmt_uptime
from ..data import DockerSnapshot, SystemStats


def _state_bucket(state: str) -> str:
    if state == "running":
        return "running"
    if state in ("dead", "error"):
        return "error"
    if state == "exited":
        return "stopped"
    if state == "paused":
        return "paused"
    return "stopped"


def docker_state_counts(snapshot: DockerSnapshot) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for status in snapshot.statuses.values():
        counts[_state_bucket(status.state)] += 1
    for key in ("running", "stopped", "paused", "error"):
        counts.setdefault(key, 0)
    return dict(counts)


def render_state_bar(counts: dict[str, int], width: int = 34) -> str:
    total = max(sum(counts.values()), 1)
    width = max(12, width)
    running = round(width * counts.get("running", 0) / total)
    error = round(width * counts.get("error", 0) / total)
    paused = round(width * counts.get("paused", 0) / total)
    stopped = max(width - running - error - paused, 0)
    bar = (
        f"[$success]{'█' * running}[/]"
        f"[$error]{'█' * error}[/]"
        f"[$warning]{'█' * paused}[/]"
        f"[$text-muted]{'░' * stopped}[/]"
    )
    return (
        f"{bar}\n"
        f"RUN {counts.get('running', 0)}  "
        f"STOP {counts.get('stopped', 0)}  "
        f"PAUSE {counts.get('paused', 0)}  "
        f"ERR {counts.get('error', 0)}"
    )


class DashboardPage(VerticalScroll):
    """Overview page for homelab system and container state."""

    DEFAULT_CSS = """
    DashboardPage {
        padding: 1 1;
    }
    DashboardPage .dash-section {
        height: auto;
        padding: 0 0 1 0;
    }
    DashboardPage .dash-title {
        height: 1;
        color: $accent;
        text-style: bold;
    }
    DashboardPage .dash-line {
        height: auto;
        color: $text-muted;
    }
    DashboardPage .dash-card {
        width: 1fr;
        height: auto;
        min-width: 20;
        padding: 1 1;
        margin: 0 1 1 0;
        background: $surface;
        border: solid $border-blurred;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._labels: dict[str, Static] = {}
        self._gauges: dict[str, StatGauge] = {}

    def compose(self) -> ComposeResult:
        with Vertical(classes="dash-section"):
            yield Static("DASHBOARD", classes="dash-title")
            yield Static("Waiting for system snapshot...", id="dash-host", classes="dash-line")
        with Horizontal(classes="dash-section"):
            with Vertical(classes="dash-card"):
                yield Static("SYSTEM", classes="dash-title")
                yield StatGauge("CPU", id="dash-cpu")
                yield StatGauge("Memory", id="dash-mem")
                yield StatGauge("Disk", id="dash-disk")
            with Vertical(classes="dash-card"):
                yield Static("SERVICES", classes="dash-title")
                yield Static("Waiting for Docker snapshot...", id="dash-counts", classes="dash-line")
                yield Static("", id="dash-state-bar", classes="dash-line")
        with Vertical(classes="dash-section"):
            yield Static("LIVE CONTEXT", classes="dash-title")
            yield Static("", id="dash-context", classes="dash-line")

    def on_mount(self) -> None:
        self._cache_children()

    def _cache_children(self) -> None:
        if self._labels and self._gauges:
            return
        self._labels = {
            "host": self.query_one("#dash-host", Static),
            "counts": self.query_one("#dash-counts", Static),
            "state_bar": self.query_one("#dash-state-bar", Static),
            "context": self.query_one("#dash-context", Static),
        }
        self._gauges = {
            "cpu": self.query_one("#dash-cpu", StatGauge),
            "mem": self.query_one("#dash-mem", StatGauge),
            "disk": self.query_one("#dash-disk", StatGauge),
        }

    def update_system(self, stats: SystemStats) -> None:
        self._cache_children()
        uptime = _fmt_uptime(stats.uptime_seconds) if stats.uptime_seconds else "unknown"
        self._labels["host"].update(f"{stats.hostname or 'unknown'}  up {uptime}  load {stats.load_avg[0]:.2f}")
        self._gauges["cpu"].set_value(stats.cpu_percent)
        self._gauges["mem"].set_value(stats.mem_percent, f"{_fmt_bytes(stats.mem_used)} / {_fmt_bytes(stats.mem_total)}")
        self._gauges["disk"].set_value(stats.disk_percent, f"{_fmt_bytes(stats.disk_used)} / {_fmt_bytes(stats.disk_total)}")
        temp = f"  temp {stats.temp_celsius:.1f}C" if stats.temp_celsius is not None else ""
        context = self._labels.get("context")
        if context is not None:
            context.update(
                f"cores {stats.cpu_count}  net up {_fmt_bytes(stats.net_sent)} down {_fmt_bytes(stats.net_recv)}{temp}"
            )

    def update_docker(self, snapshot: DockerSnapshot) -> None:
        self._cache_children()
        if not snapshot.available:
            self._labels["counts"].update("Docker unavailable")
            self._labels["state_bar"].update(render_state_bar({}, width=28))
            return
        counts = docker_state_counts(snapshot)
        total = sum(counts.values())
        self._labels["counts"].update(f"{total} services observed")
        self._labels["state_bar"].update(render_state_bar(counts, width=28))
