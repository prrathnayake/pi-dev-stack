"""Orange-tinted log panel with service selector and streaming."""
from __future__ import annotations

import threading
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, RichLog, Static, Label
from textual.message import Message


class LogPanel(Horizontal):
    """Streaming log viewer with clickable service selector."""

    DEFAULT_CSS = """
    LogPanel {
        padding: 0;
    }
    LogPanel > #log-sidebar {
        width: 24;
        dock: left;
        background: $panel;
        border-right: solid $border;
        padding: 0;
        height: 1fr;
    }
    LogPanel > #log-sidebar > #sidebar-header {
        text-style: bold;
        color: $accent;
        padding: 1 1;
        height: 1;
        background: $surface;
    }
    LogPanel > #log-sidebar > VerticalScroll {
        height: 1fr;
    }
    LogPanel > #log-sidebar .svc-btn {
        width: 100%;
        height: 1;
        text-align: left;
        padding: 0 2;
        color: $text-muted;
        border: none;
        background: $panel;
    }
    LogPanel > #log-sidebar .svc-btn:hover {
        color: $text;
        background: $surface;
    }
    LogPanel > #log-sidebar .svc-btn.-active {
        color: $accent;
        text-style: bold;
        background: $primary 15%;
        border-left: thick $primary;
    }
    LogPanel > #log-content {
        width: 1fr;
        padding: 0;
    }
    LogPanel > #log-content > #log-status {
        height: 1;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
        border-bottom: solid $border-blurred;
    }
    LogPanel > #log-content > RichLog {
        height: 1fr;
        padding: 0 1;
    }
    LogPanel > #log-content > #log-hint {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $text-disabled;
        background: $panel;
    }
    """

    class ServiceLogSelected(Message):
        def __init__(self, service: str) -> None:
            self.service = service
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_stop = threading.Event()
        self._current_service: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="log-sidebar"):
            yield Static("SERVICES", id="sidebar-header")
            with VerticalScroll(id="svc-list"):
                from ..data import load_registry
                for svc in load_registry():
                    btn_id = f"log-svc-{svc.name}"
                    yield Button(svc.name, id=btn_id, classes="svc-btn")
        with Vertical(id="log-content"):
            yield Static("Select a service to view logs", id="log-status")
            yield RichLog(id="log-output", wrap=False, markup=True)
            yield Static("  click a service to stream  c=clear", id="log-hint")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("log-svc-"):
            service = event.button.id[8:]
            self._select_service(service)

    def _select_service(self, service: str) -> None:
        from ..data import load_registry
        for svc in load_registry():
            btn = self.query_one(f"#log-svc-{svc.name}", Button)
            if svc.name == service:
                btn.add_class("-active")
            else:
                btn.remove_class("-active")
        self._current_service = service
        self._start_stream()
        self.post_message(self.ServiceLogSelected(service))

    def _start_stream(self) -> None:
        self._stop_stream()
        if not self._current_service:
            return
        self._stream_stop.clear()
        log = self.query_one("#log-output", RichLog)
        log.clear()
        status = self.query_one("#log-status", Static)
        status.update(f"[$accent]Streaming:[/] {self._current_service}")
        svc = self._current_service

        from ..data import log_stream

        def _stream() -> None:
            for line in log_stream(svc):
                if self._stream_stop.is_set():
                    break
                try:
                    self.app.call_from_thread(log.write, line)
                except Exception:
                    break

        self._stream_thread = threading.Thread(target=_stream, daemon=True)
        self._stream_thread.start()

    def _stop_stream(self) -> None:
        self._stream_stop.set()
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=2)
        self._stream_thread = None

    def clear_log(self) -> None:
        self.query_one("#log-output", RichLog).clear()
        self.query_one("#log-status", Static).update("Log cleared")

    def stop_stream(self) -> None:
        self._stop_stream()
        self.query_one("#log-status", Static).update("Stream stopped")

    def select_service(self, service: str) -> None:
        """Called from outside to select a service."""
        if service:
            self._select_service(service)

    @property
    def current_service(self) -> str | None:
        return self._current_service

    def on_unmount(self) -> None:
        self._stop_stream()
