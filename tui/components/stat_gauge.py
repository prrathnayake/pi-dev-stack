"""Custom orange progress gauge — animated fill bar."""
from __future__ import annotations

from textual.widgets import Static
from textual.reactive import reactive


def render_gauge(label: str, percent: float, total: str = "", width: int = 30) -> str:
    width = max(6, min(width, 30))
    percent = max(0.0, min(float(percent), 100.0))
    filled = int(percent / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    if percent < 60:
        color = "$accent"
    elif percent < 85:
        color = "$warning"
    else:
        color = "$error"
    label_line = f"{label} [{color}]{percent:.0f}%[/]"
    if total:
        label_line += f"  {total}"
    return f"{label_line}\n[{color}]{bar}[/]"


class StatGauge(Static):
    """A custom horizontal progress bar with orange theming."""

    DEFAULT_CSS = """
    StatGauge {
        height: 2;
        padding: 0 1;
    }
    StatGauge > .gauge-label {
        height: 1;
        color: $text-muted;
    }
    StatGauge > .gauge-bar {
        height: 1;
    }
    """

    percent = reactive(0.0)
    label = reactive("")
    total = reactive("")

    def __init__(self, label: str = "", id: str | None = None) -> None:
        super().__init__(id=id)
        self.label = label

    def watch_percent(self, percent: float) -> None:
        self._render_bar()

    def watch_label(self, label: str) -> None:
        self._render_bar()

    def on_mount(self) -> None:
        self._render_bar()

    def set_value(self, percent: float, total: str = "") -> None:
        self.percent = percent
        self.total = total

    def _render_bar(self) -> None:
        width = self.size.width if self.size.width else 30
        self.update(render_gauge(self.label, self.percent, self.total, width=max(6, width - 4)))
