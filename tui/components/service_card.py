"""Service card — clickable card showing container status and stats."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import Static
from textual.reactive import reactive

from .status_badge import StatusBadge


class ServiceCard(Container):
    """A clickable card displaying a single service's status."""

    DEFAULT_CSS = """
    ServiceCard {
        width: 24;
        height: 7;
        padding: 0 1;
        margin: 0 1;
        border: solid $border-blurred;
        background: $surface;
    }
    ServiceCard:hover {
        border: solid $accent;
        background: $surface-lighten-1;
    }
    ServiceCard.-selected {
        border: solid $primary;
        background: $primary 10%;
    }
    ServiceCard.-running {
        border-left: thick $success;
    }
    ServiceCard.-stopped {
        border-left: thick $border-blurred;
    }
    ServiceCard.-pulling {
        border-left: thick $accent;
    }
    ServiceCard.-error {
        border-left: thick $error;
    }
    ServiceCard > .card-name {
        text-style: bold;
        color: $text;
        height: 1;
        padding: 0;
    }
    ServiceCard > .card-port {
        color: $text-muted;
        height: 1;
        padding: 0;
    }
    ServiceCard > .card-stats {
        color: $text-muted;
        height: 1;
        padding: 0;
    }
    """

    class CardClicked(Message):
        def __init__(self, service: str) -> None:
            self.service = service
            super().__init__()

    def __init__(self, service_name: str, id: str | None = None) -> None:
        super().__init__(id=id or f"card-{service_name}")
        self.service_name = service_name
        self.state = "missing"
        self.cpu = "—"
        self.mem = "—"
        self.port = ""
        self.uptime = ""
        self.profile = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.service_name, classes="card-name")
            yield StatusBadge(state=self.state, id=f"badge-{self.service_name}")
            yield Static("", classes="card-port", id=f"port-{self.service_name}")
            yield Static("", classes="card-stats", id=f"stats-{self.service_name}")

    def update_state(self, state: str, port: str = "", uptime: str = "", cpu: str = "—", mem: str = "—", profile: str = "") -> None:
        self.state = state
        self.port = port
        self.uptime = uptime
        self.cpu = cpu
        self.mem = mem
        self.profile = profile
        self.remove_class("-running", "-stopped", "-pulling", "-error")
        if state == "running":
            self.add_class("-running")
        elif state == "pulling":
            self.add_class("-pulling")
        elif state in ("exited", "dead", "error"):
            self.add_class("-error")
        else:
            self.add_class("-stopped")
        badge = self.query_one(StatusBadge)
        badge.state = state
        port_str = f":{port}" if port else ""
        self.query_one(f"#port-{self.service_name}", Static).update(f"{profile}{port_str}")
        self.query_one(f"#stats-{self.service_name}", Static).update(f"CPU {cpu} │ MEM {mem}")

    def on_click(self, event) -> None:
        self.post_message(self.CardClicked(self.service_name))

    def select(self) -> None:
        self.add_class("-selected")

    def deselect(self) -> None:
        self.remove_class("-selected")
