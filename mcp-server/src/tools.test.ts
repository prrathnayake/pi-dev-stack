import test from "node:test";
import assert from "node:assert/strict";
import type { RuntimeConfig } from "./config.js";
import { createTools } from "./tools.js";
import type { CommandRunner } from "./runner.js";

function config(overrides: Partial<RuntimeConfig> = {}): RuntimeConfig {
  return {
    repoRoot: process.cwd(),
    homelabBin: "./homelab",
    readOnly: true,
    allowServiceControl: false,
    allowModelPull: false,
    allowBackups: false,
    allowTunnels: false,
    commandTimeoutMs: 30_000,
    ...overrides,
  };
}

function fakeRunner(calls: string[][]): CommandRunner {
  return async (args) => {
    calls.push(args);
    return { command: "./homelab", args, exitCode: 0, stdout: "ok", stderr: "", ok: true };
  };
}

test("read-only status tool calls homelab status", async () => {
  const calls: string[][] = [];
  const tools = createTools(config(), fakeRunner(calls));
  const tool = tools.find((item) => item.name === "homelab_status");
  assert.ok(tool);
  const output = await tool.handler({});
  assert.match(output, /"ok": true/);
  assert.deepEqual(calls, [["status"]]);
});

test("service restart is blocked in read-only mode", async () => {
  const calls: string[][] = [];
  const tools = createTools(config(), fakeRunner(calls));
  const tool = tools.find((item) => item.name === "homelab_restart_service");
  assert.ok(tool);
  await assert.rejects(() => tool.handler({ service: "n8n" }), /read-only mode/);
  assert.deepEqual(calls, []);
});

test("service restart validates allowed services", async () => {
  const calls: string[][] = [];
  const tools = createTools(config({ readOnly: false, allowServiceControl: true }), fakeRunner(calls));
  const tool = tools.find((item) => item.name === "homelab_restart_service");
  assert.ok(tool);
  await assert.rejects(() => tool.handler({ service: "bad-service" }), /Invalid enum value|Expected/);
  assert.deepEqual(calls, []);
});

test("service restart runs when explicitly enabled", async () => {
  const calls: string[][] = [];
  const tools = createTools(config({ readOnly: false, allowServiceControl: true }), fakeRunner(calls));
  const tool = tools.find((item) => item.name === "homelab_restart_service");
  assert.ok(tool);
  await tool.handler({ service: "n8n" });
  assert.deepEqual(calls, [["service", "restart", "n8n"]]);
});

test("model names are constrained before command execution", async () => {
  const calls: string[][] = [];
  const tools = createTools(config({ readOnly: false, allowModelPull: true }), fakeRunner(calls));
  const tool = tools.find((item) => item.name === "homelab_pull_model");
  assert.ok(tool);
  await assert.rejects(() => tool.handler({ model: "llama; rm -rf /" }));
  assert.deepEqual(calls, []);
});
