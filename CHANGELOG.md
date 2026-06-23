# Changelog

## Unreleased

## [0.2.0] - 2026-06-23

### Added
- Expanded the Unreal tool set from 62 to 97 tools, with 32 exposed in the default `core` profile.
- Added API discovery, viewport control, procedural builders, material graph editing, DataTables, UMG, Niagara, organization, instancing, asset-reference lookup, health checks, undo/redo, output-log filtering, screenshot UI capture, and optional-plugin probes.
- Added undo-transaction grouping for batch and procedural mutations, plus a safety denylist for console commands.

### Fixed
- Fixed `list_layers` on Unreal versions where `EditorLevelLibrary.add_all_layer_names_to()` takes no output argument.
- Fixed Codex one-click TOML config updates so the existing `funplay-unreal` env table is replaced instead of leaving stale tokens or duplicate tables.
- Fixed README tool-count copy for the 32-tool `core` profile and 97-tool `full` profile.

### Notes
- Blueprint event-graph node wiring remains out of scope because the K2 graph API is not exposed to Python; Blueprint support covers structure, components, CDO defaults, and compile.

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
