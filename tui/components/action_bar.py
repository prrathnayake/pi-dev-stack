"""Clickable action bar — touch-friendly buttons for service control."""
from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Static


@dataclass(frozen=True)
class ActionSpec:
    action: str
    label: str
    button_id: str
    css_class: str


class ActionBar(Horizontal):
    """Bottom action bar with clickable buttons for touch screens."""

    DEFAULT_CSS = """
    ActionBar {
        height: 2;
        dock: bottom;
        padding: 0 0;
        background: $panel;
        border-top: solid $border;
    }
    ActionBar > .action-btn {
        min-width: 7;
        height: 2;
        padding: 0 1;
        margin: 0 0;
        border: solid $border-blurred;
    }
    ActionBar > .action-btn:hover {
        border: solid $accent;
    }
    ActionBar > .action-start {
        color: $success;
        border: solid $success;
    }
    ActionBar > .action-start:hover {
        background: $success 10%;
    }
    ActionBar > .action-stop {
        color: $error;
        border: solid $error;
    }
    ActionBar > .action-stop:hover {
        background: $error 10%;
    }
    ActionBar > .action-restart {
        color: $warning;
        border: solid $warning;
    }
    ActionBar > .action-restart:hover {
        background: $warning 10%;
    }
    ActionBar > .action-url {
        color: $accent;
        border: solid $accent;
    }
    ActionBar > .action-url:hover {
        background: $accent 10%;
    }
    ActionBar > .action-logs {
        color: $accent;
        border: solid $accent;
    }
    ActionBar > .action-logs:hover {
        background: $accent 10%;
    }
    ActionBar > .action-quit {
        color: $foreground-muted;
        border: solid $border-blurred;
    }
    ActionBar > .action-quit:hover {
        background: $boost;
    }
    ActionBar > #key-hints {
        width: 1fr;
        color: $text-disabled;
        padding: 0 1;
        text-align: right;
    }
    """

    class ActionTriggered(Message):
        def __init__(self, action: str) -> None:
            self.action = action
            super().__init__()

    @classmethod
    def actions(cls) -> tuple[ActionSpec, ...]:
        return (
            ActionSpec("menu", "Menu", "btn-menu", "action-menu"),
            ActionSpec("start", "Start", "btn-start", "action-start"),
            ActionSpec("stop", "Stop", "btn-stop", "action-stop"),
            ActionSpec("restart", "Restart", "btn-restart", "action-restart"),
            ActionSpec("url", "URL", "btn-url", "action-url"),
            ActionSpec("logs", "Logs", "btn-logs", "action-logs"),
            ActionSpec("quit", "Quit", "btn-quit", "action-quit"),
        )

    def compose(self) -> ComposeResult:
        for spec in self.actions():
            yield Button(spec.label, id=spec.button_id, classes=f"action-btn {spec.css_class}")
        yield Static("m menu  s/x/r/u/l  q", id="key-hints")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action_map = {spec.button_id: spec.action for spec in self.actions()}
        action = action_map.get(event.button.id, "")
        if action:
            self.post_message(self.ActionTriggered(action))
