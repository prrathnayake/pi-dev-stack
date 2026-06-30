"""Services management page with touch-friendly action controls."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Static

from ..data import DockerSnapshot, load_registry


SERVICE_ACTIONS = ("start", "stop", "restart", "url", "logs")


class ServicesPage(VerticalScroll):
    """Manage homelab services and emit per-service action requests."""

    DEFAULT_CSS = """
    ServicesPage {
        padding: 1 1;
    }
    ServicesPage .service-row {
        width: 1fr;
        height: auto;
        min-width: 22;
        padding: 1 1;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $border-blurred;
    }
    ServicesPage .service-row.-selected {
        border: solid $primary;
        background: $primary 10%;
    }
    ServicesPage .service-title {
        height: 1;
        color: $text;
        text-style: bold;
    }
    ServicesPage .service-meta {
        height: auto;
        color: $text-muted;
    }
    ServicesPage .service-actions {
        height: auto;
        padding: 1 0 0 0;
        layout: grid;
        grid-size: 3;
        grid-gutter: 1 1;
    }
    ServicesPage .svc-action {
        width: 1fr;
        min-width: 7;
        height: 2;
        margin: 0;
        border: solid $border-blurred;
    }
    """

    class ServiceSelected(Message):
        def __init__(self, service: str) -> None:
            self.service = service
            super().__init__()

    class ServiceActionRequested(Message):
        def __init__(self, service: str, action: str) -> None:
            self.service = service
            self.action = action
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self._selected: str | None = None
        self._rows: dict[str, Vertical] = {}
        self._meta: dict[str, Static] = {}

    def compose(self) -> ComposeResult:
        for service in load_registry():
            with Vertical(id=f"svc-row-{service.name}", classes="service-row") as row:
                self._rows[service.name] = row
                yield Static(service.name, classes="service-title")
                meta = Static(f"{service.profile}  :{service.port or '-'}  missing", classes="service-meta")
                self._meta[service.name] = meta
                yield meta
                with Grid(classes="service-actions"):
                    yield Button("Select", id=f"svc-select-{service.name}", classes="svc-action")
                    for action in SERVICE_ACTIONS:
                        yield Button(action.title(), id=f"svc-action-{service.name}-{action}", classes="svc-action")

    @property
    def selected_service(self) -> str | None:
        return self._selected

    def select_service(self, service: str) -> None:
        if self._selected:
            old = self._rows.get(self._selected)
            if old:
                old.remove_class("-selected")
        self._selected = service
        row = self._rows.get(service)
        if row:
            row.add_class("-selected")

    def update_snapshot(self, snapshot: DockerSnapshot) -> None:
        registry = {service.name: service for service in load_registry()}
        for name, label in self._meta.items():
            service = registry.get(name)
            status = snapshot.statuses.get(name)
            stats = snapshot.stats.get(name)
            state = status.state if status else "missing"
            cpu = stats.cpu_percent if stats else "-"
            mem = stats.mem_percent if stats else "-"
            profile = service.profile if service else "-"
            port = service.port if service and service.port else "-"
            label.update(f"{profile}  :{port}  {state}  cpu {cpu}  mem {mem}")

    def update_service_state(self, service: str, state: str) -> None:
        label = self._meta.get(service)
        if label is not None:
            label.update(f"state {state}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.startswith("svc-select-"):
            service = button_id.removeprefix("svc-select-")
            self.select_service(service)
            self.post_message(self.ServiceSelected(service))
            return
        if button_id.startswith("svc-action-"):
            rest = button_id.removeprefix("svc-action-")
            service, action = rest.rsplit("-", 1)
            self.select_service(service)
            self.post_message(self.ServiceActionRequested(service, action))
