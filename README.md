<p align="center">
  <h1 align="center">Funplay MCP for Unreal</h1>
  <p align="center"><strong>The most advanced MCP server for the Unreal Editor.</strong></p>
  <p align="center">
    <img src="https://img.shields.io/badge/Unreal%20Engine-5.3%E2%80%935.8-blue" alt="Unreal Engine 5.3-5.8" />
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT" />
    <img src="https://img.shields.io/badge/MCP-compatible-purple" alt="MCP compatible" />
    <img src="https://img.shields.io/badge/editor-only-lightgrey" alt="Editor only" />
  </p>
  <p align="center"><a href="./README_CN.md">中文</a> | English</p>
</p>

> 💖 If this saves you time, please star the repo — it helps a lot.

---

Funplay MCP for Unreal lets AI assistants — **Claude Code, Cursor, Windsurf, Codex,
VS Code Copilot** and any other MCP client — operate directly inside a running
Unreal Editor. It is a **pure-Python editor plugin** (no C++ build, works across
Unreal Engine 5.3–5.8) that exposes the editor over a local MCP server, plus a
tiny Node.js stdio bridge that connects your AI client to it. MIT-licensed and
free for commercial use.

Describe what you want in natural language — *spawn and arrange actors, build
levels and Blueprints, create materials, import assets, drive Play-In-Editor,
capture screenshots, or run arbitrary `execute_python`* — and let the assistant
do it.

> "Build a small arena: a floor, four walls, some point lights, and a player
> start in the middle. Then play it and send me a screenshot."
>
> The assistant inspects the level, spawns and positions the actors, sets up
> lighting, enters Play-In-Editor, and returns a screenshot — all through this
> MCP server.

## Demo

<p align="center">
  <img src="./docs/assets/codex-to-unreal-castle-demo.gif" alt="Codex uses Funplay MCP to build a castle in Unreal Editor" width="900" />
</p>

Codex asks for a castle, Funplay MCP drives the Unreal Editor through MCP, and
the finished scene appears directly in the editor.

## Quick Start

Three things: **(1)** drop the plugin into your project, **(2)** enable it and
start the server, **(3)** point your AI client at it.

### 1. Install the plugin

> 💡 The plugin is pure Python — there is nothing to compile.

