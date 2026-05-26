#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { loadConfig } from "./config.js";
import { createHomelabRunner } from "./runner.js";
import { createTools } from "./tools.js";

const config = loadConfig();
const run = createHomelabRunner(config);
const tools = createTools(config, run);
const toolMap = new Map(tools.map((tool) => [tool.name, tool]));

const server = new Server(
  {
    name: "pi-dev-stack-mcp-server",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: tools.map((tool) => ({
    name: tool.name,
    description: tool.description,
    inputSchema: zodToJsonSchema(tool.inputSchema),
  })),
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const tool = toolMap.get(request.params.name);
  if (!tool) {
    throw new Error(`Unknown tool: ${request.params.name}`);
  }

  try {
    const text = await tool.handler(request.params.arguments ?? {});
    return {
      content: [{ type: "text", text }],
    };
  } catch (error) {
    return {
      isError: true,
      content: [
        {
          type: "text",
          text: error instanceof Error ? error.message : String(error),
        },
      ],
    };
  }
});

function zodToJsonSchema(schema: { _def?: unknown }): Record<string, unknown> {
  // Minimal MCP-compatible schema metadata. Runtime validation still happens through Zod in each handler.
  return { type: "object" };
}

const transport = new StdioServerTransport();
await server.connect(transport);
