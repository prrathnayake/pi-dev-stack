"""Animated homelab banner with pyfiglet ASCII logo and orange gradient."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual.color import Gradient
from rich.text import Text
from rich.style import Style
from rich.align import Align


def _gradient_ascii(text: str, c1: str = "#FF7A1A", c2: str = "#FFD580") -> Text:
    """Apply a horizontal orange gradient to ASCII art text."""
    grad = Gradient((0.0, c1), (1.0, c2))
    out = Text()
    lines = text.splitlines()
    width = max(len(line) for line in lines) if lines else 1
    for line in lines:
        for i, ch in enumerate(line):
            if ch == " ":
                out.append(" ")
            else:
                color = grad.get_color(i / max(width - 1, 1))
                out.append(ch, Style.from_color(color=color.rich_color))
        out.append("\n")
    return out


def _generate_logo() -> str:
    try:
        import pyfiglet
        return pyfiglet.figlet_text("homelab", font="slant")
    except Exception:
        return "  homelab"


class HomelabBanner(Container):
    """Animated banner with the homelab ASCII logo."""

    DEFAULT_CSS = """
    HomelabBanner {
        height: auto;
        padding: 0 0;
        dock: top;
        text-align: center;
    }
    HomelabBanner > #logo {
        height: auto;
        padding: 0;
        text-align: center;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._logo_text = _generate_logo()
        self._logo_frames = (
            _gradient_ascii(self._logo_text, "#FF7A1A", "#FFD580"),
            _gradient_ascii(self._logo_text, "#FF9A3C", "#FFB347"),
        )
        self._pulse_phase = 0

    def compose(self) -> ComposeResult:
        yield Static(Align.center(self._logo_frames[0]), id="logo")

    def on_mount(self) -> None:
        self.styles.animate("opacity", 1.0, duration=0.01, final_value=1.0)
        self.set_interval(3.0, self._pulse)

    def _pulse(self) -> None:
        self._pulse_phase = (self._pulse_phase + 1) % 2
        logo = self.query_one("#logo", Static)
        logo.update(Align.center(self._logo_frames[self._pulse_phase]))