- Copy the `FunplayMCP/` folder into your project's `Plugins/` directory
  (`<YourProject>/Plugins/FunplayMCP/`), **or** download
  `Funplay.UnrealMcp.vX.Y.Z.zip` from the latest [Release](https://github.com/FunplayAI/funplay-unreal-mcp/releases)
  and extract it there.
- It depends on the engine's **Python Editor Script Plugin**, which the
  `.uplugin` enables automatically.

### 2. Enable and start the MCP Server

- Open your project. In **Edit → Plugins**, confirm **Funplay MCP for Unreal** is
  enabled, then restart the editor if prompted.
- On startup the server listens at `http://127.0.0.1:8765/` by default. If the
  port is busy it automatically picks a free local port (and a second editor of
  the *same* project attaches to the existing server).
- A per-project **auth token** is generated and stored in
  `<YourProject>/Saved/FunplayMCP/funplay_mcp_settings.json`.
- Get the endpoint and token any time from **Tools → Funplay MCP → Log Endpoint
  + Token** (printed to the Output Log).

### 3. Configure your AI client

The fastest path is the editor menu: **Tools → Funplay MCP → Configure Claude
Code** (or Cursor / VS Code / Codex). It writes the right config with the
endpoint and token filled in.

<details>
<summary>Manual configuration</summary>

**Claude Code** (`~/.claude.json`), **Cursor** (`~/.cursor/mcp.json`):

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

**VS Code** (`mcp.json`) uses the `servers` key; **Codex**
(`~/.codex/config.toml`) uses a `[mcp_servers."funplay-unreal"]` table. Both are
written for you by the one-click menu.
</details>

### 4. Verify the connection

Ask your assistant to:
- call `get_project_info`,
- read the resource `unreal://project/context`,
- run `execute_python` with `result = unreal.SystemLibrary.get_engine_version()`.

## Before You Start

- **Editor only.** The server runs inside the Unreal Editor; it does not ship in
  packaged games.
- **Loopback only.** It binds `127.0.0.1` and rejects non-loopback Origins; POST
  requests require the per-project auth token.
- **Default `core` profile.** A focused 32-tool set is exposed by default; switch
  to `full` (97 tools) in the settings file when you want everything.
- **`execute_python` safety checks** are on by default (a filesystem/process
  denylist); pass `safety_checks=false` to override per call.
- All `unreal` API work is marshalled onto the game thread, so the editor never
  crashes from off-thread access.

## Why This Project

- **`execute_python` first.** A first-class tool that runs arbitrary Python in
  the editor — anything the 96 dedicated tools don't cover, you can still do.
- **API discovery built in.** `search_api` / `describe_class` / `inspect_object`
  read the embedded `unreal` module's own docs, so the assistant uses the real
  API instead of hallucinating it.
- **Pure Python, no build.** No C++ module, no compile step, portable across UE
  5.3–5.8.
- **Safe by construction.** Game-thread marshalling, loopback binding, auth
  token, and DNS-rebinding protection out of the box.
- **One-click client config + project skills.** Configure Claude Code / Cursor /
  VS Code / Codex and generate an `AGENTS.md` bridge from the editor menu.
- **Same family, same conventions** as Funplay MCP for Unity / Godot / Cocos.

## Highlights

- **97 built-in tools** (32 in the default `core` profile) across 20 categories.
- **MCP resources** (`unreal://...`) for project, level, selection, logs, and the
  tool catalog, plus **prompt templates** for common workflows.
- **Structured results** — every tool returns JSON the assistant can reason over;
  screenshots come back as inline images.
- **Auto port-fallback** and **same-project instance attach**.
- **Zero-dependency Node bridge** published to npm as `funplay-unreal-mcp`.

## MCP Capabilities

- **Tools:** 97 (32 core / 97 full).
- **Primary execution:** `execute_python` — run any Python snippet in the editor.
- **Prompts:** `level_review`, `feature_plan`, `debug_runtime`, `blueprint_actor`.
- **Resources:** `unreal://project/context`, `unreal://project/info`,
  `unreal://level/current`, `unreal://actors/list`, `unreal://selection/current`,
  `unreal://tools/catalog`, `unreal://logs/recent`, `unreal://interaction/history`,
  plus templates `unreal://actor/{ref}` and `unreal://asset/{path}`.

## Comparison with Funplay MCP for Unity

| | Funplay MCP for Unreal | Funplay MCP for Unity |
|---|---|---|
| Editor side | Pure-Python plugin (no build) | C# package |
| Primary execution | `execute_python` (embedded `unreal`) | `execute_code` (in-memory C#) |
| Transport | Local HTTP + stdio bridge | Local HTTP + stdio bridge |
| Default exposure | `core` profile (32 of 97) | `core` profile |
| Engine versions | UE 5.3–5.8 | Unity 2022.3+ |
| Client config | One-click (Claude/Cursor/VS Code/Codex) | One-click |

## Built-in Tools

**97 built-in tools** (32 `core`). Call `get_tool_catalog` for the live list.

| Category | Tools |
|---|---|
| Execution | `execute_python`, `run_console_command` |
| Reflection | `search_api`, `describe_class`, `list_enum_values`, `inspect_object` |
| Actors | `spawn_actor`, `spawn_actor_from_asset`, `destroy_actor`, `duplicate_actor`, `set_actor_transform`, `set_actor_label`, `set_actor_property`, `attach_actor`, `get_actor_info`, `list_actors`, `find_actors`, `batch_spawn_actors` |
| Components | `add_component`, `list_components`, `get_component_properties`, `set_component_property`, `set_static_mesh`, `set_material`, `set_physics_properties`, `add_ism_instances` |
| Assets | `list_assets`, `find_assets`, `get_asset_info`, `duplicate_asset`, `rename_asset`, `delete_asset`, `save_asset`, `import_asset`, `create_folder`, `asset_exists`, `get_asset_references` |
| Blueprints | `create_blueprint`, `add_blueprint_component`, `compile_blueprint`, `get_blueprint_info`, `spawn_blueprint` |
| Materials | `create_material`, `create_material_instance`, `set_material_instance_parameter`, `get_material_info`, `add_material_expression`, `connect_material_expressions`, `connect_material_property`, `recompile_material` |
| Levels | `new_level`, `load_level`, `save_current_level`, `save_all_dirty`, `get_level_info`, `list_levels` |
| Play-In-Editor | `play_in_editor`, `stop_play_in_editor`, `simulate_in_editor`, `get_play_state` |
| Viewport | `set_viewport_camera`, `get_viewport_camera`, `focus_viewport` |
| Screenshots | `take_screenshot` |
| Selection | `get_selection`, `set_selection`, `select_none`, `get_selected_assets` |
| Editor State | `get_editor_state`, `get_project_info`, `get_output_log`, `sync_content_browser`, `health_status`, `undo`, `redo` |
| Files | `read_file`, `write_file`, `list_directory`, `file_exists` |
| Procedural | `build_wall`, `build_floor`, `build_stairs`, `scatter_actors` |
| Organization | `set_actor_folder`, `create_layer`, `add_actors_to_layer`, `list_layers` |
| Data | `create_data_table`, `get_data_table`, `set_data_table_rows`, `export_data_table_csv` |
| UMG | `create_widget_blueprint`, `add_widget`, `set_widget_property` |
| Effects | `spawn_niagara_system`, `set_niagara_parameter` |
| Discovery | `get_tool_catalog` |

## Repository Layout

```
FunplayMCP/                         # the Unreal editor plugin (pure Python)
  FunplayMCP.uplugin
  Content/Python/
    init_unreal.py                  # auto-run entry point
    funplay_mcp/                    # server, transport, registry, providers
      tools/                        # one module per tool category
stdio-wrapper/                      # zero-dependency Node.js stdio<->HTTP bridge
scripts/                           # validate_repo.py, package_release.py
tests/                             # Node + Python tests (run without the editor)
server.json                        # MCP registry manifest
```

## Architecture

```
AI client (Claude Code / Cursor / ...)
        │  stdio (MCP JSON-RPC)
        ▼
funplay-unreal-mcp  (Node bridge, npx)
        │  HTTP + token  →  127.0.0.1:8765
        ▼
Unreal Editor plugin (Python)
        │  game-thread pump (register_slate_post_tick_callback)
        ▼
unreal API  →  Actors / Assets / Blueprints / Levels / PIE
```

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). Run `python3 scripts/validate_repo.py`
before opening a PR.

## License

MIT — see [LICENSE](./LICENSE).
