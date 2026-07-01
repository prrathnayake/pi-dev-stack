"""Main Textual application for homelab tui — fully redesigned.

Features:
- Custom orange theme (pi-orange)
- One-line live system stats (always visible)
- Toggleable side menu for page switching (touch-friendly)
- Clickable action bar for service control (touch-friendly)
- Dashboard, services management, and activities/log monitoring pages
- Real-time Docker event stream for instant state updates
- Live Docker status and resource stats (2.5s poll)
- Live system stats (1.5s poll)
- Full-screen idle logo after inactivity
- Animated loading spinner during actions
"""
from __future__ import annotations

import threading
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual import events
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.timer import Timer
from textual.widgets import Static

from .theme import PI_ORANGE
from .components.stats_bar import StatsBar
from .components.action_bar import ActionBar
from .components.dialogs import MessageDialog
from .components.activities_page import ActivitiesPage, ActivityEvent
from .components.dashboard_page import DashboardPage
from .components.idle_screen import IdleLogoScreen
from .components.loading_spinner import OrangeSpinner
from .components.log_panel import LogPanel
from .components.services_page import ServicesPage
from .components.side_panel import SidePanel
from .data import (
    DockerEvent,
    DockerSnapshot,
    SystemStats,
    docker_events,
    docker_snapshot,
    action as do_action,
    load_registry,
    prime_system_stats,
    system_stats,
)


class DockerEventMessage(Message):
    """Posted from the event stream thread to update the UI."""
    def __init__(self, event: DockerEvent) -> None:
        self.event = event
        super().__init__()


def should_show_side_panel(width: int) -> bool:
    return width >= 90


IDLE_TIMEOUT_SECONDS = 60.0
MAX_ACTIVITY_EVENTS = 200


def action_progress_message(action_name: str, service: str) -> str:
    labels = {
        "start": "Starting",
        "stop": "Stopping",
        "restart": "Restarting",
    }
    return f"{labels.get(action_name, action_name.title())} {service}..."


