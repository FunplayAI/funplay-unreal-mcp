<p align="center">
  <h1 align="center">Funplay MCP for Unreal</h1>
  <p align="center"><strong>面向 Unreal 编辑器最先进的 MCP 服务器。</strong></p>
  <p align="center">
    <img src="https://img.shields.io/badge/Unreal%20Engine-5.3%E2%80%935.8-blue" alt="Unreal Engine 5.3-5.8" />
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT" />
    <img src="https://img.shields.io/badge/MCP-compatible-purple" alt="MCP compatible" />
    <img src="https://img.shields.io/badge/editor-only-lightgrey" alt="Editor only" />
  </p>
  <p align="center">中文 | <a href="./README.md">English</a></p>
</p>

> 💖 如果它为你节省了时间，请给仓库点个 star——这对我们帮助很大。

---

Funplay MCP for Unreal 让 AI 助手——**Claude Code、Cursor、Windsurf、Codex、
VS Code Copilot** 以及任何其他 MCP 客户端——直接在运行中的 Unreal 编辑器内进行操作。它是一个
**纯 Python 编辑器插件**（无需编译 C++，可跨 Unreal Engine 5.3–5.8 使用），通过本地 MCP
服务器把编辑器能力暴露出来，并附带一个极小的 Node.js stdio 桥接，把你的 AI 客户端连接到它。采用 MIT
许可，可免费商用。

用自然语言描述你想要什么——*生成并摆放 actor、搭建关卡与蓝图、创建材质、导入资源、驱动
Play-In-Editor、截屏，或运行任意 `execute_python`*——然后让助手去完成。

> “搭一个小型竞技场：一块地板、四面墙、几盏点光源，中间放一个 player
> start。然后运行它并发我一张截图。”
>
> 助手会检查关卡、生成并摆放 actor、设置灯光、进入 Play-In-Editor，并返回一张截图——全部
> 通过这个 MCP 服务器完成。

## 快速开始

只需三步：**(1)** 把插件放进你的项目，**(2)** 启用它并
启动服务器，**(3)** 让你的 AI 客户端指向它。

### 1. 安装插件

> 💡 该插件是纯 Python——没有任何需要编译的东西。

