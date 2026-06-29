# Homelab Runtime Architecture

## Core principle

Tracked infrastructure files should remain stable and updateable through:

```bash
git pull
```

All runtime-generated information, user configuration, and machine-specific state must be stored in ignored local folders.

## Runtime state folders

### state/

Persistent generated runtime state.

Examples:

```text
state/tunnels.json
state/system-info.json
state/desktop.json
state/services.json
```

### .local-state/

Ephemeral machine-local runtime cache.

Examples:

```text
.local-state/current-urls.txt
.local-state/doctor-report.txt
.local-state/dashboard-cache.json
```

### local/

User custom scripts and extensions.

Examples:

```text
local/custom-tunnels.sh
local/backup-hooks.sh
local/desktop-start.sh
```

### media/

Plex media library bind mount. Not part of `data/` so it is excluded from
`homelab backup` by design (large, often already backed up elsewhere).

Examples:

```text
media/movies
media/tv
media/music
```

## Generated configuration

Generated configs should never overwrite tracked templates.

Examples:

```text
Tracked template:
cloudflared/config.example.yml

Generated local file:
cloudflared/config.yml
```

## Safe update workflow

The goal is:

```bash
git pull
```

without conflicts.

This is achieved by:

- never editing tracked runtime files locally
- generating machine-specific state into ignored folders
- using templates + generated configs
- separating runtime state from infrastructure code

## Recommended future improvements

- SQLite runtime metadata database
- plugin system under local/plugins/
- YAML-driven service registry
- runtime event bus
- background daemon mode
- JSON API server for homelab CLI
- web dashboard frontend
