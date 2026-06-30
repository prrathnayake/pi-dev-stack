"""Container status table widget."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Label

from ..data import ContainerStatus, containers, container_stats, load_registry


class ContainerTable(Vertical):
    """Live-refreshing table of all Docker Compose services."""

    DEFAULT_CSS = """
    ContainerTable {
        padding: 0 1;
    }
    ContainerTable > Label {
        padding: 0 1;
        color: $text-muted;
    }
    ContainerTable > DataTable {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Docker Compose services — auto-refresh every 3s")
        yield DataTable(id="container-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one("#container-table", DataTable)
        table.add_columns(
            "Service", "Profile", "State", "Uptime", "CPU", "Mem", "Ports",
        )
        self.refresh_data()
        self.set_interval(3, self.refresh_data)

    def refresh_data(self) -> None:
        registry = {s.name: s for s in load_registry()}
        stats = container_stats()
        running = {c.service: c for c in containers()}

        table = self.query_one("#container-table", DataTable)
        row_keys = list(table.rows.keys())
        if row_keys:
            table.clear()

        for svc in load_registry():
            st = stats.get(svc.name)
            c = running.get(svc.name)
            if c:
                state = c.state
                uptime = c.uptime or c.status
            else:
                state = "—"
                uptime = "—"
            cpu = st.cpu_percent if st else "—"
            mem = st.mem_percent if st else "—"
            ports = c.ports if c else "—"
            table.add_row(
                svc.name, svc.profile, state, uptime, cpu, mem, ports,
                key=svc.name,
            )

    @property
    def selected_service(self) -> str | None:
        table = self.query_one("#container-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            return None
        try:
            row_key = table.coordinate_to_cell_key(
                table.coordinate(table.cursor_row, 0)
            ).row_key
            return str(row_key.value) if row_key.value else None
        except Exception:
            return None
