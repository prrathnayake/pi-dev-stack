# homelab tui

## Overview

Interactive terminal user interface for monitoring Docker Compose services, system resources, live logs, and the service registry. Built with Textual, featuring a custom orange theme, animated ASCII logo, real-time Docker event updates, and touch-friendly clickable controls.

Launch with:

```bash
homelab tui
```

## First Run

On first launch, `homelab tui` creates a Python virtual environment at `tui/.venv` and installs `textual`, `psutil`, and `pyfiglet` (one-time, ~8s on Raspberry Pi 5). Subsequent launches reuse the venv and start instantly.

Requires `python3` and `python3-venv` on the host:

```bash
sudo apt install -y python3 python3-venv
```

## Layout

```
┌────────────────────────────────────────────────┐
│            homelab (ASCII logo)                 │  ← banner with orange gradient
│  CPU 45% │ MEM 62% │ DISK 71% │ LOAD 1.2       │  ← live stats bar
├────────────────────────────────────────────────┤
│  ▸ Containers   System   Logs   Registry       │  ← clickable menu bar
├────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ n8n      │ │ ollama   │ │ plex     │       │  ← clickable service cards
│  │ ● running│ │ ● running│ │ ○ stopped│       │
│  │ 5678     │ │ 11434    │ │ 32400    │       │
│  │ CPU 2.1% │ │ CPU 0.8% │ │ CPU —    │       │
│  └──────────┘ └──────────┘ └──────────┘       │
├────────────────────────────────────────────────┤
│ [▶ Start] [■ Stop] [↻ Restart] [🔗URL] [📜] [✕]│  ← clickable action buttons
└────────────────────────────────────────────────┘
```

## Touch Support

All interactive elements are clickable for touch screens:
- **Menu bar items** — tap to switch pages
- **Action buttons** — tap Start/Stop/Restart/URL/Logs/Quit
- **Service cards** — tap to select a service
- **Log service list** — tap a service to stream its logs

## Pages

| Page | Key | Content |
|---|---|---|
| Containers | `1` | Scrollable grid of clickable service cards with real-time status, CPU, memory |
| System | `2` | Custom orange gauges for CPU, memory, swap, disk, load, network, temperature |
| Logs | `3` | Clickable service sidebar + streaming log viewer |
| Registry | `4` | Read-only browse of `config/services.tsv` with orange-themed cards |

## Keybindings

| Key | Action |
|---|---|
| `1`-`4` | Switch pages |
| `s` | Start selected service (shows loading spinner) |
| `x` | Stop selected service |
| `r` | Restart selected service |
| `u` | Show selected service URL |
| `l` | Jump to Logs page for selected service |
| `?` | Show help |
| `q` | Quit |

## Real-time Updates

- **Docker event stream** — container start/stop/die events update service cards instantly via `docker events --format json`
- **Container resource stats** — CPU/memory per container polled every 2.5s
- **System stats** — CPU/mem/disk/load/net/temp polled every 1.5s
- **Action feedback** — loading spinner overlay during start/stop/restart actions

## Custom Theme

The TUI uses a custom `pi-orange` theme:
- Primary: `#FF7A1A` (vivid orange)
- Accent: `#FFD580` (pale orange)
- Background: `#1B1410` (warm near-black)
- All gauges, borders, highlights, and the ASCII logo use the orange palette

## Rebuild venv

After dependency changes:

```bash
rm -rf tui/.venv
homelab tui
```

## Troubleshooting

### python3 not found

```bash
sudo apt install -y python3 python3-venv
```

### pyfiglet import error

Rebuild the venv:

```bash
rm -rf tui/.venv
homelab tui
```
