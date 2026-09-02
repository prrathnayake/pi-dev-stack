# Homelab CLI Architecture

## Principles

- Tracked infrastructure remains safe to update with fast-forward-only Git operations.
- Runtime data and machine-specific configuration live only in ignored paths.
- Every external command is executed as an argument array without shell expansion.
- Human-readable and JSON operation paths share validation, safety, and exit behavior.
- Destructive targets must be explicit and confirmation is independent of output format.

## Launcher and Python package

`homelab` is a small POSIX shell bootstrapper. It verifies Python 3.11+, creates `.homelab-venv`, installs the pinned project package, and runs `python -m homelab_cli`.

The Python package is divided by responsibility:

```text
homelab_cli/
  app.py            Typer command groups and public behavior
  context.py        global options, output envelope, confirmations, exit codes
  runner.py         bounded subprocess execution and Docker detection
  registry.py       service metadata and Compose contract validation
  configuration.py  masked reads and atomic .env writes
  backups.py        verified backup, restore, and pruning operations
  tunnels.py        Cloudflare process and URL state
  guided.py         line-oriented interactive command launcher
```

## Service registry

`config/services.tsv` remains the metadata source for names, profiles, groups, aliases, local URLs, and tunnel eligibility. `docker-compose.yml` remains the deployment source. Validation requires both sources to contain the same service set, correct `pi-<service>` container names, and matching core/extras profiles.

## Runtime paths

```text
.env                         local configuration and secrets
.homelab-venv/               managed Python environment
data/                        persistent service data
media/                       media library; never implicitly purged or backed up
backups/                     verified archives
logs/                        tunnel and operational logs
state/tunnels.json           persistent tunnel process and URL state
.local-state/config-backups/ atomic .env backups
.local-state/restore-backups/rollback data from restores
local/                       preserved user-local data; never executed automatically
```

## Command execution

The shared runner captures at most 1 MiB per stream, enforces timeouts, and terminates the complete process group with TERM followed by KILL. Streaming is reserved for explicitly interactive commands such as followed logs and service shells. Docker privilege detection tries the current user and then `sudo -n`; it never opens a hidden password prompt.

## Backups

Backups require `.env` and `data/`, exclude media unless requested, write to a partial archive, validate content, and atomically publish the final file. Restore rejects traversal, links, devices, and unexpected roots, stages extraction, and keeps replaced paths under `.local-state/restore-backups`.
