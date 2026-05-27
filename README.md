# Pi Dev Stack / Homelab CLI

A Raspberry Pi self-hosted developer, AI, automation, monitoring, networking, remote-access, and cyberdeck stack managed by a single `homelab` CLI command.

This project is designed for Raspberry Pi 5 and ARM64 Linux machines, but most services also run on regular Linux servers.

## What This Homelab Provides

This repository gives you:

- Docker Compose based service orchestration
- interactive `homelab` CLI
- MCP server for AI-assisted homelab inspection and safe operations
- AI runtime with Ollama
- browser AI interface with Open WebUI
- workflow automation with n8n
- PostgreSQL and Redis infrastructure
- network-wide ad blocking with Pi-hole
- container management with Portainer
- logs dashboard with Dozzle
- uptime monitoring with Uptime Kuma
- system monitoring with Glances
- dashboard launcher with Homepage
- temporary HTTPS access with Cloudflare quick tunnels
- stable domain support with named Cloudflare Tunnels
- private remote desktop access through Tailscale + VNC
- backup and restore commands
- local generated state separation for safe `git pull`

## Included Services

### AI and Automation

| Service | Purpose | Local URL |
|---|---|---|
| n8n | Workflow automation | http://localhost:5678 |
| Ollama | Local LLM runtime | http://localhost:11434 |
| Open WebUI | Browser interface for Ollama | http://localhost:3000 |

### Infrastructure and Networking

| Service | Purpose | Local URL |
|---|---|---|
| PostgreSQL | Main database for n8n | - |
| Redis | Cache / queue service | - |
| Pi-hole | DNS ad blocker and local DNS sinkhole | http://localhost:8081/admin |

### Monitoring and Operations

| Service | Purpose | Local URL |
|---|---|---|
| Portainer | Docker management dashboard | http://localhost:9000 |
| Dozzle | Real-time logs | http://localhost:9999 |
| Uptime Kuma | Uptime monitoring | http://localhost:3001 |
| Homepage | Homelab dashboard | http://localhost:8088 |
| Glances | System monitoring | http://localhost:61208 |

## Quick Start

```bash
sudo apt install -y git

git clone https://github.com/prrathnayake/pi-dev-stack.git
cd pi-dev-stack
chmod +x homelab pi-stack setup.sh stop.sh tunnel.sh validate.sh
./homelab install
```

## Pi-hole

Pi-hole is included for network-wide DNS filtering and ad blocking.

Admin UI:

```text
http://localhost:8081/admin
```

### Start Pi-hole

```bash
homelab pihole start
```

### Pi-hole CLI Commands

```bash
homelab pihole status
homelab pihole logs
homelab pihole shell

homelab pihole block ads.example.com
homelab pihole enable example.com

homelab pihole disable 300
homelab pihole enable-blocking

homelab pihole update-gravity
homelab pihole stats
```

### Change Pi-hole Password

```bash
homelab pihole password '<new-password>'
```

### DNS Port

Pi-hole exposes:

| Port | Purpose |
|---:|---|
| 53 TCP/UDP | DNS |
| 8081 | Admin web UI |

### Environment Variables

Configure in `.env`:

```env
PIHOLE_WEBPASSWORD=change_this_pihole_password
PIHOLE_HOSTNAME=pi-hole
PIHOLE_DNS_BIND=0.0.0.0
PIHOLE_WEB_BIND=127.0.0.1
PIHOLE_DNS_LISTENING_MODE=all
PIHOLE_DNS_UPSTREAMS=1.1.1.1;1.0.0.1
TIMEZONE=Australia/Melbourne
```

### Persistent Pi-hole Data

```text
data/pihole/etc-pihole
data/pihole/etc-dnsmasq.d
```

See full documentation:

```text
docs/PIHOLE.md
```
