import { z } from "zod";
import { ALLOWED_SERVICES, assertAllowedService, assertWriteAllowed, type RuntimeConfig } from "./config.js";
import { formatResult, type CommandRunner } from "./runner.js";

export type ToolDef = {
  name: string;
  description: string;
  inputSchema: z.ZodTypeAny;
  handler: (input: unknown) => Promise<string>;
};

const EmptySchema = z.object({}).optional().default({});
const ServiceSchema = z.object({ service: z.enum(ALLOWED_SERVICES) });
const LogsSchema = z.object({ service: z.enum(ALLOWED_SERVICES).optional() });
const ModelSchema = z.object({ model: z.string().min(1).max(120).regex(/^[a-zA-Z0-9._:\/-]+$/) });
const BackupPruneSchema = z.object({ days: z.number().int().min(1).max(365).default(7) });
const TunnelSchema = z.object({ group: z.string().min(1).max(50).regex(/^[a-zA-Z0-9_-]+$/).default("core") });

function withJson(args: string[]): string[] {
  return [...args, "--json"];
}

export function createTools(config: RuntimeConfig, run: CommandRunner): ToolDef[] {
  return [
    {
      name: "homelab_status",
      description: "Show Docker Compose service status for the Pi Dev Stack.",
      inputSchema: EmptySchema,
      handler: async () => formatResult(await run(withJson(["status"]))),
    },
    {
      name: "homelab_doctor",
      description: "Run homelab diagnostics for Docker, Compose, cloudflared, Tailscale, disk, memory, temperature, and containers.",
      inputSchema: EmptySchema,
      handler: async () => formatResult(await run(withJson(["doctor"]))),
    },
    {
      name: "homelab_list_services",
      description: "List services known to the Pi Dev Stack CLI.",
      inputSchema: EmptySchema,
      handler: async () => formatResult(await run(withJson(["service", "list"]))),
    },
    {
      name: "homelab_get_service_logs",
      description: "Get Docker Compose logs. Pass a service for one service, or omit it for stack logs.",
      inputSchema: LogsSchema,
      handler: async (input) => {
        const parsed = LogsSchema.parse(input ?? {});
        if (parsed.service) assertAllowedService(parsed.service);
        const args = parsed.service ? ["logs", parsed.service] : ["logs"];
        return formatResult(await run(args, { timeoutMs: 10_000 }));
      },
    },
    {
      name: "homelab_get_urls",
      description: "Show saved Cloudflare tunnel URLs from local state.",
      inputSchema: EmptySchema,
      handler: async () => formatResult(await run(withJson(["urls"]))),
    },
    {
      name: "homelab_security_check",
      description: "Run safe security checks for default secrets, port binding, and Docker socket mounts.",
      inputSchema: EmptySchema,
      handler: async () => formatResult(await run(withJson(["security", "check"]))),
    },
    {
      name: "homelab_system_info",
      description: "Show operating system, architecture, kernel, and current user information.",
      inputSchema: EmptySchema,
      handler: async () => formatResult(await run(withJson(["system-info"]))),
    },
    {
      name: "homelab_list_models",
      description: "List local Ollama models through the Ollama API.",
      inputSchema: EmptySchema,
      handler: async () => formatResult(await run(withJson(["model", "list"]))),
    },
    {
      name: "homelab_recommend_models",
      description: "Show recommended small Ollama models for Raspberry Pi.",
      inputSchema: EmptySchema,
      handler: async () => formatResult(await run(withJson(["model", "recommend"]))),
    },
    {
      name: "homelab_list_backups",
      description: "List local homelab backup archives.",
      inputSchema: EmptySchema,
      handler: async () => formatResult(await run(withJson(["backup", "list"]))),
    },
    {
      name: "homelab_start_service",
      description: "Start one allowed Docker Compose service. Disabled unless write mode and service control are enabled.",
      inputSchema: ServiceSchema,
      handler: async (input) => {
        assertWriteAllowed(config, "allowServiceControl");
        const { service } = ServiceSchema.parse(input);
        return formatResult(await run(["service", "start", service]));
      },
    },
    {
      name: "homelab_stop_service",
      description: "Stop one allowed Docker Compose service. Disabled unless write mode and service control are enabled.",
      inputSchema: ServiceSchema,
      handler: async (input) => {
        assertWriteAllowed(config, "allowServiceControl");
        const { service } = ServiceSchema.parse(input);
        return formatResult(await run(["service", "stop", service]));
      },
    },
    {
      name: "homelab_restart_service",
      description: "Restart one allowed Docker Compose service. Disabled unless write mode and service control are enabled.",
      inputSchema: ServiceSchema,
      handler: async (input) => {
        assertWriteAllowed(config, "allowServiceControl");
        const { service } = ServiceSchema.parse(input);
        return formatResult(await run(["service", "restart", service]));
      },
    },
    {
      name: "homelab_create_backup",
      description: "Create a local backup archive. Disabled unless write mode and backups are enabled.",
      inputSchema: EmptySchema,
      handler: async () => {
        assertWriteAllowed(config, "allowBackups");
        return formatResult(await run(["backup", "create"], { timeoutMs: 120_000 }));
      },
    },
    {
      name: "homelab_prune_backups",
      description: "Delete backup archives older than a number of days. Disabled unless write mode and backups are enabled.",
      inputSchema: BackupPruneSchema,
      handler: async (input) => {
        assertWriteAllowed(config, "allowBackups");
        const { days } = BackupPruneSchema.parse(input ?? {});
        return formatResult(await run(["backup", "prune", String(days)]));
      },
    },
    {
      name: "homelab_pull_model",
      description: "Pull an Ollama model into the Pi Dev Stack. Disabled unless write mode and model pull are enabled.",
      inputSchema: ModelSchema,
      handler: async (input) => {
        assertWriteAllowed(config, "allowModelPull");
        const { model } = ModelSchema.parse(input);
        return formatResult(await run(["model", "pull", model], { timeoutMs: 600_000 }));
      },
    },
    {
      name: "homelab_start_tunnel",
      description: "Start a Cloudflare quick tunnel group. Disabled unless write mode and tunnels are enabled.",
      inputSchema: TunnelSchema,
      handler: async (input) => {
        assertWriteAllowed(config, "allowTunnels");
        const { group } = TunnelSchema.parse(input ?? {});
        return formatResult(await run(["tunnel", group, "start"], { timeoutMs: 120_000 }));
      },
    },
  ];
}
