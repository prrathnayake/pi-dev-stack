from __future__ import annotations

from pathlib import Path

import pytest

from homelab_cli.registry import RegistryError, load_registry, validate_compose_contract


ROOT = Path(__file__).resolve().parents[1]


def test_registry_matches_compose_contract() -> None:
    registry = load_registry(ROOT / "config" / "services.tsv")
    assert len(registry.services) == 27
    assert validate_compose_contract(registry, ROOT / "docker-compose.yml") == []


def test_registry_resolves_aliases_groups_and_profiles() -> None:
    registry = load_registry(ROOT / "config" / "services.tsv")
    assert registry.get("webui").name == "open-webui"
    assert all(item.profile == "extras" for item in registry.select(profile="extras"))
    assert {item.name for item in registry.tunnel_targets("media")} == {"plex"}
    with pytest.raises(RegistryError, match="not tunnel-enabled"):
        registry.tunnel_targets("postgres")


def test_registry_rejects_duplicates(tmp_path: Path) -> None:
    registry = tmp_path / "services.tsv"
    row = "web|core|app|8080|http|/||yes|core|\n"
    registry.write_text(row + row, encoding="utf-8")
    with pytest.raises(RegistryError, match="Duplicate"):
        load_registry(registry)
