"""Status badge — animated indicator for container state."""
from __future__ import annotations

from textual.widgets import Static
from textual.reactive import reactive


class StatusBadge(Static):
    """A colored, animated status indicator for a container."""

    DEFAULT_CSS = """
    StatusBadge {
        height: 1;
        width: auto;
        padding: 0 1;
    }
    StatusBadge.-running {
        color: $success;
        text-style: bold;
    }
    StatusBadge.-stopped {
        color: $text-muted;
    }
    StatusBadge.-pulling {
        color: $accent;
        text-style: bold;
    }
    StatusBadge.-error {
        color: $error;
        text-style: bold;
    }
    StatusBadge.-paused {
        color: $warning;
    }
    """

    state = reactive("stopped")

    def __init__(self, state: str = "stopped", id: str | None = None) -> None:
        super().__init__(id=id)
        self._frame = 0
        self.state = state

    def watch_state(self, state: str) -> None:
        self.remove_class("-running", "-stopped", "-pulling", "-error", "-paused")
        if state == "running":
            self.add_class("-running")
        elif state == "pulling":
            self.add_class("-pulling")
        elif state == "paused":
            self.add_class("-paused")
        elif state in ("exited", "dead", "error"):
            self.add_class("-error")
        else:
            self.add_class("-stopped")
        self._update_render()

    def _update_render(self) -> None:
        icons = {
            "running": ["●", "◉", "●"],
            "pulling": ["◐", "◓", "◑", "◒"],
            "stopped": ["○"],
            "paused": ["◐"],
            "error": ["✗"],
            "exited": ["○"],
            "dead": ["✗"],
            "missing": ["—"],
        }
        frames = icons.get(self.state, ["○"])
        icon = frames[self._frame % len(frames)]
        label = self.state.upper()
        self.update(f"{icon} {label}")

    def on_mount(self) -> None:
        self._update_render()
        if self.state in ("running", "pulling"):
            self.set_interval(0.8, self._animate)

    def _animate(self) -> None:
        if self.state in ("running", "pulling"):
            self._frame += 1
            self._update_render()
