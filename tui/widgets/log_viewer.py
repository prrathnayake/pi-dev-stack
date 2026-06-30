"""Live log viewer widget."""
from __future__ import annotations

import threading
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import ListView, ListItem, Label, RichLog, Static


class LogViewer(Vertical):
    """Service log viewer with a sidebar list and a streaming log panel."""

    DEFAULT_CSS = """
    LogViewer {
        padding: 0 1;
    }
    LogViewer > Horizontal {
        height: 1fr;
    }
    LogViewer #log-sidebar {
        width: 22;
        border-right: solid $primary;
        padding: 0;
    }
    LogViewer #log-sidebar > Label {
        text-style: bold;
        padding: 0 1;
        background: $primary 10%;
    }
    LogViewer #log-sidebar > ListView {
        height: 1fr;
    }
    LogViewer #log-panel {
        width: 1fr;
        padding: 0 1;
    }
    LogViewer #log-status {
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_stop = threading.Event()
        self._current_service: str | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="log-sidebar"):
                yield Label("Services")
                yield ListView(id="log-service-list")
            with Vertical(id="log-panel"):
                yield Static("Select a service to view logs", id="log-status")
                yield RichLog(id="log-output", wrap=False, markup=True)
        yield Static(
            "c=clear  s=start stream  x=stop stream  ↑↓=select service",
            id="log-footer",
        )

    def on_mount(self) -> None:
        from ..data import load_registry
        lv = self.query_one("#log-service-list", ListView)
        for svc in load_registry():
            if svc.port or svc.profile == "extras":
                lv.append(ListItem(Label(svc.name), id=f"log-svc-{svc.name}"))

    def on_list_view_selected(self, event: ListItem.Selected) -> None:
        item_id = event.item.id
        if item_id and item_id.startswith("log-svc-"):
            self._current_service = item_id[8:]
            self._start_stream()

    def _start_stream(self) -> None:
        self._stop_stream()
        if not self._current_service:
            return
        self._stream_stop.clear()
        log = self.query_one("#log-output", RichLog)
        log.clear()
        status = self.query_one("#log-status", Static)
        status.update(f"Streaming: {self._current_service}")
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

    def start_stream(self) -> None:
        self._start_stream()

    @property
    def current_service(self) -> str | None:
        return self._current_service

    def on_unmount(self) -> None:
        self._stop_stream()
