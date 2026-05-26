# Pi Dev Stack / Homelab CLI

A Raspberry Pi self-hosted developer, AI, automation, monitoring, remote-access, and cyberdeck stack managed by a single `homelab` CLI command.

This project is designed for Raspberry Pi 5 and ARM64 Linux machines, but most services also run on regular Linux servers.

## What This Homelab Provides

This repository gives you:

- Docker Compose based service orchestration
- interactive `homelab` CLI
- AI runtime with Ollama
- browser AI interface with Open WebUI
- workflow automation with n8n
- PostgreSQL and Redis infrastructure
- container management with Portainer
- logs dashboard with Dozzle
- uptime monitoring with Uptime Kuma
- system monitoring with Glances
- dashboard launcher with Homepage
- temporary HTTPS access with Cloudflare quick tunnels
- stable domain support with named Cloudflare Tunnels
- private remote desktop access through Tailscale + VNC
- KiCad remote desktop workflow
- backup and restore commands
- local generated state separation for safe `git pull`
- GitHub Actions CI/CD validation
- MIT license for contributors

## Architecture

```text
homelab CLI
  ├── Docker Compose services
  ├── Cloudflare tunnels
  ├── Tailscale + VNC remote desktop
  ├── backup / restore tools
  ├── local runtime state
  └── diagnostics / dashboard
```

Core tracked files stay updateable through Git. Runtime-generated data is stored in ignored local folders.

See:

```text
docs/ARCHITECTURE.md
```

## Included Services

### AI and Automation

| Service | Purpose | Local URL |
|---|---|---|
| n8n | Workflow automation, Telegram bots, webhooks, background workflows | http://localhost:5678 |
| Ollama | Local LLM runtime for running small/medium models on the Pi | http://localhost:11434 |
| Open WebUI | Browser interface for Ollama models | http://localhost:3000 |

### Data Services

| Service | Purpose |
|---|---|
| PostgreSQL | Main database for n8n |
| Redis | Cache / queue-ready service for future stack extensions |

### Management and Monitoring

| Service | Purpose | Local URL |
|---|---|---|
| Portainer | Docker/container management dashboard | http://localhost:9000 |
| Dozzle | Real-time Docker log viewer | http://localhost:9999 |
| Uptime Kuma | Service uptime monitoring and alerting | http://localhost:3001 |
| Homepage | Central dashboard launcher for homelab services | http://localhost:8088 |
| Glances | CPU/RAM/disk/network system monitor | http://localhost:61208 |

### Remote Access

| Tool | Purpose |
|---|---|
| cloudflared | Temporary or stable HTTPS tunnels |
| Tailscale | Private VPN access to the Pi |
| VNC | Remote graphical desktop access for KiCad and GUI apps |

## Recommended Hardware

- Raspberry Pi 5
- 8GB RAM recommended
- Active cooler
- SSD strongly recommended
- Stable power supply
- Ethernet recommended for reliable tunnels and remote desktop

## Quick Start

```bash
sudo apt install -y git

git clone https://github.com/prrathnayake/pi-dev-stack.git
cd pi-dev-stack
chmod +x homelab pi-stack setup.sh stop.sh tunnel.sh validate.sh
./homelab install
```

Or use the interactive menu:

```bash
./homelab
```

## Install Global CLI Command

After cloning the repo:

```bash
chmod +x homelab pi-stack setup.sh stop.sh tunnel.sh validate.sh
./homelab install-global
```

Then you can run from anywhere:

```bash
homelab
homelab doctor
homelab start
homelab status
```

If you get permission errors:

```bash
cd ~/Desktop/Projects/pi-dev-stack
chmod +x homelab pi-stack setup.sh stop.sh tunnel.sh validate.sh
```

## Homelab CLI Commands

| Command | Purpose |
|---|---|
| `homelab` | Open interactive menu |
| `homelab install` | Install Docker, cloudflared, folders, permissions, and start stack |
| `homelab start` | Start Docker services |
| `homelab stop` | Stop Docker services and tunnels |
| `homelab restart` | Restart stack |
| `homelab status` | Show Docker Compose service status |
| `homelab logs` | Follow logs |
| `homelab doctor` | Run diagnostics for Docker, Compose, cloudflared, Tailscale, disk, memory, temperature |
| `homelab dashboard` | Terminal dashboard with service/system status |
| `homelab models` | Ollama model manager |
| `homelab tunnel` | Start temporary Cloudflare quick tunnels |
| `homelab urls` | Show generated public URLs from logs/state |
| `homelab configure-named-tunnel` | Prepare stable Cloudflare named tunnel setup |
| `homelab named-tunnel` | Start configured named tunnel |
| `homelab backup` | Create backup archive |
| `homelab restore` | Restore from backup archive |
| `homelab validate` | Validate Docker Compose and environment |
| `homelab update` | Pull latest Git changes and refresh executable permissions |
| `homelab install-global` | Install global `homelab` command |
| `homelab reset` | Full reset / wipe local data after confirmation |
| `homelab desktop-install` | Install Tailscale + VNC remote desktop support |
| `homelab desktop-status` | Show Tailscale and VNC remote desktop info |
| `homelab kicad` | Print KiCad remote desktop usage helper |

## Service Ports

| Service | Port |
|---|---:|
| n8n | 5678 |
| Open WebUI | 3000 |
| Uptime Kuma | 3001 |
| Ollama API | 11434 |
| Portainer | 9000 |
| Dozzle | 9999 |
| Homepage | 8088 |
| Glances | 61208 |

Ports are bound to `127.0.0.1` for safer local-only access. Remote access should be done through Cloudflare Tunnel or Tailscale.

## Cloudflare Quick Tunnels

