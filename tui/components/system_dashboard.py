"""System dashboard — grid of custom orange gauges and system info."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Horizontal, Container
from textual.widgets import Static

from .stat_gauge import StatGauge
from ..data import SystemStats


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def _fmt_uptime(seconds: int) -> str:
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{mins}m")
    return " ".join(parts)


class SystemDashboard(VerticalScroll):
    """Full system monitoring dashboard with custom orange gauges."""

    DEFAULT_CSS = """
    SystemDashboard {
        padding: 1 2;
    }
    SystemDashboard > .sys-row {
        height: auto;
        padding: 0 0 1 0;
    }
    SystemDashboard > .sys-info {
        padding: 1 1;
        border: solid $border-blurred;
        background: $surface;
        margin: 0 0 1 0;
    }
    SystemDashboard > .sys-info > .info-line {
        color: $text-muted;
        height: 1;
    }
    SystemDashboard > .sys-info > .info-header {
        text-style: bold;
        color: $accent;
        height: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._statics: dict[str, Static] = {}
        self._gauges: dict[str, StatGauge] = {}

    def compose(self) -> ComposeResult:
        yield Static("HOST INFORMATION", classes="info-header")
        yield Static("", id="sys-host", classes="info-line")
        yield Static("", id="sys-os", classes="info-line")
        yield Static("", id="sys-uptime", classes="info-line")
        yield Static("", id="sys-cores", classes="info-line")
        yield Static("")

        with Horizontal(classes="sys-row"):
            with Container():
                yield StatGauge("CPU", id="gauge-cpu")
                yield StatGauge("Memory", id="gauge-mem")
                yield StatGauge("Swap", id="gauge-swap")
            with Container():
                yield StatGauge("Disk", id="gauge-disk")
                yield StatGauge("Load", id="gauge-load")
                yield StatGauge("Network", id="gauge-net")

        yield Static("PER-CORE CPU", classes="info-header")
        yield Static("", id="sys-cores-detail", classes="info-line")
        yield Static("")

        yield Static("SYSTEM METRICS", classes="info-header")
        yield Static("", id="sys-load-detail", classes="info-line")
        yield Static("", id="sys-net-detail", classes="info-line")
        yield Static("", id="sys-temp-detail", classes="info-line")

    def on_mount(self) -> None:
        self._cache_children()

    def _cache_children(self) -> None:
        if self._statics and self._gauges:
            return
        self._statics = {
            "host": self.query_one("#sys-host", Static),
            "os": self.query_one("#sys-os", Static),
            "uptime": self.query_one("#sys-uptime", Static),
            "cores": self.query_one("#sys-cores", Static),
            "cores_detail": self.query_one("#sys-cores-detail", Static),
            "load_detail": self.query_one("#sys-load-detail", Static),
            "net_detail": self.query_one("#sys-net-detail", Static),
            "temp_detail": self.query_one("#sys-temp-detail", Static),
        }
        self._gauges = {
            "cpu": self.query_one("#gauge-cpu", StatGauge),
            "mem": self.query_one("#gauge-mem", StatGauge),
            "swap": self.query_one("#gauge-swap", StatGauge),
            "disk": self.query_one("#gauge-disk", StatGauge),
            "load": self.query_one("#gauge-load", StatGauge),
            "net": self.query_one("#gauge-net", StatGauge),
        }

    def update_stats(self, stats: SystemStats) -> None:
        self._cache_children()
        s = stats

        self._statics["host"].update(f"  Host:  {s.hostname}")
        os_line = f"  OS:    {s.os_name}" if s.os_name else "  OS:    unknown"
        self._statics["os"].update(os_line)
        up_line = f"  Up:    {_fmt_uptime(s.uptime_seconds)}" if s.uptime_seconds else "  Up:    unknown"
        self._statics["uptime"].update(up_line)
        self._statics["cores"].update(f"  Cores: {s.cpu_count}")

        self._gauges["cpu"].set_value(s.cpu_percent)
        self._gauges["mem"].set_value(
            s.mem_percent, f"{_fmt_bytes(s.mem_used)} / {_fmt_bytes(s.mem_total)}"
        )
        swap_gauge = self._gauges["swap"]
        if s.swap_total > 0:
            swap_gauge.set_value(s.swap_percent, f"{_fmt_bytes(s.swap_used)} / {_fmt_bytes(s.swap_total)}")
        else:
            swap_gauge.set_value(0.0, "no swap")
        self._gauges["disk"].set_value(
            s.disk_percent, f"{_fmt_bytes(s.disk_used)} / {_fmt_bytes(s.disk_total)}"
        )
        load_percent = min(s.load_avg[0] / max(s.cpu_count, 1) * 100, 100) if s.cpu_count else 0
        self._gauges["load"].set_value(load_percent, f"{s.load_avg[0]:.2f}")
        net_percent = 0.0
        self._gauges["net"].set_value(net_percent, f"↑{_fmt_bytes(s.net_sent)} ↓{_fmt_bytes(s.net_recv)}")

        if s.cpu_per_core:
            core_summary = "  ".join(f"[{i}] {c:.0f}%" for i, c in enumerate(s.cpu_per_core[:8]))
            self._statics["cores_detail"].update(f"  {core_summary}")

        self._statics["load_detail"].update(
            f"  Load:  {s.load_avg[0]:.2f}  {s.load_avg[1]:.2f}  {s.load_avg[2]:.2f}"
        )
        self._statics["net_detail"].update(
            f"  Net:   ↑ {_fmt_bytes(s.net_sent)}   ↓ {_fmt_bytes(s.net_recv)}"
        )
        if s.temp_celsius is not None:
            self._statics["temp_detail"].update(f"  Temp:  {s.temp_celsius:.1f}°C")
        else:
            self._statics["temp_detail"].update("  Temp:  —")
