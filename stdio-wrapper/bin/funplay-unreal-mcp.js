#!/usr/bin/env node
// Funplay MCP for Unreal -- thin stdio <-> HTTP bridge.
//
// AI clients speak MCP over stdio; this process forwards each JSON-RPC message
// verbatim to the Unreal editor plugin's local HTTP endpoint and pipes the
// response back to stdout. All MCP intelligence (tools, profiles, safety) lives
// in the editor plugin -- this bridge holds none of it. Zero dependencies.

import { argv, env, exit, stderr, stdin, stdout } from "node:process";

const VERSION = "0.2.0";
const DEFAULT_URL = "http://127.0.0.1:8765/";

function parseArgs(args) {
  const out = { url: null, token: null, help: false, version: false };
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--help" || arg === "-h") out.help = true;
    else if (arg === "--version" || arg === "-v") out.version = true;
    else if (arg === "--url") out.url = args[++i];
    else if (arg.startsWith("--url=")) out.url = arg.slice("--url=".length);
    else if (arg === "--token") out.token = args[++i];
    else if (arg.startsWith("--token=")) out.token = arg.slice("--token=".length);
  }
  return out;
}

const opts = parseArgs(argv.slice(2));

if (opts.help) {
  stdout.write(
    [
      "funplay-unreal-mcp -- stdio bridge to a local Funplay MCP server for Unreal",
      "",
      "Usage: funplay-unreal-mcp [--url <endpoint>] [--token <token>]",
      "",
      "Environment:",
      "  FUNPLAY_UNREAL_MCP_URL    HTTP endpoint (default http://127.0.0.1:8765/)",
      "  FUNPLAY_UNREAL_MCP_TOKEN  Auth token from the Funplay MCP editor menu",
      "",
    ].join("\n"),
  );
  exit(0);
}
if (opts.version) {
  stdout.write(VERSION + "\n");
  exit(0);
}

const endpoint =
  opts.url || env.FUNPLAY_UNREAL_MCP_URL || env.UNREAL_MCP_URL || DEFAULT_URL;
const authToken =
  opts.token || env.FUNPLAY_UNREAL_MCP_TOKEN || env.UNREAL_MCP_TOKEN || "";

function isJsonRpcRequest(message) {
  return message && typeof message === "object" &&
    Object.prototype.hasOwnProperty.call(message, "id");
}

function writeMessage(message) {
  if (message === null || message === undefined) return;
  stdout.write(JSON.stringify(message) + "\n");
}

function buildErrorFor(message, code, errMessage) {
  // Only respond to requests (which carry an id); notifications stay silent.
  const list = Array.isArray(message) ? message : [message];
  const responses = list
    .filter(isJsonRpcRequest)
    .map((m) => ({
      jsonrpc: "2.0",
      id: m.id,
      error: { code, message: errMessage },
    }));
  if (!responses.length) return;
  writeMessage(Array.isArray(message) ? responses : responses[0]);
}

async function forwardMessage(message) {
  let response;
  try {
    const headers = {
      accept: "application/json",
      "content-type": "application/json",
    };
    if (authToken) headers["x-funplay-mcp-token"] = authToken;
    response = await fetch(endpoint, {
      method: "POST",
      headers,
      body: JSON.stringify(message),
    });
  } catch (err) {
    buildErrorFor(
      message,
      -32000,
      `Failed to reach Funplay MCP for Unreal at ${endpoint}: ${err.message}. ` +
        "Is the editor open with the MCP server running?",
    );
    return;
  }

  if (response.status === 204) return; // notification accepted, no body
  const text = await response.text();
  if (!text) {
    buildErrorFor(message, -32603, "Empty response from Unreal MCP server");
    return;
  }
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    buildErrorFor(message, -32603, "Invalid JSON from Unreal MCP server");
    return;
  }
  writeMessage(parsed);
}

// Serialize message handling so responses keep input order.
let queue = Promise.resolve();
function enqueue(line) {
  const trimmed = line.trim();
  if (!trimmed) return;
  let message;
  try {
    message = JSON.parse(trimmed);
  } catch {
    writeMessage({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } });
    return;
  }
  queue = queue.then(() => forwardMessage(message)).catch((err) => {
    stderr.write(`[funplay-unreal-mcp] ${err && err.stack ? err.stack : err}\n`);
  });
}

let buffer = "";
stdin.setEncoding("utf8");
stdin.on("data", (chunk) => {
  buffer += chunk;
  let index = buffer.indexOf("\n");
  while (index !== -1) {
    const line = buffer.slice(0, index);
    buffer = buffer.slice(index + 1);
    enqueue(line);
    index = buffer.indexOf("\n");
  }
});
stdin.on("end", () => {
  if (buffer.trim()) enqueue(buffer);
});
