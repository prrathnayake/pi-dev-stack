# Contributing

## Development setup

```bash
git clone https://github.com/prrathnayake/pi-dev-stack.git
cd pi-dev-stack
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Run the checks:

```bash
.venv/bin/ruff check homelab_cli tests
.venv/bin/pytest
docker compose --profile extras config
sh -n homelab
```

## CLI rules

- Preserve the structured result envelope and documented exit codes.
- Route external processes through the shared runner.
- Do not use shell expansion for user-controlled input.
- Propagate underlying failures instead of printing unconditional success.
- Make destructive targets explicit and require confirmation or `--yes`.
- Do not let `--json` weaken confirmation behavior.
- Mask secrets in both text and JSON unless the user explicitly requests disclosure.
- Keep service metadata and Compose definitions synchronized.

## Local state

Never commit secrets or generated machine state. Do not alter user-owned `.env`, `data/`, `media/`, `logs/`, `backups/`, `.local-state/`, `state/`, or `local/` content in changes or tests.

## Pull requests

- Add or update tests for public behavior and failure paths.
- Run the full Python, shell, and Compose checks.
- Update user documentation when command behavior changes.
- Preserve Raspberry Pi ARM64 and AMD64 Linux support.
