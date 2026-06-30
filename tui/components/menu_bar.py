"""Clickable menu bar — CLI-style page selection with touch support."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button


class MenuBar(Horizontal):
    """Selectable menu bar with clickable items for touch screens."""

    DEFAULT_CSS = """
    MenuBar {
        height: 3;
        dock: top;
        padding: 0 1;
        background: $panel;
        border-bottom: solid $border;
    }
    MenuBar > .menu-item {
        min-width: 14;
        height: 3;
        border: solid $border-blurred;
        background: $surface;
        color: $text-muted;
        text-align: center;
        padding: 0 2;
    }
    MenuBar > .menu-item:hover {
        background: $surface-lighten-1;
        color: $text;
        border: solid $accent;
    }
    MenuBar > .menu-item.-active {
        background: $primary 20%;
        color: $accent;
        text-style: bold;
        border: solid $primary;
    }
    """

    PAGES = ["Containers", "System", "Logs", "Registry"]

    class PageSelected(Message):
        def __init__(self, page: str) -> None:
            self.page = page
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self._active = "Containers"

    def compose(self) -> ComposeResult:
        for page in self.PAGES:
            btn = Button(
                f"  {page}  ",
                id=f"menu-{page.lower()}",
                classes="menu-item",
            )
            if page == self._active:
                btn.add_class("-active")
            yield btn

    @property
    def active(self) -> str:
        return self._active

    def set_active(self, page: str) -> None:
        self._active = page
        for p in self.PAGES:
            btn = self.query_one(f"#menu-{p.lower()}", Button)
            if p == page:
                btn.add_class("-active")
            else:
                btn.remove_class("-active")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        for page in self.PAGES:
            if event.button.id == f"menu-{page.lower()}":
                self.set_active(page)
                self.post_message(self.PageSelected(page))
                break
