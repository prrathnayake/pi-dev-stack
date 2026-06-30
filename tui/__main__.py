"""homelab tui — entry point for `python3 -m tui`."""
from __future__ import annotations

from .app import HomelabTui


def main() -> None:
    app = HomelabTui()
    app.run()


if __name__ == "__main__":
    main()
