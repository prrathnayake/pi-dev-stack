"""One-line live system stats bar — always visible under the banner."""
from __future__ import annotations

from textual.widgets import Static
from textual.reactive import reactive

from ..data import system_stats


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}P"


class StatsBar(Static):
    """Compact one-line system stats display."""

    DEFAULT_CSS = """
    StatsBar {
        height: 1;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
        text-align: center;
    }
    """

    def on_mount(self) -> None:
        self.refresh_stats()
        self.set_interval(1.5, self.refresh_stats)

    def refresh_stats(self) -> None:
        s = system_stats()
        parts = []
        parts.append(f"CPU [$accent]{s.cpu_percent:.0f}%[/]")
        parts.append(f"MEM [$accent]{s.mem_percent:.0f}%[/]")
        parts.append(f"DISK [$accent]{s.disk_percent:.0f}%[/]")
        if s.load_avg[0] > 0:
            parts.append(f"LOAD [$accent]{s.load_avg[0]:.1f}[/]")
        parts.append(f"↑[$accent]{_fmt_bytes(s.net_sent)}[/]")
        parts.append(f"↓[$accent]{_fmt_bytes(s.net_recv)}[/]")
        if s.temp_celsius is not None:
            parts.append(f"TEMP [$accent]{s.temp_celsius:.0f}°C[/]")
        self.update("  │  ".join(parts))
