"""Service grid — scrollable grid of clickable service cards."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.message import Message
from textual.widgets import Static

from .service_card import ServiceCard
from ..data import load_registry, containers, container_stats


class ServiceGrid(VerticalScroll):
    """Scrollable grid of ServiceCards with real-time updates."""

    DEFAULT_CSS = """
    ServiceGrid {
        padding: 1 1;
    }
    ServiceGrid > .grid-row {
        height: auto;
        padding: 0 0 1 0;
    }
    ServiceGrid > #grid-empty {
        padding: 2 2;
        color: $text-muted;
        text-align: center;
    }
    """

    class ServiceSelected(Message):
        def __init__(self, service: str) -> None:
            self.service = service
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self._selected: str | None = None
        self._cards: dict[str, ServiceCard] = {}

    def compose(self) -> ComposeResult:
        registry = load_registry()
        row: list[ServiceCard] = []
        cards_per_row = 3

        for svc in registry:
            card = ServiceCard(service_name=svc.name)
            card.port = svc.port
            card.profile = svc.profile
            self._cards[svc.name] = card
            row.append(card)
            if len(row) >= cards_per_row:
                with Horizontal(classes="grid-row"):
                    for c in row:
                        yield c
                row = []

        if row:
            with Horizontal(classes="grid-row"):
                for c in row:
                    yield c

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(2.5, self.refresh_data)

    def refresh_data(self) -> None:
        running = {c.service: c for c in containers()}
        stats = container_stats()
        registry = {s.name: s for s in load_registry()}

        for name, card in self._cards.items():
            svc = registry.get(name)
            c = running.get(name)
            st = stats.get(name)
            if c:
                state = c.state
                uptime = c.uptime or c.status
            else:
                state = "missing"
                uptime = ""
            cpu = st.cpu_percent if st else "—"
            mem = st.mem_percent if st else "—"
            port = svc.port if svc else ""
            profile = svc.profile if svc else ""
            card.update_state(state, port, uptime, cpu, mem, profile)

    def on_service_card_card_clicked(self, event: ServiceCard.CardClicked) -> None:
        self.select_service(event.service)
        self.post_message(self.ServiceSelected(event.service))

    def select_service(self, service: str) -> None:
        if self._selected:
            old = self._cards.get(self._selected)
            if old:
                old.deselect()
        self._selected = service
        card = self._cards.get(service)
        if card:
            card.select()

    @property
    def selected_service(self) -> str | None:
        return self._selected

    def update_service_state(self, service: str, state: str) -> None:
        """Called from docker event stream — update a single card."""
        card = self._cards.get(service)
        if card:
            current = card.state
            card.update_state(state, card.port, "", card.cpu, card.mem, card.profile)
