"""Modal dialog screens for compact TUI feedback."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class MessageDialog(ModalScreen[None]):
    """Simple centered message dialog."""

    CSS = """
    MessageDialog {
        align: center middle;
    }
    MessageDialog > #dialog {
        width: 72;
        max-width: 92%;
        height: auto;
        max-height: 85%;
        padding: 1 2;
        background: $panel;
        border: thick $primary;
    }
    MessageDialog .dialog-title {
        height: auto;
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }
    MessageDialog .dialog-body {
        height: auto;
        color: $text;
        padding: 0 0 1 0;
    }
    MessageDialog .dialog-buttons {
        height: 3;
        align: right middle;
    }
    MessageDialog .dialog-button {
        min-width: 10;
    }
    """

    def __init__(self, title: str, message: str, button_label: str = "OK") -> None:
        super().__init__()
        self.title_text = title
        self.message = message
        self.button_label = button_label

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(self.title_text, classes="dialog-title")
            yield Static(self.message, classes="dialog-body")
            with Horizontal(classes="dialog-buttons"):
                yield Button(self.button_label, id="dialog-ok", variant="primary", classes="dialog-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)
