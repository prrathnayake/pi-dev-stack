"""Main Textual application for homelab tui — fully redesigned.

Features:
- Custom orange theme (pi-orange)
- pyfiglet ASCII banner with orange gradient
- One-line live system stats (always visible)
- Clickable menu bar for page switching (touch-friendly)
- Clickable action bar for service control (touch-friendly)
- Clickable service cards in a scrollable grid
- Real-time Docker event stream for instant state updates
- Live container resource stats (2s poll)
- Live system stats (1.5s poll)
- Animated loading spinner during actions
- Docker pull progress with per-layer bars
- Custom-styled log viewer and registry browser
"""
from __future__ import annotations

import threading
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.message import Message
from textual.widgets import Static

from .theme import PI_ORANGE
from .components.banner import HomelabBanner
from .components.stats_bar import StatsBar
from .components.menu_bar import MenuBar
from .components.action_bar import ActionBar
from .components.service_grid import ServiceGrid
from .components.system_dashboard import SystemDashboard
from .components.log_panel import LogPanel
from .components.registry_table import RegistryTable
from .components.loading_spinner import OrangeSpinner
from .components.pull_progress import PullProgress
from .data import (
    DockerEvent,
    docker_events,
    action as do_action,
    start_service,
    load_registry,
)


class DockerEventMessage(Message):
    """Posted from the event stream thread to update the UI."""
    def __init__(self, event: DockerEvent) -> None:
        self.event = event
        super().__init__()


