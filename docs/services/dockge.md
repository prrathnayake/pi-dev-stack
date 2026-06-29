# Dockge

## Overview

Dockge is a minimalistic dashboard for managing Docker Compose stacks. It can start, stop, restart, view logs, and edit compose files for every stack on the host, including the `pi-dev-stack` itself.

Local URL:

```text
http://localhost:5001
```

## Start Service

```bash
docker compose --profile extras up -d dockge
```

Then:

```bash
homelab dockge status
```

## Restart Service

```bash
homelab dockge restart
```

## Logs

```bash
homelab dockge logs
```

## Open Shell

```bash
homelab dockge shell
```

## Persistent Data

```text
data/dockge/          Dockge internal data and accounts
data/dockge/stacks/   New compose stacks created via Dockge
```

## Managing the Existing Stack

The repository root is bind-mounted into Dockge as the stack `pi-dev-stack`:

```text
/compose/stacks/pi-dev-stack -> ./  (the repo)
/compose/stacks/             -> ./data/dockge/stacks/  (new stacks)
```

So Dockge sees `pi-dev-stack` as an existing stack and can start, stop, restart, and tail logs for every service defined in `docker-compose.yml`. New stacks created from the UI are stored under `./data/dockge/stacks/`.

### Editing Compose via Dockge

Because the repo is mounted read-write, editing `pi-dev-stack` from Dockge writes directly to the tracked `docker-compose.yml`. This can conflict with `git pull`. Prefer editing `docker-compose.yml` by hand and use Dockge for operating the stack, or keep Dockge edits in separate stacks under `./data/dockge/stacks/`.

## Exposing to the LAN

By default Dockge is bound to `127.0.0.1`. To access it from other devices on your network, set in `.env`:

```env
DOCKGE_WEB_BIND=0.0.0.0
```

Then restart:

```bash
homelab dockge restart
```

## Ports

| Port | Protocol | Purpose |
|---:|---|---|
| 5001 | TCP | Web UI |

## Security Notes

- Dockge has access to the Docker socket, so it can control every container on the host.
- The repo mount includes `.env`, which holds secrets. Keep Dockge localhost-bound unless you understand the exposure.
- First-run admin account is created in the UI.

## Troubleshooting

### Stack Not Visible

Confirm Dockge is running and the repo mount is present:

```bash
homelab service inspect dockge
```

### Cannot Start a Service

Check that `.env` exists in the repo root with required variables; compose variable interpolation fails without it.

```bash
homelab dockge logs
```