Start temporary HTTPS URLs:

```bash
homelab tunnel
```

Show URLs:

```bash
homelab urls
```

Quick tunnels generate URLs like:

```text
https://example-random-name.trycloudflare.com
```

Important: these URLs are temporary. They can change after restart and may stop working if the `cloudflared` process exits.

For n8n Telegram nodes, `homelab tunnel` updates:

```text
N8N_WEBHOOK_URL=https://your-current-n8n-url.trycloudflare.com/
```

Then n8n can provide HTTPS webhooks for Telegram.

## Stable Domain Tunnels

For permanent URLs, use Cloudflare named tunnels.

Example target domains:

```text
n8n.yourdomain.com
ai.yourdomain.com
portainer.yourdomain.com
status.yourdomain.com
logs.yourdomain.com
```

Requirements:

- Cloudflare account
- domain connected to Cloudflare DNS
- named Cloudflare Tunnel

Template file:

```text
cloudflared/config.example.yml
```

Generated local config:

```text
cloudflared/config.yml
```

The generated config is ignored by Git to prevent conflicts and accidental credential leaks.

## Tailscale + VNC Remote Desktop

This is for remote GUI access to the Raspberry Pi desktop and apps like KiCad.

Install remote desktop support:

```bash
homelab desktop-install
```

Check connection info:

```bash
homelab desktop-status
```

The command shows your Tailscale IP. From your laptop, connect using a VNC Viewer:

```text
100.x.x.x:5900
```

Then open KiCad on the remote Pi desktop.

KiCad helper:

```bash
homelab kicad
```

## Ollama Model Manager

Open the model manager:

```bash
homelab models
```

Recommended Raspberry Pi models:

```text
llama3.2:1b
llama3.2:3b
qwen2.5:3b
```

Large models may be slow on Raspberry Pi. Use small models first.

## Backup and Restore

Create backup:

```bash
homelab backup
```

Restore backup:

```bash
homelab restore backups/pi-dev-stack-YYYYMMDD-HHMMSS.tar.gz
```

Backups include local data/config where available:

```text
data/
.env
homepage/
cloudflared/
local/
docker-compose.override.yml
```

## Persistent Data

Persistent service data is stored under:

```text
data/postgres
data/redis
data/n8n
data/ollama
data/open-webui
data/portainer
data/uptime-kuma
```

Do not delete `data/` unless you want to reset the stack.

## Local State and Safe Git Updates

Generated runtime information should not be committed.

Ignored local folders:

```text
state/
.local-state/
local/
data/
logs/
backups/
```

Purpose:

| Path | Purpose |
|---|---|
| `state/` | persistent generated runtime state |
| `.local-state/` | temporary local cache/status files |
| `local/` | your own scripts and custom extensions |
| `data/` | Docker service data |
| `logs/` | tunnel/runtime logs |
| `backups/` | backup archives |

This keeps the main system updateable:

```bash
git pull
homelab update
```

without interfering with your local runtime files.

## Local Customization Without Git Conflicts

Do not modify tracked infrastructure files directly:

```text
docker-compose.yml
setup.sh
tunnel.sh
validate.sh
stop.sh
pi-stack
homelab
```

Instead, use local override files.

Create Docker override:

```bash
cp docker-compose.override.example.yml docker-compose.override.yml
```

Example:

```yaml
services:
  open-webui:
    environment:
      WEBUI_NAME: Pasan AI Lab
```

Store custom scripts under:

```text
local/
```

Example:

```text
local/custom-backup.sh
local/custom-tunnels.sh
local/kicad-start.sh
```

## Docker Permission Fix

If this fails:

```bash
docker ps
```

with:

```text
permission denied while trying to connect to the docker API
```

run:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

If still failing, reboot:

```bash
sudo reboot
```

Temporary workaround:

```bash
sudo docker ps
```

## n8n Permission Fix

If n8n logs show:

```text
EACCES: permission denied, open '/home/node/.n8n/config'
```

fix folder ownership:

```bash
sudo chown -R 1000:1000 data/n8n
docker compose restart n8n
```

## Portainer First-Run Timeout

If Portainer shows:

```text
Your Portainer instance timed out for security purposes.
```

restart it:

```bash
docker restart pi-portainer
```

Then open Portainer immediately and create the first admin user.

## Common Docker Commands

```bash
docker compose ps
docker compose logs -f
docker compose logs -f n8n
docker compose restart n8n
docker compose down
docker compose up -d
```

## CI/CD

GitHub Actions validates:

- Docker Compose config
- shell script syntax
- `homelab` CLI syntax
- PostgreSQL startup
- Redis startup
- n8n startup
- n8n HTTP readiness
- cloudflared binary install

There is also an optional Raspberry Pi self-hosted runner workflow for full ARM64 stack validation.

## Contributing

See:

```text
CONTRIBUTING.md
```

Contributor principles:

- keep Raspberry Pi ARM64 support working
- do not commit secrets
- do not commit generated local state
- update documentation when adding features
- prefer safe defaults for exposed services

## Security Notes

- Do not expose Portainer publicly without strong authentication.
- Prefer Tailscale for private administrative access.
- Prefer Cloudflare Zero Trust for public dashboards.
- Keep `.env` private.
- Never commit Cloudflare credentials.
- Use named tunnels for stable production URLs.

## Recommended Next Improvements

- Better tunnel state stored as JSON
- web dashboard for homelab status
- plugin system under `local/plugins/`
- scheduled backups
- Grafana + Prometheus
- Loki log aggregation
- Qdrant/Chroma vector database
- MinIO object storage
- kiosk/cyberdeck boot mode
- local API daemon for the CLI

## License

MIT. See `LICENSE`.
