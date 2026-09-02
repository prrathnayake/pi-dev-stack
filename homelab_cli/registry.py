from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import yaml

from .context import repo_root


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class Service:
    name: str
    profile: str
    group: str
    port: str
    scheme: str
    path: str
    aliases: str
    tunnel: str
    tunnel_groups: str
    url_note: str

    @property
    def url(self) -> str:
        if self.url_note:
            return self.url_note
        if not self.port:
            return f"{self.name} has no web UI"
        return f"{self.scheme}://localhost:{self.port}{self.path}"

    @property
    def is_extra(self) -> bool:
        return self.profile == "extras"

    @property
    def is_tunnelable(self) -> bool:
        return self.tunnel == "yes"


@dataclass(frozen=True)
class Registry:
    services: tuple[Service, ...]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.services)

    def get(self, name: str) -> Service:
        for service in self.services:
            if service.name == name or name in service.aliases.split(","):
                return service
        raise RegistryError(f"Unknown service: {name}")

    def select(self, *, profile: str | None = None, group: str | None = None) -> list[Service]:
        return [
            service
            for service in self.services
            if (profile in (None, "all") or service.profile == profile)
            and (group is None or service.group == group)
        ]

    def tunnel_targets(self, target: str) -> list[Service]:
        if target == "all":
            return [item for item in self.services if item.is_tunnelable]
        try:
            service = self.get(target)
        except RegistryError:
            selected = [item for item in self.services if target in item.tunnel_groups.split(",") and item.is_tunnelable]
            if selected:
                return selected
            raise RegistryError(f"Unknown tunnel target: {target}")
        if not service.is_tunnelable:
            raise RegistryError(f"Service is not tunnel-enabled: {target}")
        return [service]


def load_registry(path: Path | None = None) -> Registry:
    source = path or repo_root() / "config" / "services.tsv"
    services: list[Service] = []
    try:
        with source.open(newline="", encoding="utf-8") as handle:
            for row in csv.reader(handle, delimiter="|"):
                if not row or row[0].startswith("#"):
                    continue
                row.extend([""] * (10 - len(row)))
                services.append(Service(*row[:10]))
    except OSError as exc:
        raise RegistryError(f"Cannot read service registry: {exc}") from exc
    names = [item.name for item in services]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise RegistryError("Duplicate registry services: " + ", ".join(duplicates))
    invalid = [item.name for item in services if item.profile not in {"core", "extras"}]
    if invalid:
        raise RegistryError("Invalid service profiles: " + ", ".join(invalid))
    return Registry(tuple(services))


def validate_compose_contract(registry: Registry, compose_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        document = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return [f"Cannot parse docker-compose.yml: {exc}"]
    compose_services = document.get("services") or {}
    registry_names = set(registry.names)
    compose_names = set(compose_services)
    for name in sorted(registry_names - compose_names):
        errors.append(f"Registry service missing from Compose: {name}")
    for name in sorted(compose_names - registry_names):
        errors.append(f"Compose service missing from registry: {name}")
    for service in registry.services:
        spec = compose_services.get(service.name, {})
        expected_container = f"pi-{service.name}"
        if spec.get("container_name") != expected_container:
            errors.append(f"{service.name}: container_name must be {expected_container}")
        profiles = spec.get("profiles", [])
        if service.is_extra and "extras" not in profiles:
            errors.append(f"{service.name}: extras registry service lacks Compose extras profile")
        if not service.is_extra and profiles:
            errors.append(f"{service.name}: core registry service unexpectedly has a Compose profile")
    return errors
