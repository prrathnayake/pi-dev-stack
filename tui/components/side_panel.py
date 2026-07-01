"""Toggleable side navigation for small-screen friendly TUI layout."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Button, Static


class SidePanel(Vertical):
    """Collapsible main menu with compact homelab branding."""

    DEFAULT_CSS = """
    SidePanel {
        width: 24;
        min-width: 20;
        height: 1fr;
        background: $panel;
        border-right: solid $border;
        padding: 1 1;
    }
    SidePanel.-collapsed {
        display: none;
    }
    SidePanel .side-section {
        height: 1;
        color: $text-disabled;
        padding: 0 0 1 0;
    }
    SidePanel .side-item {
        width: 100%;
        height: 3;
        border: none;
        background: $panel;
        color: $text-muted;
        text-align: left;
        padding: 0 1;
    }
    SidePanel .side-item:hover {
        background: $surface;
        color: $text;
    }
    SidePanel .side-item.-active {
        background: $primary 18%;
        color: $accent;
        text-style: bold;
        border-left: thick $primary;
    }
    SidePanel .side-hint {
        dock: bottom;
        height: auto;
        color: $text-disabled;
        padding: 1 0 0 0;
    }
    """

    PAGES = ("Dashboard", "Services", "Activities")

    class PageSelected(Message):
        def __init__(self, page: str) -> None:
            self.page = page
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self._active = "Dashboard"
        self._buttons: dict[str, Button] = {}

    @property
    def active(self) -> str:
        return self._active

    def compose(self) -> ComposeResult:
        yield Static("MAIN MENU", classes="side-section")
        for page in self.PAGES:
            button = Button(page, id=f"side-{page.lower()}", classes="side-item")
            if page == self._active:
                button.add_class("-active")
            self._buttons[page] = button
            yield button
        yield Static("m toggles menu\n1-4 jump pages", classes="side-hint")

    def set_active(self, page: str) -> None:
        self._active = page
        for name, button in self._buttons.items():
            if name == page:
                button.add_class("-active")
            else:
                button.remove_class("-active")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        for page in self.PAGES:
            if event.button.id == f"side-{page.lower()}":
                self.set_active(page)
                self.post_message(self.PageSelected(page))
                break
