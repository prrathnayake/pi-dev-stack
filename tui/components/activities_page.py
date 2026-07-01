"""Activities page with bounded event history and live logs."""
from __future__ import annotations

from dataclasses import dataclass
from time import strftime

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog, Static

from .log_panel import LogPanel


@dataclass(frozen=True)
class ActivityEvent:
    kind: str
    service: str
    summary: str
    detail: str = ""
    timestamp: str = ""

    def line(self) -> str:
        timestamp = self.timestamp or strftime("%H:%M:%S")
        service = f" [{self.service}]" if self.service else ""
        detail = f" - {self.detail}" if self.detail else ""
        return f"{timestamp} {self.kind.upper()}{service} {self.summary}{detail}"


class ActivitiesPage(Vertical):
    """Activity feed plus live container log monitor."""

    DEFAULT_CSS = """
    ActivitiesPage {
        padding: 0;
    }
    ActivitiesPage > #activity-header {
        height: 1;
        color: $accent;
        text-style: bold;
        padding: 0 1;
        background: $surface;
    }
    ActivitiesPage > #activity-feed {
        height: 10;
        min-height: 5;
        padding: 0 1;
        border-bottom: solid $border-blurred;
    }
    ActivitiesPage > LogPanel {
        height: 1fr;
    }
    """

    def __init__(self, max_events: int = 200) -> None:
        super().__init__()
        self.max_events = max_events
        self._activities: list[ActivityEvent] = []
        self._activity_log: RichLog | None = None

    @property
    def activities(self) -> tuple[ActivityEvent, ...]:
        return tuple(self._activities)

    def compose(self) -> ComposeResult:
        yield Static("ACTIVITIES", id="activity-header")
        yield RichLog(id="activity-feed", wrap=True, markup=False)
        yield LogPanel()

    def on_mount(self) -> None:
        self._activity_log = self.query_one("#activity-feed", RichLog)
        self._render_activities()

    def append_activity(self, event: ActivityEvent) -> None:
        self._activities.append(event)
        if len(self._activities) > self.max_events:
            self._activities = self._activities[-self.max_events:]
        if self._activity_log is not None:
            self._activity_log.write(event.line())

    def set_activities(self, events: list[ActivityEvent]) -> None:
        self._activities = list(events)[-self.max_events:]
        self._render_activities()

    def _render_activities(self) -> None:
        if self._activity_log is None:
            return
        self._activity_log.clear()
        for event in self._activities:
            self._activity_log.write(event.line())

    def select_service(self, service: str) -> None:
        self.query_one(LogPanel).select_service(service)
