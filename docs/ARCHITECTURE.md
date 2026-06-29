# Homelab Runtime Architecture

## Core principle

Tracked infrastructure files should remain stable and updateable through:

```bash
git pull
```

All runtime-generated information, user configuration, and machine-specific state must be stored in ignored local folders.

## CLI structure

The `homelab` command is a modular bash CLI:

```text
homelab                  entry point — flag parsing, lib loading, dispatch
lib/
  output.sh              text + JSON output helpers
  docker.sh              Docker command detection, compose helpers
  registry.sh            service registry loader and query functions
  system.sh              OS detection
config/
  services.tsv           service registry (single source of truth)
commands/
  up.sh    down.sh    restart.sh   status.sh   logs.sh
  doctor.sh validate.sh backup.sh   update.sh   install.sh
  tunnel.sh service.sh  pihole.sh   help.sh
```

### Service registry

`config/services.tsv` is the single source of truth for service metadata.

Pipe-delimited columns:

```text
name|profile|group|port|scheme|path|aliases|tunnel|tunnel_groups|url_note
```

Adding a new service to `docker-compose.yml` requires one additional line in the registry. The CLI automatically picks up the new service for `service list`, `url`, tunnel groups, and `homelab <service> <action>` aliases.

### Local extensions

User-defined commands can be added as scripts in `local/cli.d/*.sh`. These are sourced at startup and can define a `local_cli_command` function for custom dispatch.

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

- runtime event bus
- background daemon mode
- JSON API server for homelab CLI
- web dashboard frontend
