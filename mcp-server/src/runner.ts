import { spawn } from "node:child_process";
import type { RuntimeConfig } from "./config.js";

export type CommandResult = {
  command: string;
  args: string[];
  exitCode: number | null;
  stdout: string;
  stderr: string;
  ok: boolean;
};

export type CommandRunner = (args: string[], options?: { timeoutMs?: number }) => Promise<CommandResult>;

export function createHomelabRunner(config: RuntimeConfig): CommandRunner {
  return async (args, options = {}) => {
    const timeoutMs = options.timeoutMs ?? config.commandTimeoutMs;

    return new Promise<CommandResult>((resolve, reject) => {
      const child = spawn(config.homelabBin, args, {
        cwd: config.repoRoot,
        shell: false,
        env: process.env,
      });

      let stdout = "";
      let stderr = "";
      let timedOut = false;

      const timer = setTimeout(() => {
        timedOut = true;
        child.kill("SIGTERM");
      }, timeoutMs);

      child.stdout.on("data", (chunk) => {
        stdout += chunk.toString();
      });
      child.stderr.on("data", (chunk) => {
        stderr += chunk.toString();
      });
      child.on("error", reject);
      child.on("close", (exitCode) => {
        clearTimeout(timer);
        const result: CommandResult = {
          command: config.homelabBin,
          args,
          exitCode,
          stdout: stdout.trim(),
          stderr: (timedOut ? `${stderr}\nCommand timed out after ${timeoutMs}ms` : stderr).trim(),
          ok: exitCode === 0 && !timedOut,
        };
        resolve(result);
      });
    });
  };
}

export function formatResult(result: CommandResult): string {
  return JSON.stringify(result, null, 2);
}
