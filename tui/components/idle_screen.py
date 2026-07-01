"""Full-screen idle logo screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static


def idle_logo_text() -> str:
    return "\n".join((
        "  __                         __      __   ",
        " / /_  ____  ____ ___  ___  / /___ _/ /_  ",
        "/ __ \\/ __ \\/ __ `__ \\/ _ \\/ / __ `/ __ \\ ",
        "/ / / / /_/ / / / / / /  __/ / /_/ / /_/ /",
        "/_/ /_/\\____/_/ /_/ /_/\\___/_/\\__,_/_.___/ ",
    ))


class IdleLogoScreen(ModalScreen[None]):
    """Minimal full-screen idle/sleep screen."""

    CSS = """
    IdleLogoScreen {
        align: center middle;
        background: $background;
    }
    IdleLogoScreen > #idle-logo {
        width: auto;
        height: auto;
        color: $accent;
        text-style: bold;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(idle_logo_text(), id="idle-logo")

    def on_mount(self) -> None:
        self.set_interval(4.0, self._pulse_logo)

    def _pulse_logo(self) -> None:
        logo = self.query_one("#idle-logo", Static)
        logo.styles.opacity = 0.7 if logo.styles.opacity == 1 else 1

    def on_key(self, event) -> None:
        self.dismiss(None)

    def on_click(self, event) -> None:
        self.dismiss(None)
