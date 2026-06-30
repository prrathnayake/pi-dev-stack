"""Custom-styled registry browser for config/services.tsv."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from ..data import load_registry


class RegistryTable(VerticalScroll):
    """Read-only registry browser with orange-themed formatting."""

    DEFAULT_CSS = """
    RegistryTable {
        padding: 1 2;
    }
    RegistryTable > .reg-header {
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }
    RegistryTable > .reg-entry {
        padding: 0 1;
        height: auto;
        margin: 0 0 1 0;
        border: solid $border-blurred;
        background: $surface;
    }
    RegistryTable > .reg-entry:hover {
        border: solid $accent;
    }
    RegistryTable > .reg-entry > .reg-name {
        text-style: bold;
        color: $text;
        height: 1;
    }
    RegistryTable > .reg-entry > .reg-details {
        color: $text-muted;
        height: 1;
    }
    RegistryTable > .reg-entry > .reg-url {
        color: $accent;
        height: 1;
    }
    RegistryTable > .reg-entry > .reg-tags {
        color: $text-disabled;
        height: 1;
    }
    RegistryTable > .reg-entry.-core {
        border-left: thick $success;
    }
    RegistryTable > .reg-entry.-extras {
        border-left: thick $warning;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("SERVICE REGISTRY — config/services.tsv", classes="reg-header")
        for svc in load_registry():
            classes = "reg-entry"
            if svc.profile == "core":
                classes += " -core"
            else:
                classes += " -extras"
            with VerticalScroll(classes=classes, id=f"reg-{svc.name}"):
                yield Static(svc.name, classes="reg-name")
                yield Static(
                    f"profile: {svc.profile}  │  group: {svc.group}  │  port: {svc.port or '—'}",
                    classes="reg-details",
                )
                yield Static(f"  {svc.url}", classes="reg-url")
                tags = []
                if svc.tunnel == "yes":
                    tags.append("tunnelable")
                if svc.tunnel_groups:
                    tags.append(f"groups: {svc.tunnel_groups}")
                if svc.aliases:
                    tags.append(f"aliases: {svc.aliases}")
                yield Static("  " + "  │  ".join(tags) if tags else "  —", classes="reg-tags")
