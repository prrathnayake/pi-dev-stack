"""Service registry browser widget."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Label

from ..data import load_registry


class RegistryView(Vertical):
    """Read-only browse of config/services.tsv metadata."""

    DEFAULT_CSS = """
    RegistryView {
        padding: 0 1;
    }
    RegistryView > Label {
        padding: 0 1;
        color: $text-muted;
    }
    RegistryView > DataTable {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Service registry — config/services.tsv")
        yield DataTable(id="registry-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one("#registry-table", DataTable)
        table.add_columns(
            "Service", "Profile", "Group", "Port", "Scheme", "URL", "Tunnel", "Tunnel Groups",
        )
        self.refresh_data()

    def refresh_data(self) -> None:
        table = self.query_one("#registry-table", DataTable)
        table.clear()
        for svc in load_registry():
            url = svc.url
            table.add_row(
                svc.name,
                svc.profile,
                svc.group,
                svc.port or "—",
                svc.scheme,
                url,
                svc.tunnel,
                svc.tunnel_groups or "—",
                key=svc.name,
            )