- 把 `FunplayMCP/` 文件夹复制到项目的 `Plugins/` 目录下
  （`<YourProject>/Plugins/FunplayMCP/`），**或者**从最新的 [Release](https://github.com/FunplayAI/funplay-unreal-mcp/releases)
  下载 `Funplay.UnrealMcp.vX.Y.Z.zip`
  并解压到那里。
- 它依赖引擎的 **Python Editor Script Plugin**，而
  `.uplugin` 会自动启用它。

### 2. 启用并启动 MCP 服务器

- 打开你的项目。在 **Edit → Plugins** 中确认 **Funplay MCP for Unreal** 已
  启用，如有提示则重启编辑器。
- 启动时服务器默认监听 `http://127.0.0.1:8765/`。如果该
  端口被占用，它会自动选择一个空闲的本地端口（同一个项目的第二个编辑器
  会附加到现有服务器）。
- 每个项目的 **auth token** 会被生成并存储在
  `<YourProject>/Saved/FunplayMCP/funplay_mcp_settings.json`。
- 随时都可以通过 **Tools → Funplay MCP → Log Endpoint
  + Token**（打印到 Output Log）获取端点和 token。

### 3. 配置你的 AI 客户端

最快的方式是使用编辑器菜单：**Tools → Funplay MCP → Configure Claude
Code**（或 Cursor / VS Code / Codex）。它会写入填好
端点和 token 的正确配置。

<details>
<summary>手动配置</summary>

**Claude Code**（`~/.claude.json`）、**Cursor**（`~/.cursor/mcp.json`）：

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

**VS Code**（`mcp.json`）使用 `servers` 键；**Codex**
（`~/.codex/config.toml`）使用 `[mcp_servers."funplay-unreal"]` 表。两者都会由
一键菜单为你写入。
</details>

### 4. 验证连接

让你的助手：
- 调用 `get_project_info`，
- 读取资源 `unreal://project/context`，
- 用 `result = unreal.SystemLibrary.get_engine_version()` 运行 `execute_python`。

## 开始之前

- **仅限编辑器。** 服务器运行在 Unreal 编辑器内部；它不会随
  打包后的游戏一同发布。
- **仅限回环地址。** 它绑定 `127.0.0.1` 并拒绝非回环的 Origin；POST
  请求需要每个项目的 auth token。
- **默认 `core` 配置。** 默认暴露一组精选的 32 个工具；当你想要全部时，可在设置文件中切换
  到 `full`（97 个工具）。
- **`execute_python` 安全检查** 默认开启（一份文件系统/进程
  黑名单）；可按单次调用传入 `safety_checks=false` 来覆盖。
- 所有 `unreal` API 操作都会被编排到游戏线程上，因此编辑器绝不会
  因跨线程访问而崩溃。

## 为什么做这个项目

- **`execute_python` 优先。** 一个一等公民工具，可在编辑器中运行任意 Python——
  那 96 个专用工具未覆盖的一切，你依然可以做到。
- **内置 API 发现。** `search_api` / `describe_class` / `inspect_object`
  会读取内嵌 `unreal` 模块自身的文档，因此助手使用的是真实的
  API，而不是凭空臆造。
- **纯 Python，无需编译。** 没有 C++ 模块、没有编译步骤，可在 UE
  5.3–5.8 间通用。
- **天生安全。** 开箱即带游戏线程编排、回环地址绑定、auth
  token 以及 DNS 重绑定防护。
- **一键客户端配置 + 项目技能。** 从编辑器菜单配置 Claude Code / Cursor /
  VS Code / Codex 并生成一个 `AGENTS.md` 桥接。
- **同一家族、同一套约定**，与 Funplay MCP for Unity / Godot / Cocos 一致。

## 亮点

- **97 个内置工具**（默认 `core` 配置暴露其中 32 个），分布在 20 个类别中。
- **MCP 资源**（`unreal://...`）覆盖项目、关卡、选择、日志和
  工具目录，外加面向常见工作流的 **prompt 模板**。
- **结构化结果**——每个工具都返回助手可以推理的 JSON；
  截图以内联图像形式返回。
- **自动端口回退** 和 **同项目实例附加**。
- **零依赖的 Node 桥接**，以 `funplay-unreal-mcp` 之名发布到 npm。

## MCP 能力

- **工具：** 97（32 core / 97 full）。
- **主执行方式：** `execute_python`——在编辑器中运行任意 Python 片段。
- **Prompts：** `level_review`、`feature_plan`、`debug_runtime`、`blueprint_actor`。
- **资源：** `unreal://project/context`、`unreal://project/info`、
  `unreal://level/current`、`unreal://actors/list`、`unreal://selection/current`、
  `unreal://tools/catalog`、`unreal://logs/recent`、`unreal://interaction/history`，
  外加模板 `unreal://actor/{ref}` 和 `unreal://asset/{path}`。

共 **97 个内置工具**（32 core / 97 full）。

## 与 Funplay MCP for Unity 对比

| | Funplay MCP for Unreal | Funplay MCP for Unity |
|---|---|---|
| 编辑器侧 | 纯 Python 插件（无需编译） | C# 包 |
| 主执行方式 | `execute_python`（内嵌 `unreal`） | `execute_code`（内存中 C#） |
| 传输 | 本地 HTTP + stdio 桥接 | 本地 HTTP + stdio 桥接 |
| 默认暴露 | `core` 配置（97 个中的 32 个） | `core` 配置 |
| 引擎版本 | UE 5.3–5.8 | Unity 2022.3+ |
| 客户端配置 | 一键（Claude/Cursor/VS Code/Codex） | 一键 |

## 内置工具

**97 个内置工具**（32 个 `core`）。调用 `get_tool_catalog` 获取实时列表。

| 类别 | 工具 |
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

## 仓库结构

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

## 架构

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

## 参与贡献

参见 [CONTRIBUTING.md](./CONTRIBUTING.md)。在提交 PR 之前请运行 `python3 scripts/validate_repo.py`。

## 许可

MIT——参见 [LICENSE](./LICENSE)。
