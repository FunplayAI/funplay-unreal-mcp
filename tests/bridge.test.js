// Tests for the stdio <-> HTTP bridge, runnable without Unreal.
import { test } from "node:test";
import assert from "node:assert";
import http from "node:http";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { fileURLToPath } from "node:url";
import path from "node:path";

const BIN = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "stdio-wrapper",
  "bin",
  "funplay-unreal-mcp.js",
);

function startMockEditor() {
  const server = http.createServer((req, res) => {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      const msg = JSON.parse(body || "{}");
      if (!Object.prototype.hasOwnProperty.call(msg, "id")) {
        res.writeHead(204).end(); // notification
        return;
      }
      const out = JSON.stringify({
        jsonrpc: "2.0",
        id: msg.id,
        result: { method: msg.method, token: req.headers["x-funplay-mcp-token"] || null },
      });
      res.writeHead(200, { "Content-Type": "application/json" }).end(out);
    });
  });
  return server;
}

async function runBridge(server, lines) {
  await once(server.listen(0, "127.0.0.1"), "listening");
  const { port } = server.address();
  const child = spawn(process.execPath, [BIN], {
    env: {
      ...process.env,
      FUNPLAY_UNREAL_MCP_URL: `http://127.0.0.1:${port}/`,
      FUNPLAY_UNREAL_MCP_TOKEN: "tkn",
    },
  });
  let out = "";
  child.stdout.on("data", (c) => (out += c));
  child.stdin.write(lines);
  child.stdin.end();
  await once(child, "exit");
  server.close();
  return out.trim().split("\n").filter(Boolean).map((l) => JSON.parse(l));
}

test("forwards a request and pipes the response with the auth token", async () => {
  const responses = await runBridge(
    startMockEditor(),
    JSON.stringify({ jsonrpc: "2.0", id: 7, method: "tools/list", params: {} }) + "\n",
  );
  assert.equal(responses.length, 1);
  assert.equal(responses[0].id, 7);
  assert.equal(responses[0].result.method, "tools/list");
  assert.equal(responses[0].result.token, "tkn");
});

test("a notification produces no stdout", async () => {
  const responses = await runBridge(
    startMockEditor(),
    JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n",
  );
  assert.equal(responses.length, 0);
});

test("an unparseable line yields a -32700 parse error", async () => {
  const responses = await runBridge(startMockEditor(), "this is not json\n");
  assert.equal(responses.length, 1);
  assert.equal(responses[0].error.code, -32700);
});
