"""Custom orange theme for the homelab TUI."""
from __future__ import annotations

from textual.theme import Theme

PI_ORANGE = Theme(
    name="pi-orange",
    primary="#FF7A1A",
    secondary="#C85A1A",
    accent="#FFD580",
    warning="#FFB347",
    error="#E03C31",
    success="#5BA661",
    foreground="#F5E6D8",
    background="#1B1410",
    surface="#241A14",
    panel="#2E2118",
    boost="#FFFFFF08",
    dark=True,
    variables={
        "footer-key-foreground": "#FF9A3C",
        "border": "#FF7A1A",
        "border-blurred": "#5A3A22",
        "input-selection-background": "#FF7A1A 40%",
        "block-cursor-background": "#FF7A1A",
        "scrollbar": "#FF7A1A 60%",
        "scrollbar-hover": "#FF7A1A",
        "scrollbar-active": "#FFB347",
        "button-foreground": "#FFD580",
        "button-focus-text-style": "bold",
    },
)
