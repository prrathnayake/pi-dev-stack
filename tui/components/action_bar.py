"""Clickable action bar — touch-friendly buttons for service control."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Static


class ActionBar(Horizontal):
    """Bottom action bar with clickable buttons for touch screens."""

    DEFAULT_CSS = """
    ActionBar {
        height: 3;
        dock: bottom;
        padding: 0 1;
        background: $panel;
        border-top: solid $border;
    }
    ActionBar > .action-btn {
        min-width: 10;
        height: 3;
        padding: 0 1;
        margin: 0 1;
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
        padding: 1 1;
        text-align: right;
    }
    """

    class ActionTriggered(Message):
        def __init__(self, action: str) -> None:
            self.action = action
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Button("▶ Start", id="btn-start", classes="action-btn action-start")
        yield Button("■ Stop", id="btn-stop", classes="action-btn action-stop")
        yield Button("↻ Restart", id="btn-restart", classes="action-btn action-restart")
        yield Button("🔗 URL", id="btn-url", classes="action-btn action-url")
        yield Button("📜 Logs", id="btn-logs", classes="action-btn action-logs")
        yield Button("✕ Quit", id="btn-quit", classes="action-btn action-quit")
        yield Static("  s x r u l  1-4  q", id="key-hints")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action_map = {
            "btn-start": "start",
            "btn-stop": "stop",
            "btn-restart": "restart",
            "btn-url": "url",
            "btn-logs": "logs",
            "btn-quit": "quit",
        }
        action = action_map.get(event.button.id, "")
        if action:
            self.post_message(self.ActionTriggered(action))