class HomelabTui(App):
    """homelab TUI — a Gemini CLI-style monitoring dashboard."""

    TITLE = "homelab"
    SUB_TITLE = "Pi Dev Stack Monitor"

    CSS = """
    #workspace {
        height: 1fr;
        min-height: 0;
    }
    #content {
        height: 1fr;
        width: 1fr;
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
        padding: 1 2;
    }
    .loading-panel {
        width: 56;
        max-width: 92%;
        height: auto;
        padding: 1 2;
        background: $panel;
        border: thick $primary;
    }
    .loading-panel > OrangeSpinner {
        height: auto;
    }
    .loading-panel > .loading-msg {
        padding: 1 0;
        color: $accent;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("m", "toggle_menu", "Menu"),
        Binding("1", "switch_page('Dashboard')", "Dashboard"),
        Binding("2", "switch_page('Services')", "Services"),
        Binding("3", "switch_page('Activities')", "Activities"),
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
        self._active_page: str = "Dashboard"
        self._event_thread: Optional[threading.Thread] = None
        self._event_stop = threading.Event()
        self._system_timer: Timer | None = None
        self._docker_timer: Timer | None = None
        self._docker_reconcile_timer: Timer | None = None
        self._idle_timer: Timer | None = None
        self._idle_screen_visible = False
        self._side_panel_visible = True
        self._menu_user_overridden = False
        self._activities: list[ActivityEvent] = []

    def compose(self) -> ComposeResult:
        yield StatsBar()
        with Horizontal(id="workspace"):
            yield SidePanel()
            with Container(id="content"):
                yield DashboardPage()
                yield ServicesPage()
                yield ActivitiesPage(max_events=MAX_ACTIVITY_EVENTS)
        yield ActionBar()

    def on_mount(self) -> None:
        self.register_theme(PI_ORANGE)
        self.theme = "pi-orange"
        prime_system_stats()
        self._sync_side_panel_for_width(self.size.width)
        self._switch_page("Dashboard")
        self._schedule_system_refresh()
        self._schedule_docker_refresh()
        self._system_timer = self.set_interval(1.5, self._schedule_system_refresh, name="system-refresh")
        self._docker_timer = self.set_interval(2.5, self._schedule_docker_refresh, name="docker-refresh")
        self._reset_idle_timer()
        self._start_event_stream()

    def on_resize(self, event: events.Resize) -> None:
        self._reset_idle_timer()
        self._sync_side_panel_for_width(event.size.width)

    def on_key(self, event: events.Key) -> None:
        self._reset_idle_timer()

    def on_click(self, event: events.Click) -> None:
        self._reset_idle_timer()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        self._reset_idle_timer()

    # ------------------------------------------------------------------
    # Page switching
    # ------------------------------------------------------------------

    def _switch_page(self, page: str) -> None:
        self._reset_idle_timer()
        self._active_page = page
        self.query_one(SidePanel).set_active(page)
        content = self.query_one("#content", Container)
        for child in content.children:
            child.remove_class("-visible")
        page_map = {
            "Dashboard": DashboardPage,
            "Services": ServicesPage,
            "Activities": ActivitiesPage,
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

    def on_side_panel_page_selected(self, event: SidePanel.PageSelected) -> None:
        self._switch_page(event.page)

    def action_toggle_menu(self) -> None:
        self._reset_idle_timer()
        self._menu_user_overridden = True
        self._set_side_panel_visible(not self._side_panel_visible)

    def _sync_side_panel_for_width(self, width: int) -> None:
        if not self._menu_user_overridden:
            self._set_side_panel_visible(should_show_side_panel(width))

    def _set_side_panel_visible(self, visible: bool) -> None:
        self._side_panel_visible = visible
        panel = self.query_one(SidePanel)
        if visible:
            panel.remove_class("-collapsed")
        else:
            panel.add_class("-collapsed")

    # ------------------------------------------------------------------
    # Action handling
    # ------------------------------------------------------------------

    def on_action_bar_action_triggered(self, event: ActionBar.ActionTriggered) -> None:
        self._handle_action(event.action)

    def action_do_action(self, action: str) -> None:
        self._handle_action(action)

    def _handle_action(self, action: str) -> None:
        self._reset_idle_timer()
        if action == "quit":
            self.exit()
            return
        if action == "menu":
            self.action_toggle_menu()
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
            self._show_dialog("No service selected", "Select a service card first, then run the action.")
            return
        self._append_activity(ActivityEvent("action", svc, action_progress_message(action_name, svc)))
        self._show_loading(action_progress_message(action_name, svc))

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
            self._append_activity(ActivityEvent("action", service, f"{action_name.title()} completed"))
            self._show_dialog("Action complete", f"{action_name.title()} {service} completed.")
        else:
            detail = err.strip()[:240] or "No error output returned."
            self._append_activity(ActivityEvent("error", service, f"{action_name} failed", detail))
            self._show_dialog("Action failed", f"{action_name} {service} failed:\n\n{detail}")
        self._schedule_docker_refresh()

    # ------------------------------------------------------------------
    # Centralized refresh workers
    # ------------------------------------------------------------------

    def _schedule_system_refresh(self) -> None:
        self.run_worker(
            self._load_system_stats,
            name="system-refresh",
            group="system-refresh",
            exclusive=True,
            thread=True,
            exit_on_error=False,
        )

    def _load_system_stats(self) -> None:
        stats = system_stats()
        try:
            self.call_from_thread(self._apply_system_stats, stats)
        except Exception:
            pass

    def _apply_system_stats(self, stats: SystemStats) -> None:
        try:
            self.query_one(StatsBar).update_stats(stats)
        except Exception:
            pass
        try:
            self.query_one(DashboardPage).update_system(stats)
        except Exception:
            pass

    def _schedule_docker_refresh(self) -> None:
        self.run_worker(
            self._load_docker_snapshot,
            name="docker-refresh",
            group="docker-refresh",
            exclusive=True,
            thread=True,
            exit_on_error=False,
        )

    def _load_docker_snapshot(self) -> None:
        snapshot = docker_snapshot()
        try:
            self.call_from_thread(self._apply_docker_snapshot, snapshot)
        except Exception:
            pass

    def _apply_docker_snapshot(self, snapshot: DockerSnapshot) -> None:
        try:
            self.query_one(DashboardPage).update_docker(snapshot)
        except Exception:
            pass
        try:
            self.query_one(ServicesPage).update_snapshot(snapshot)
        except Exception:
            pass

    def _schedule_debounced_docker_refresh(self) -> None:
        if not self.is_running:
            return
        if self._docker_reconcile_timer is not None:
            self._docker_reconcile_timer.reset()
            return
        self._docker_reconcile_timer = self.set_timer(
            0.35,
            self._run_debounced_docker_refresh,
            name="docker-event-reconcile",
        )

    def _run_debounced_docker_refresh(self) -> None:
        self._docker_reconcile_timer = None
        self._schedule_docker_refresh()

    def _show_url(self) -> None:
        svc = self._get_selected_service()
        if not svc:
            self._show_dialog("No service selected", "Select a service card first to view its URL.")
            return
        for s in load_registry():
            if s.name == svc:
                self._show_dialog(f"{svc} URL", s.url)
                return
        self._show_dialog("Unknown service", f"Unknown service: {svc}")

    def _show_logs(self) -> None:
        svc = self._get_selected_service()
        if not svc:
            self._show_dialog("No service selected", "Select a service card first to view logs.")
            return
        self._switch_page("Activities")
        try:
            self.query_one(ActivitiesPage).select_service(svc)
        except Exception:
            pass

    def _get_selected_service(self) -> str | None:
        if self._active_page == "Services":
            try:
                services = self.query_one(ServicesPage)
                return services.selected_service
            except Exception:
                return self._selected_service
        return self._selected_service

    # ------------------------------------------------------------------
    # Service selection
    # ------------------------------------------------------------------

    def on_services_page_service_selected(self, event: ServicesPage.ServiceSelected) -> None:
        self._reset_idle_timer()
        self._selected_service = event.service

    def on_services_page_service_action_requested(self, event: ServicesPage.ServiceActionRequested) -> None:
        self._reset_idle_timer()
        self._selected_service = event.service
        self._handle_action(event.action)

    def on_log_panel_service_log_selected(self, event: LogPanel.ServiceLogSelected) -> None:
        self._reset_idle_timer()
        self._selected_service = event.service
        self._append_activity(ActivityEvent("logs", event.service, "Live log monitor selected"))

    # ------------------------------------------------------------------
    # Loading overlay
    # ------------------------------------------------------------------

    def _show_loading(self, message: str) -> None:
        for existing in self.query(".loading-overlay"):
            existing.remove()
        overlay = Container(
            Container(
                OrangeSpinner(message),
                Static(message, classes="loading-msg"),
                classes="loading-panel",
            ),
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
            try:
                self.query_one(ServicesPage).update_service_state(event.service, state)
            except Exception:
                pass
            self._append_activity(ActivityEvent("docker", event.service, f"State changed to {state}", event.action))
            self._schedule_debounced_docker_refresh()
            self.notify(f"[$accent]{event.service}[/] → {state}", timeout=3)
        except Exception:
            pass

    def on_unmount(self) -> None:
        self._event_stop.set()
        for timer in (self._system_timer, self._docker_timer, self._docker_reconcile_timer, self._idle_timer):
            if timer is not None:
                timer.stop()

    # ------------------------------------------------------------------
    # Activity and idle screens
    # ------------------------------------------------------------------

    def _append_activity(self, event: ActivityEvent) -> None:
        self._activities.append(event)
        if len(self._activities) > MAX_ACTIVITY_EVENTS:
            self._activities = self._activities[-MAX_ACTIVITY_EVENTS:]
        try:
            self.query_one(ActivitiesPage).append_activity(event)
        except Exception:
            pass

    def _reset_idle_timer(self) -> None:
        if not self.is_running:
            return
        if self._idle_screen_visible:
            return
        if self._idle_timer is None:
            self._idle_timer = self.set_timer(IDLE_TIMEOUT_SECONDS, self._show_idle_screen, name="idle-logo")
        else:
            self._idle_timer.reset()

    def _show_idle_screen(self) -> None:
        self._idle_timer = None
        if self._idle_screen_visible:
            return
        self._idle_screen_visible = True
        self.push_screen(IdleLogoScreen(), callback=self._idle_screen_dismissed)

    def _idle_screen_dismissed(self, result: None) -> None:
        self._idle_screen_visible = False
        self._reset_idle_timer()

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def action_help_overlay(self) -> None:
        help_text = (
            "[bold $accent]homelab tui — keybindings[/]\n\n"
            "  [bold]m[/]  Toggle main menu\n"
            "  [bold]1[/]  Dashboard page\n"
            "  [bold]2[/]  Services page\n"
            "  [bold]3[/]  Activities page\n\n"
            "  [bold]s[/]  Start selected service\n"
            "  [bold]x[/]  Stop selected service\n"
            "  [bold]r[/]  Restart selected service\n"
            "  [bold]u[/]  Show service URL\n"
            "  [bold]l[/]  Jump to logs\n"
            "  [bold]?[/]  This help\n"
            "  [bold]q[/]  Quit\n\n"
            "  Touch: tap menu items, service action buttons, and log selectors"
        )
        self._show_dialog("Help", help_text)

    def _show_dialog(self, title: str, message: str) -> None:
        self.push_screen(MessageDialog(title, message))
