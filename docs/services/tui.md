# homelab tui

## Overview

Interactive terminal user interface for monitoring Docker Compose services, system resources, live logs, and the service registry.

Launch with:

```bash
homelab tui
```

## First Run

On first launch, `homelab tui` creates a Python virtual environment at `tui/.venv` and installs `textual` and `psutil` (one-time, ~5s on Raspberry Pi 5). Subsequent launches reuse the venv and start instantly.

Requires `python3` and `python3-venv` on the host:

```bash
sudo apt install -y python3 python3-venv
```

## Tabs

| Tab | Key | Content |
|---|---|---|
| Containers | `1` | Live table of all services with state, uptime, CPU, memory, ports. Auto-refreshes every 3s. |
| System | `2` | CPU, memory, swap, disk, load average, network, temperature (psutil). Auto-refreshes every 2s. |
| Logs | `3` | Sidebar of services + streaming log viewer. Select a service to tail its logs live. |
| Registry | `4` | Read-only browse of `config/services.tsv` metadata. |

## Keybindings

| Key | Action |
|---|---|
| `1`-`4` | Switch tabs |
| `s` | Start selected service |
| `x` | Stop selected service |
| `r` | Restart selected service |
| `u` | Show selected service URL |
| `l` | Jump to Logs tab for selected service |
| `c` | Clear log output (on Logs tab) |
| `?` | Show help overlay |
| `q` | Quit |

## Actions

Service actions (`s`, `x`, `r`) call the `homelab` CLI under the hood — no duplicate Docker logic. The container table refreshes immediately after an action completes.

## Data Sources

- **Container status**: `docker compose --profile extras ps --format json`
- **Resource usage**: `docker stats --no-stream`
- **System stats**: `psutil` (CPU, memory, disk, load, network, temperature)
- **Logs**: `docker compose logs -f --tail 100 <service>`
- **Registry**: `config/services.tsv` (read directly)

## Troubleshooting

### python3 not found

```bash
sudo apt install -y python3 python3-venv
```

### venv creation fails

Ensure `python3-venv` is installed:

```bash
sudo apt install -y python3-venv
```

### Rebuild venv after dependency change

```bash
rm -rf tui/.venv
homelab tui
```

### Inspect environment

```bash
tui/.venv/bin/python -m pip list
```
