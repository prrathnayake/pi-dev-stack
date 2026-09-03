# Pi Dev Stack

A Raspberry Pi and ARM64 homelab stack with a guided, automation-friendly `homelab` command.

The stack includes developer tools, local AI, automation, monitoring, networking, storage, remote access, and media services managed through Docker Compose.

## Quick start

```bash
sudo apt install -y git python3 python3-venv
git clone https://github.com/prrathnayake/pi-dev-stack.git
cd pi-dev-stack
./homelab setup
./homelab stack start
```

The launcher creates an ignored `.homelab-venv` and installs pinned CLI dependencies on first use. Running `./homelab` with no arguments opens guided mode in an interactive terminal.

## Common commands

```bash
# One-shot summary
homelab overview

# Stack and services
homelab stack start --profile core
homelab stack status --profile all
homelab service list
homelab service start n8n open-webui
homelab service logs n8n --tail 200
homelab service logs n8n --follow
homelab service url pihole

# Configuration and diagnostics
homelab config init
homelab config list
homelab config set POSTGRES_PASSWORD
homelab config validate
homelab system doctor
homelab system validate

# Backups and maintenance
homelab backup create
homelab backup verify backups/pi-dev-stack-YYYYMMDD-HHMMSS.tar.gz
homelab update check
homelab update images n8n --restart
```

Use `homelab COMMAND --help` for the complete option list.

## Safety and automation

- Destructive operations require confirmation or the global `--yes` flag.
- The global `--dry-run` flag previews state-changing commands.
- Media deletion always requires the explicit `data purge --media` option.
- Secret configuration values are masked unless deliberately revealed.
- `--json` emits one object with `ok`, `command`, `data`, `warnings`, and `errors`.
- Underlying Docker, Git, archive, and system failures are returned as nonzero exit codes.

Global exit codes are `0` success, `2` usage or confirmation required, `3` missing prerequisite, `4` operation failure, and `5` partial completion.

## Service groups

Core services include PostgreSQL, Redis, n8n, Ollama, Open WebUI, Portainer, Dozzle, Uptime Kuma, Homepage, Glances, Home Assistant, and Pi-hole.

Optional services under the `extras` profile include Watchtower, Traefik, Vaultwarden, Gitea, MinIO, Syncthing, File Browser, Netdata, Prometheus, Grafana, Mosquitto, Node-RED, code-server, Plex, and Dockge.

Service metadata lives in `config/services.tsv`; `homelab system validate` checks it against `docker-compose.yml`.

## Remote access

Quick Cloudflare tunnels can be managed by service or tunnel group:

```bash
homelab tunnel start core
homelab tunnel status
homelab tunnel urls
homelab tunnel stop core
```

For persistent administrative access, prefer Tailscale or a local SSH session.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