class HomelabTui(App):
    """homelab TUI — a Gemini CLI-style monitoring dashboard."""

    TITLE = "homelab"
    SUB_TITLE = "Pi Dev Stack Monitor"

    CSS = """
    #content {
        height: 1fr;
        padding: 0;
    }
    #content > * {
        display: none;
    }
    #content > .-visible {
        display: block;
    }
    .loading-overlay {
        layer: above;
        dock: top;
        height: 1fr;
        background: $background 90%;
        align: center middle;
        padding: 2 4;
    }
    .loading-overlay > OrangeSpinner {
        height: auto;
    }
    .loading-overlay > .loading-msg {
        padding: 1 0;
        color: $accent;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "switch_page('Containers')", "Containers"),
        Binding("2", "switch_page('System')", "System"),
        Binding("3", "switch_page('Logs')", "Logs"),
        Binding("4", "switch_page('Registry')", "Registry"),
        Binding("s", "do_action('start')", "Start"),
        Binding("x", "do_action('stop')", "Stop"),
        Binding("r", "do_action('restart')", "Restart"),
        Binding("u", "do_action('url')", "URL"),
        Binding("l", "do_action('logs')", "Logs"),
        Binding("?", "help_overlay", "Help"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._selected_service: str | None = None
        self._active_page: str = "Containers"
        self._event_thread: Optional[threading.Thread] = None
        self._event_stop = threading.Event()

    def compose(self) -> ComposeResult:
        yield HomelabBanner()
        yield StatsBar()
        yield MenuBar()
        with Container(id="content"):
            yield ServiceGrid()
            yield SystemDashboard()
            yield LogPanel()
            yield RegistryTable()
        yield ActionBar()

    def on_mount(self) -> None:
        self.register_theme(PI_ORANGE)
        self.theme = "pi-orange"
        self._switch_page("Containers")
        self._start_event_stream()

    # ------------------------------------------------------------------
    # Page switching
    # ------------------------------------------------------------------

    def _switch_page(self, page: str) -> None:
        self._active_page = page
        menu = self.query_one(MenuBar)
        menu.set_active(page)
        content = self.query_one("#content", Container)
        for child in content.children:
            child.remove_class("-visible")
        page_map = {
            "Containers": ServiceGrid,
            "System": SystemDashboard,
            "Logs": LogPanel,
            "Registry": RegistryTable,
        }
        widget_class = page_map.get(page)
        if widget_class:
            try:
                widget = self.query_one(widget_class)
                widget.add_class("-visible")
            except Exception:
                pass

    def action_switch_page(self, page: str) -> None:
        self._switch_page(page)

    def on_menu_bar_page_selected(self, event: MenuBar.PageSelected) -> None:
        self._switch_page(event.page)

    # ------------------------------------------------------------------
    # Action handling
    # ------------------------------------------------------------------

    def on_action_bar_action_triggered(self, event: ActionBar.ActionTriggered) -> None:
        self._handle_action(event.action)

    def action_do_action(self, action: str) -> None:
        self._handle_action(action)

    def _handle_action(self, action: str) -> None:
        if action == "quit":
            self.exit()
            return
        if action in ("start", "stop", "restart"):
            self._do_service_action(action)
        elif action == "url":
            self._show_url()
        elif action == "logs":
            self._show_logs()

    def _do_service_action(self, action_name: str) -> None:
        svc = self._get_selected_service()
        if not svc:
            self.notify("No service selected — click a service card first", severity="warning")
            return
        self.notify(f"{action_name} {svc}...", timeout=2)
        self._show_loading(f"{action_name.title()}ing {svc}...")

        def _run() -> None:
            code, out, err = do_action(svc, action_name, timeout=60)
            try:
                self.app.call_from_thread(self._action_done, svc, action_name, code, err)
            except Exception:
                pass

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _action_done(self, service: str, action_name: str, code: int, err: str) -> None:
        self._hide_loading()
        if code == 0:
            self.notify(f"[$success]{action_name.title()} {service} — done[/]", timeout=3)
        else:
            self.notify(f"[$error]{action_name} {service} failed: {err.strip()[:80]}[/]", severity="error", timeout=5)
        try:
            grid = self.query_one(ServiceGrid)
            grid.refresh_data()
        except Exception:
            pass

    def _show_url(self) -> None:
        svc = self._get_selected_service()
        if not svc:
            self.notify("No service selected", severity="warning")
            return
        for s in load_registry():
            if s.name == svc:
                self.notify(s.url, timeout=8)
                return
        self.notify(f"Unknown service: {svc}", severity="error")

    def _show_logs(self) -> None:
        svc = self._get_selected_service()
        if not svc:
            self.notify("No service selected", severity="warning")
            return
        self._switch_page("Logs")
        try:
            log_panel = self.query_one(LogPanel)
            log_panel.select_service(svc)
        except Exception:
            pass

    def _get_selected_service(self) -> str | None:
        if self._active_page == "Containers":
            try:
                grid = self.query_one(ServiceGrid)
                return grid.selected_service
            except Exception:
                return self._selected_service
        return self._selected_service

    # ------------------------------------------------------------------
    # Service selection
    # ------------------------------------------------------------------

    def on_service_grid_service_selected(self, event: ServiceGrid.ServiceSelected) -> None:
        self._selected_service = event.service

    def on_log_panel_service_log_selected(self, event: LogPanel.ServiceLogSelected) -> None:
        self._selected_service = event.service

    # ------------------------------------------------------------------
    # Loading overlay
    # ------------------------------------------------------------------

    def _show_loading(self, message: str) -> None:
        for existing in self.query(".loading-overlay"):
            existing.remove()
        overlay = Container(
            OrangeSpinner(message),
            Static(message, classes="loading-msg"),
            classes="loading-overlay",
        )
        self.mount(overlay)

    def _hide_loading(self) -> None:
        for overlay in self.query(".loading-overlay"):
            overlay.remove()

    # ------------------------------------------------------------------
    # Docker event stream — real-time container state updates
    # ------------------------------------------------------------------

    def _start_event_stream(self) -> None:
        def _stream() -> None:
            for event in docker_events():
                if self._event_stop.is_set():
                    break
                try:
                    self.app.call_from_thread(self._on_docker_event, event)
                except Exception:
                    break

        self._event_thread = threading.Thread(target=_stream, daemon=True)
        self._event_thread.start()

    def _on_docker_event(self, event: DockerEvent) -> None:
        if not event.is_state_change:
            return
        try:
            grid = self.query_one(ServiceGrid)
            state_map = {
                "start": "running",
                "stop": "stopped",
                "die": "stopped",
                "pause": "paused",
                "unpause": "running",
                "create": "pulling",
                "destroy": "missing",
            }
            state = state_map.get(event.action, event.action)
            grid.update_service_state(event.service, state)
            self.notify(f"[$accent]{event.service}[/] → {state}", timeout=3)
        except Exception:
            pass

    def on_unmount(self) -> None:
        self._event_stop.set()

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def action_help_overlay(self) -> None:
        help_text = (
            "[bold $accent]homelab tui — keybindings[/]\n\n"
            "  [bold]1[/]  Containers page\n"
            "  [bold]2[/]  System page\n"
            "  [bold]3[/]  Logs page\n"
            "  [bold]4[/]  Registry page\n\n"
            "  [bold]s[/]  Start selected service\n"
            "  [bold]x[/]  Stop selected service\n"
            "  [bold]r[/]  Restart selected service\n"
            "  [bold]u[/]  Show service URL\n"
            "  [bold]l[/]  Jump to logs\n"
            "  [bold]?[/]  This help\n"
            "  [bold]q[/]  Quit\n\n"
            "  Touch: tap menu items, action buttons, and service cards"
        )
        self.notify(help_text, timeout=15)
