# Plex

## Overview

Plex is a media server that organizes and streams your movies, TV shows, music, and photos.

Local URL:

```text
http://localhost:32400/web
```

## Start Service

```bash
docker compose --profile extras up -d plex
```

Then:

```bash
homelab plex status
```

## Restart Service

```bash
homelab plex restart
```

## Logs

```bash
homelab plex logs
```

## Open Shell

```bash
homelab plex shell
```

## Persistent Data

```text
data/plex/config/
```

## Media Library

Place media under the repository `media/` directory, which is mounted into the container at:

```text
/media
```

Subdirectories are not created automatically. A typical layout is:

```text
media/movies
media/tv
media/music
media/photos
```

## Claiming the Server

On first run, claim the server against your Plex account by setting `PLEX_CLAIM` in `.env`:

```env
PLEX_CLAIM=claim-xxxxxxxxxxxxxxxxxxxx
```

Obtain a claim token from:

```text
https://www.plex.tv/claim/
```

Then restart:

```bash
homelab plex restart
```

The token expires after a few minutes, so claim promptly after starting the container.

## Exposing to the LAN

By default the web UI and discovery ports are bound to `127.0.0.1` only. To stream to other devices on your local network, set the bind address in `.env`:

```env
PLEX_WEB_BIND=0.0.0.0
```

Then restart:

```bash
homelab plex restart
```

## Ports

| Port | Protocol | Purpose |
|---:|---|---|
| 32400 | TCP | Web UI / streaming |
| 1900 | UDP | DLNA discovery |
| 3005 | TCP | Plex Companion |
| 5353 | UDP | Bonjour / mDNS discovery |
| 8324 | TCP | Plex Companion |
| 32410 | UDP | GDM discovery |
| 32412 | UDP | GDM discovery |
| 32413 | UDP | GDM discovery |
| 32414 | UDP | GDM discovery |
| 32469 | TCP | DLNA |

## Troubleshooting

### Server Not Reachable on LAN

Confirm `PLEX_WEB_BIND=0.0.0.0` in `.env` and that no firewall blocks the ports above.

### Claim Token Expired

Request a new token from `https://www.plex.tv/claim/`, update `PLEX_CLAIM`, and restart.

### Inspect Container

```bash
homelab service inspect plex
```
