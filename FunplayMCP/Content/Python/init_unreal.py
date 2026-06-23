# Funplay MCP for Unreal -- editor auto-run entry point.
#
# The PythonScriptPlugin automatically adds every enabled plugin's
# Content/Python directory to sys.path and executes the init_unreal.py it
# finds there once the embedded interpreter is initialized (verified in
# PythonScriptPlugin.cpp::RunStartupScripts). So merely shipping this file
# inside an enabled plugin is enough to boot the MCP server on editor start.
import os
import sys

import unreal

_PLUGIN_PYTHON_DIR = os.path.dirname(os.path.abspath(__file__))
if _PLUGIN_PYTHON_DIR not in sys.path:
    sys.path.append(_PLUGIN_PYTHON_DIR)

try:
    import funplay_mcp

    funplay_mcp.start()
except Exception as exc:  # never let a bootstrap error break the editor
    unreal.log_error("[FunplayMCP] failed to start: %s" % exc)
    import traceback

    unreal.log_error(traceback.format_exc())
