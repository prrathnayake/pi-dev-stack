"""Service grid — scrollable grid of clickable service cards."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message

from .service_card import ServiceCard
from ..data import DockerSnapshot, load_registry


class ServiceGrid(VerticalScroll):
    """Scrollable grid of ServiceCards with real-time updates."""

    DEFAULT_CSS = """
    ServiceGrid {
        padding: 1 1;
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

        for svc in registry:
            card = ServiceCard(service_name=svc.name)
            card.port = svc.port
            card.profile = svc.profile
            self._cards[svc.name] = card
            yield card

    def update_snapshot(self, snapshot: DockerSnapshot) -> None:
        running = snapshot.statuses
        stats = snapshot.stats
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

    def refresh_data(self) -> None:
        from ..data import docker_snapshot

        self.update_snapshot(docker_snapshot())

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
            card.update_state(state, card.port, card.uptime, card.cpu, card.mem, card.profile)
