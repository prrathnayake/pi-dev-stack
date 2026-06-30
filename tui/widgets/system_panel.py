"""System / machine stats panel widget."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label

from ..data import system_stats


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}EB"


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


def _bar(percent: float, width: int = 20) -> str:
    filled = int(percent / 100 * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


class SystemPanel(VerticalScroll):
    """Live-refreshing system resource panel."""

    DEFAULT_CSS = """
    SystemPanel {
        padding: 0 1;
    }
    SystemPanel > Label {
        padding: 0 0;
    }
    .sys-header {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }
    .sys-metric {
        padding: 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("System resources — auto-refresh every 2s", id="sys-title")

    def on_mount(self) -> None:
        self.set_interval(2, self.refresh_data)
        self.refresh_data()

    def refresh_data(self) -> None:
        s = system_stats()
        labels: list[str] = []

        labels.append(f"[b]Host[/b]  {s.hostname}")
        if s.os_name:
            labels.append(f"[b]OS[/b]    {s.os_name}")
        if s.uptime_seconds:
            labels.append(f"[b]Up[/b]    {_fmt_uptime(s.uptime_seconds)}")
        labels.append("")

        cpu_label = f"CPU    {_bar(s.cpu_percent)} {s.cpu_percent:5.1f}%  ({s.cpu_count} cores)"
        labels.append(cpu_label)
        if s.cpu_per_core:
            core_summary = "  ".join(f"{c:.0f}%" for c in s.cpu_per_core[:8])
            labels.append(f"       cores: {core_summary}")
        labels.append("")

        mem_label = f"Memory {_bar(s.mem_percent)} {s.mem_percent:5.1f}%  ({_fmt_bytes(s.mem_used)} / {_fmt_bytes(s.mem_total)})"
        labels.append(mem_label)

        if s.swap_total > 0:
            swap_label = f"Swap   {_bar(s.swap_percent)} {s.swap_percent:5.1f}%  ({_fmt_bytes(s.swap_used)} / {_fmt_bytes(s.swap_total)})"
            labels.append(swap_label)

        disk_label = f"Disk   {_bar(s.disk_percent)} {s.disk_percent:5.1f}%  ({_fmt_bytes(s.disk_used)} / {_fmt_bytes(s.disk_total)})"
        labels.append(disk_label)
        labels.append("")

        labels.append(f"Load   {s.load_avg[0]:.2f}  {s.load_avg[1]:.2f}  {s.load_avg[2]:.2f}")
        labels.append(f"Net    ↑ {_fmt_bytes(s.net_sent)}   ↓ {_fmt_bytes(s.net_recv)}")
        if s.temp_celsius is not None:
            labels.append(f"Temp   {s.temp_celsius:.1f}°C")

        title = self.query_one("#sys-title", Label)
        title.update("\n".join(labels))
