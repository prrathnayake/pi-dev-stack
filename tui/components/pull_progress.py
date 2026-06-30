"""Docker pull progress — animated layer download bars."""
from __future__ import annotations

import threading
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static, ProgressBar
from textual.reactive import reactive

from .loading_spinner import OrangeSpinner


class PullProgress(Vertical):
    """Shows animated progress bars for docker image layer downloads."""

    DEFAULT_CSS = """
    PullProgress {
        padding: 1 2;
        height: auto;
        max-height: 80%;
        width: 60;
        align: center middle;
        background: $panel;
        border: solid $primary;
    }
    PullProgress > #pull-header {
        text-style: bold;
        color: $accent;
        text-align: center;
        height: 1;
        padding: 0 0 1 0;
    }
    PullProgress > #pull-layers {
        height: auto;
        max-height: 15;
        padding: 0;
    }
    PullProgress > .layer-line {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    PullProgress > .layer-complete {
        color: $success;
    }
    PullProgress > .layer-active {
        color: $accent;
    }
    PullProgress > .layer-waiting {
        color: $text-disabled;
    }
    """

    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def compose(self) -> ComposeResult:
        yield Static(f"Pulling images for {self.service}...", id="pull-header")
        yield OrangeSpinner("Downloading layers...", id="pull-spinner")
        yield VerticalScroll(id="pull-layers")

    def on_mount(self) -> None:
        self._start_pull()

    def _start_pull(self) -> None:
        from ..data import pull_progress

        def _pull() -> None:
            for layers in pull_progress(self.service):
                if self._stop.is_set():
                    break
                try:
                    self.app.call_from_thread(self._update_layers, layers)
                except Exception:
                    break
            try:
                self.app.call_from_thread(self._pull_complete)
            except Exception:
                pass

        self._thread = threading.Thread(target=_pull, daemon=True)
        self._thread.start()

    def _update_layers(self, layers: dict) -> None:
        container = self.query_one("#pull-layers", VerticalScroll)
        container.remove_children()
        for layer_id, layer in layers.items():
            short_id = layer_id[:12] if len(layer_id) > 12 else layer_id
            if layer.completed:
                line = Static(f"  ✓ {short_id} {layer.status}", classes="layer-line layer-complete")
            elif layer.percent is not None:
                line = Static(f"  ↓ {short_id} {layer.status} {layer.percent:.0f}%", classes="layer-line layer-active")
            elif layer.status == "Downloading":
                line = Static(f"  ↓ {short_id} Downloading...", classes="layer-line layer-active")
            elif layer.status == "Waiting":
                line = Static(f"  … {short_id} Waiting", classes="layer-line layer-waiting")
            else:
                line = Static(f"  → {short_id} {layer.status}", classes="layer-line layer-active")
            container.mount(line)

    def _pull_complete(self) -> None:
        spinner = self.query_one("#pull-spinner", OrangeSpinner)
        spinner.update_text("Pull complete!")
        header = self.query_one("#pull-header", Static)
        header.update(f"[$success]Pull complete for {self.service}[/]")

    def stop(self) -> None:
        self._stop.set()

    def on_unmount(self) -> None:
        self._stop.set()
