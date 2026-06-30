"""Main Textual application for homelab tui."""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, TabbedContent, TabPane, Static

from .widgets.container_table import ContainerTable
from .widgets.system_panel import SystemPanel
from .widgets.log_viewer import LogViewer
from .widgets.registry_view import RegistryView


class HomelabTui(App):
    """A TUI for monitoring Docker services and system state."""

    TITLE = "homelab"
    SUB_TITLE = "Pi Dev Stack Monitor"

    CSS = """
    #action-bar {
        height: 1;
        dock: bottom;
        background: $primary 20%;
        padding: 0 1;
        color: $text;
    }
    TabbedContent {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "switch_tab('containers')", "Containers"),
        Binding("2", "switch_tab('system')", "System"),
        Binding("3", "switch_tab('logs')", "Logs"),
        Binding("4", "switch_tab('registry')", "Registry"),
        Binding("s", "service_action('start')", "Start"),
        Binding("x", "service_action('stop')", "Stop"),
        Binding("r", "service_action('restart')", "Restart"),
        Binding("u", "show_url", "URL"),
        Binding("l", "show_logs", "Logs"),
        Binding("?", "help_overlay", "Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with TabbedContent(id="tabs", initial="tab-containers"):
            with TabPane("Containers", id="tab-containers"):
                yield ContainerTable()
            with TabPane("System", id="tab-system"):
                yield SystemPanel()
            with TabPane("Logs", id="tab-logs"):
                yield LogViewer()
            with TabPane("Registry", id="tab-registry"):
                yield RegistryView()
        yield Static(
            "s=start  x=stop  r=restart  u=url  l=logs  1-4=tabs  q=quit  ?=help",
            id="action-bar",
        )
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        tc = self.query_one(TabbedContent)
        tc.active = f"tab-{tab_id}"

    def _get_selected_service(self) -> str | None:
        tc = self.query_one(TabbedContent)
        if tc.active == "tab-containers":
            ct = self.query_one(ContainerTable)
            return ct.selected_service
        if tc.active == "tab-registry":
            table = self.query_one("#registry-table")
            if table.cursor_row is None or table.row_count == 0:
                return None
            try:
                row_key = table.coordinate_to_cell_key(
                    table.coordinate(table.cursor_row, 0)
                ).row_key
                return str(row_key.value) if row_key.value else None
            except Exception:
                return None
        return None

    def action_service_action(self, action_name: str) -> None:
        svc = self._get_selected_service()
        if not svc:
            self.notify("No service selected", severity="warning")
            return
        self.notify(f"{action_name} {svc}...", timeout=2)
        from .data import action as do_action
        code, out, err = do_action(svc, action_name)
        if code == 0:
            self.notify(f"{action_name} {svc}: done", severity="success")
        else:
            self.notify(f"{action_name} {svc} failed: {err.strip()[:80]}", severity="error", timeout=5)
        ct = self.query_one(ContainerTable)
        ct.refresh_data()

    def action_show_url(self) -> None:
        svc = self._get_selected_service()
        if not svc:
            self.notify("No service selected", severity="warning")
            return
        from .data import load_registry
        for s in load_registry():
            if s.name == svc:
                self.notify(s.url, timeout=8)
                return
        self.notify(f"Unknown service: {svc}", severity="error")

    def action_show_logs(self) -> None:
        tc = self.query_one(TabbedContent)
        tc.active = "tab-logs"
        svc = self._get_selected_service()
        if svc:
            lv = self.query_one(LogViewer)
            lv._current_service = svc
            lv._start_stream()

    def action_help_overlay(self) -> None:
        help_text = (
            "homelab tui — keybindings\n\n"
            "  1  Containers tab\n"
            "  2  System tab\n"
            "  3  Logs tab\n"
            "  4  Registry tab\n\n"
            "  s  Start selected service\n"
            "  x  Stop selected service\n"
            "  r  Restart selected service\n"
            "  u  Show service URL\n"
            "  l  Jump to logs for service\n"
            "  c  Clear log (on Logs tab)\n"
            "  ?  This help\n"
            "  q  Quit\n"
        )
        self.notify(help_text, timeout=15)
