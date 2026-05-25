# Pi Dev Stack

Self-hosted Raspberry Pi developer stack with:

- n8n
- Ollama
- Open WebUI
- PostgreSQL
- Redis
- Portainer
- Cloudflare Tunnel

## Quick Start

```bash
sudo apt install -y git

git clone https://github.com/prrathnayake/pi-dev-stack.git
cd pi-dev-stack
chmod +x setup.sh
./setup.sh
```

## Services

| Service | Local Port |
|---|---|
| n8n | 5678 |
| Open WebUI | 3000 |
| Ollama | 11434 |
| Portainer | 9000 |

## Public URLs

Temporary public URLs are automatically generated using Cloudflare Tunnel.

Check logs:

```bash
cat logs/n8n.log
cat logs/open-webui.log
cat logs/portainer.log
```

## Docker Commands

```bash
docker compose up -d
docker compose down
docker compose logs -f
```

## Recommended Raspberry Pi

- Raspberry Pi 5
- 8GB+ RAM
- Active cooler
- SSD recommended

## Included software

- n8n
- Ollama
- Open WebUI
- PostgreSQL
- Redis
- Portainer
- cloudflared
