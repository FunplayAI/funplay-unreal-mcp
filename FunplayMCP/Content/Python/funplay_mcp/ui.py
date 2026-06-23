"""Editor menu: a 'Funplay MCP' submenu under the main Tools menu.

Each entry runs a small Python command that calls into the funplay_mcp module.
Results are written to the Output Log (menus can't easily display return values)."""

import unreal

_SUBMENU = "LevelEditor.MainMenu.FunplayMCP"
_ENTRIES = [
    ("StartServer", "Start MCP Server", "menu_start_server()"),
    ("StopServer", "Stop MCP Server", "menu_stop_server()"),
    ("LogConnection", "Log Endpoint + Token", "menu_log_connection()"),
    ("ConfigClaude", "Configure Claude Code", "menu_configure('claude')"),
    ("ConfigCursor", "Configure Cursor", "menu_configure('cursor')"),
    ("ConfigVSCode", "Configure VS Code", "menu_configure('vscode')"),
    ("ConfigCodex", "Configure Codex", "menu_configure('codex')"),
    ("GenSkills", "Generate Project Skills", "menu_generate_skills()"),
    ("CheckUpdates", "Check for Updates", "menu_check_updates()"),
]


def register_menus():
    menus = unreal.ToolMenus.get()
    main = menus.find_menu("LevelEditor.MainMenu")
    if main is None:
        return
    submenu = main.add_sub_menu(
        "LevelEditor.MainMenu", "", "FunplayMCP", "Funplay MCP"
    )
    if submenu is None:
        submenu = menus.find_menu(_SUBMENU)
    if submenu is None:
        return
    for name, label, call in _ENTRIES:
        entry = unreal.ToolMenuEntry(
            name=name, type=unreal.MultiBlockType.MENU_ENTRY
        )
        entry.set_label(label)
        entry.set_string_command(
            unreal.ToolMenuStringCommandType.PYTHON,
            "",
            "import funplay_mcp; funplay_mcp.%s" % call,
        )
        submenu.add_menu_entry("Funplay", entry)
    menus.refresh_all_widgets()


def unregister_menus():
    try:
        menus = unreal.ToolMenus.get()
        menus.remove_menu(_SUBMENU)
        menus.refresh_all_widgets()
    except Exception:  # noqa: BLE001
        pass
