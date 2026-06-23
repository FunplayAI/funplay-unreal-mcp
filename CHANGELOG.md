# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/) and the project follows
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-06-23

Initial release.

### Added
- In-editor MCP server for Unreal Engine 5, implemented as a pure-Python editor
  plugin (`FunplayMCP`) that auto-starts via `init_unreal.py` — no C++ build.
- Loopback HTTP/1.1 transport (`127.0.0.1:8765` by default) speaking hand-rolled
  JSON-RPC 2.0 / MCP, with automatic port fallback and same-project instance
  attach via a `/health` probe.
- Per-project auth token + DNS-rebinding (Host/Origin) protection.
- Game-thread marshalling via `register_slate_post_tick_callback` so every
  `unreal` API call runs safely on the main thread.
- **62 built-in tools** (25 in the default `core` profile) across actors,
  components, assets, blueprints, materials, levels, Play-In-Editor, screenshots,
  selection, editor state, files, and `execute_python`.
- MCP resources (`unreal://...`) and prompt templates.
- One-click AI-client configuration (Claude Code, Cursor, VS Code, Codex) and a
  project skill / `AGENTS.md` generator, exposed from the **Tools → Funplay MCP**
  editor menu.
- Zero-dependency Node.js stdio bridge (`funplay-unreal-mcp`) published to npm.
