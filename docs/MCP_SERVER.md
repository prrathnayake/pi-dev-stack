# Pi Dev Stack MCP Server

The Pi Dev Stack MCP server lets AI clients inspect and safely operate a Raspberry Pi homelab through the existing `homelab` CLI.

It is read-only by default. Write actions must be enabled explicitly with environment variables.

## Location

```text
mcp-server/
```

## Install

From the repository root:

```bash
cd mcp-server
npm install
npm run build
```

## Run

```bash
cd /path/to/pi-dev-stack/mcp-server
PI_DEV_STACK_ROOT=/path/to/pi-dev-stack npm start
```

If your MCP client launches the built server directly:

```bash
node /path/to/pi-dev-stack/mcp-server/dist/index.js
```

## Example MCP client config

```json
{
  "mcpServers": {
    "pi-dev-stack": {
      "command": "node",
      "args": ["/path/to/pi-dev-stack/mcp-server/dist/index.js"],
      "env": {
        "PI_DEV_STACK_ROOT": "/path/to/pi-dev-stack",
        "PI_DEV_STACK_MCP_READ_ONLY": "true"
      }
    }
  }
}
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PI_DEV_STACK_ROOT` | current working directory | Path to the Pi Dev Stack repo |
| `PI_DEV_STACK_HOMELAB_BIN` | `./homelab` | Homelab CLI path relative to `PI_DEV_STACK_ROOT` |
| `PI_DEV_STACK_MCP_READ_ONLY` | `true` | Blocks all write actions by default |
| `PI_DEV_STACK_MCP_ALLOW_SERVICE_CONTROL` | `false` | Allows service start/stop/restart when read-only is false |
| `PI_DEV_STACK_MCP_ALLOW_MODEL_PULL` | `false` | Allows Ollama model pulls when read-only is false |
| `PI_DEV_STACK_MCP_ALLOW_BACKUPS` | `false` | Allows backup create/prune when read-only is false |
| `PI_DEV_STACK_MCP_ALLOW_TUNNELS` | `false` | Allows tunnel start when read-only is false |
| `PI_DEV_STACK_MCP_TIMEOUT_MS` | `30000` | Default command timeout |

## Read-only tools

| Tool | Purpose |
|---|---|
| `homelab_status` | Show Docker Compose service status |
| `homelab_doctor` | Run system and stack diagnostics |
| `homelab_list_services` | List known stack services |
| `homelab_get_service_logs` | Get stack or service logs |
| `homelab_get_urls` | Show saved tunnel URLs |
| `homelab_security_check` | Check default secrets, port binding, and Docker socket mounts |
| `homelab_system_info` | Show OS, architecture, kernel, and user |
| `homelab_list_models` | List local Ollama models |
| `homelab_recommend_models` | Show Pi-friendly model suggestions |
| `homelab_list_backups` | List backup archives |

## Controlled write tools

These require `PI_DEV_STACK_MCP_READ_ONLY=false` plus a matching capability flag.

| Tool | Required flag |
|---|---|
| `homelab_start_service` | `PI_DEV_STACK_MCP_ALLOW_SERVICE_CONTROL=true` |
| `homelab_stop_service` | `PI_DEV_STACK_MCP_ALLOW_SERVICE_CONTROL=true` |
| `homelab_restart_service` | `PI_DEV_STACK_MCP_ALLOW_SERVICE_CONTROL=true` |
| `homelab_create_backup` | `PI_DEV_STACK_MCP_ALLOW_BACKUPS=true` |
| `homelab_prune_backups` | `PI_DEV_STACK_MCP_ALLOW_BACKUPS=true` |
| `homelab_pull_model` | `PI_DEV_STACK_MCP_ALLOW_MODEL_PULL=true` |
| `homelab_start_tunnel` | `PI_DEV_STACK_MCP_ALLOW_TUNNELS=true` |

## Safety model

The MCP server does not expose arbitrary shell execution.

It only calls allowlisted `homelab` commands and validates input before execution:

- service names are restricted to known Docker Compose services
- model names are restricted to safe characters
- destructive reset and restore commands are not exposed
- `.env` display and secret inspection are not exposed
- service shell access is not exposed

For admin actions, prefer Tailscale or a local terminal.

## Development

```bash
cd mcp-server
npm install
npm run build
npm test
```

## CI

GitHub Actions runs:

- TypeScript compilation
- MCP unit tests
- existing Compose and homelab CLI validation
- existing core container smoke tests
