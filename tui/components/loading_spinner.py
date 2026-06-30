"""Orange-themed loading spinner using Rich's spinner engine."""
from __future__ import annotations

from textual.widgets import Static
from rich.spinner import Spinner
from rich.text import Text


class OrangeSpinner(Static):
    """A spinner with orange styling and optional status text."""

    DEFAULT_CSS = """
    OrangeSpinner {
        color: $accent;
        text-style: bold;
        padding: 0 1;
        height: 1;
        text-align: center;
    }
    """

    def __init__(self, text: str = "Loading...", spinner_name: str = "dots", id: str | None = None) -> None:
        super().__init__(id=id)
        self._text = text
        self._spinner_name = spinner_name
        self._spinner: Spinner | None = None

    def on_mount(self) -> None:
        self._spinner = Spinner(self._spinner_name, text=Text(self._text, style="bold #FFD580"), style="#FF7A1A")
        self.auto_refresh = 1 / 10

    def update_text(self, text: str) -> None:
        self._text = text
        if self._spinner:
            self._spinner.text = Text(text, style="bold #FFD580")

    def render(self):
        if self._spinner:
            return self._spinner
        return Text(self._text, style="bold #FF7A1A")
