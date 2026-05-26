import path from "node:path";

export const ALLOWED_SERVICES = [
  "postgres",
  "redis",
  "n8n",
  "ollama",
  "open-webui",
  "portainer",
  "dozzle",
  "uptime-kuma",
  "homepage",
  "glances",
  "home-assistant",
] as const;

export type HomelabService = (typeof ALLOWED_SERVICES)[number];

export type RuntimeConfig = {
  repoRoot: string;
  homelabBin: string;
  readOnly: boolean;
  allowServiceControl: boolean;
  allowModelPull: boolean;
  allowBackups: boolean;
  allowTunnels: boolean;
  commandTimeoutMs: number;
};

function envFlag(name: string, defaultValue = false): boolean {
  const value = process.env[name];
  if (value === undefined || value === "") return defaultValue;
  return ["1", "true", "yes", "on"].includes(value.toLowerCase());
}

function envNumber(name: string, defaultValue: number): number {
  const raw = process.env[name];
  if (!raw) return defaultValue;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : defaultValue;
}

export function loadConfig(): RuntimeConfig {
  const repoRoot = path.resolve(process.env.PI_DEV_STACK_ROOT ?? process.cwd());
  return {
    repoRoot,
    homelabBin: process.env.PI_DEV_STACK_HOMELAB_BIN ?? "./homelab",
    readOnly: envFlag("PI_DEV_STACK_MCP_READ_ONLY", true),
    allowServiceControl: envFlag("PI_DEV_STACK_MCP_ALLOW_SERVICE_CONTROL"),
    allowModelPull: envFlag("PI_DEV_STACK_MCP_ALLOW_MODEL_PULL"),
    allowBackups: envFlag("PI_DEV_STACK_MCP_ALLOW_BACKUPS"),
    allowTunnels: envFlag("PI_DEV_STACK_MCP_ALLOW_TUNNELS"),
    commandTimeoutMs: envNumber("PI_DEV_STACK_MCP_TIMEOUT_MS", 30_000),
  };
}

export function assertAllowedService(service: string): asserts service is HomelabService {
  if (!ALLOWED_SERVICES.includes(service as HomelabService)) {
    throw new Error(`Unsupported service: ${service}. Allowed services: ${ALLOWED_SERVICES.join(", ")}`);
  }
}

export function assertWriteAllowed(config: RuntimeConfig, capability: keyof Pick<RuntimeConfig, "allowServiceControl" | "allowModelPull" | "allowBackups" | "allowTunnels">): void {
  if (config.readOnly) {
    throw new Error("MCP server is running in read-only mode. Set PI_DEV_STACK_MCP_READ_ONLY=false and enable the specific capability flag to allow this action.");
  }
  if (!config[capability]) {
    throw new Error(`Capability is disabled: ${capability}`);
  }
}
