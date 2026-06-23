<!-- mcp-name: io.github.FunplayAI/funplay-unreal-mcp -->

# funplay-unreal-mcp (stdio bridge)

A tiny, dependency-free stdio ⇄ HTTP bridge that connects MCP clients (Claude
Code, Cursor, VS Code, Codex, …) to the **Funplay MCP server running inside the
Unreal Editor**. All tools and logic live in the editor plugin; this package
just forwards JSON-RPC messages.

## Usage

```bash
funplay-unreal-mcp --url http://127.0.0.1:8765/ --token <token>
```

or via environment variables:

```bash
FUNPLAY_UNREAL_MCP_URL=http://127.0.0.1:8765/ \
FUNPLAY_UNREAL_MCP_TOKEN=<token> \
funplay-unreal-mcp
```

Get the endpoint and token from the Unreal editor: **Tools → Funplay MCP → Log
Endpoint + Token** (printed to the Output Log).

## MCP client config

```json
{
  "mcpServers": {
    "funplay-unreal": {
      "command": "npx",
      "args": ["-y", "funplay-unreal-mcp"],
      "env": {
        "FUNPLAY_UNREAL_MCP_URL": "http://127.0.0.1:8765/",
        "FUNPLAY_UNREAL_MCP_TOKEN": "<token from the Funplay MCP menu>"
      }
    }
  }
}
```

The client launches this bridge over **stdio**; the bridge talks **HTTP** to the
editor. Requires Node.js ≥ 18.

## License

MIT — see [LICENSE](https://github.com/FunplayAI/funplay-unreal-mcp/blob/main/LICENSE).
