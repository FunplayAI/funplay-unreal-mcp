# Changelog

## Unreleased

## [0.2.0] - 2026-06-23

### Added
- Added a competitor-informed capability expansion that grows the tool set from
  62 to **97 tools** (32 core), all pure-Python.
- **Reflection** (`search_api`, `describe_class`, `list_enum_values`,
  `inspect_object`) — discover the real `unreal` API instead of guessing it.
- **Viewport** (`set_viewport_camera`, `get_viewport_camera`, `focus_viewport`)
  — deterministic "aim then screenshot" loop.
- **Procedural builders** (`build_wall`, `build_floor`, `build_stairs`,
  `scatter_actors`) — whole structures from one prompt, in one undo.
- **Material graph editing** (`add_material_expression`,
  `connect_material_expressions`, `connect_material_property`,
  `recompile_material`).
- **DataTables** (`create_data_table`, `get_data_table`, `set_data_table_rows`,
  `export_data_table_csv`), **UMG** (`create_widget_blueprint`, `add_widget`,
  `set_widget_property`), **Niagara** (`spawn_niagara_system`,
  `set_niagara_parameter`), **organization** (`set_actor_folder`, layers).
- `batch_spawn_actors`, `set_physics_properties`, `add_ism_instances`,
  `get_asset_references`, `health_status`, `undo`/`redo`.
- Undo-transaction grouping for batch/procedural mutations; `run_console_command`
  safety denylist; `get_output_log` substring filtering; `take_screenshot`
  `show_ui` option; soft-dependency probes for optional plugins (Niagara, UMG).

### Fixed
- Fixed `list_layers` for Unreal versions where
  `EditorLevelLibrary.add_all_layer_names_to()` takes no output argument.
- Fixed Codex one-click TOML config updates so replacing the
  `funplay-unreal` server also replaces its existing env child table, avoiding
  stale tokens or duplicate TOML tables.
- Fixed README tool-count copy so the default `core` and `full` profiles are
  documented as 32 and 97 tools.

### Notes
- Blueprint **event-graph node wiring** remains intentionally out of scope — every
  competitor needs a C++ helper for it (the K2 graph API is not exposed to
  Python). Blueprint support stays structure + components + CDO defaults + compile.

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
