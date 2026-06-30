"""Custom orange progress gauge — animated fill bar."""
from __future__ import annotations

from textual.widgets import Static
from textual.reactive import reactive


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
        width = 30
        filled = int(self.percent / 100 * width)
        bar = "█" * filled + "░" * (width - filled)
        if self.percent < 60:
            color = "$accent"
        elif self.percent < 85:
            color = "$warning"
        else:
            color = "$error"
        label_line = f"{self.label} [{color}]{self.percent:.0f}%[/]"
        if self.total:
            label_line += f"  {self.total}"
        self.update(f"{label_line}\n[{color}]{bar}[/]")
