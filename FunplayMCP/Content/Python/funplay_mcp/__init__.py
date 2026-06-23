"""Funplay MCP for Unreal -- in-editor MCP server.

start() is called from init_unreal.py at editor startup. It builds the settings,
tool registry, providers, and HTTP server, installs the game-thread pump, and
registers the editor menu. Idempotent: safe to call again after a hot reload."""

import unreal

from . import constants, gamethread, ui
from .context import ToolContext
from .prompt_provider import PromptProvider
from .request_handler import RequestHandler
from .resource_provider import ResourceProvider
from .server import Server
from .settings import Settings
from .tool_registry import ToolRegistry
from . import tools as _tools

__version__ = constants.SERVER_VERSION

_state = None


class _Plugin:
    def __init__(self):
        self.settings = Settings()
        self.ctx = ToolContext(self.settings)
        self.registry = ToolRegistry(self.ctx)
        self.ctx.registry = self.registry
        _tools.register_all(self.registry)

        self.resources = ResourceProvider(self.ctx, self.registry)
        self.prompts = PromptProvider(self.ctx, self.registry)
        self.server = Server(self.settings, self.registry, None)
        self.request_handler = RequestHandler(
            self.settings,
            self.registry,
            self.resources,
            self.prompts,
            constants.SERVER_NAME,
            constants.SERVER_VERSION,
            self.settings.project_name,
            self.settings.project_identity,
            log_interaction=self.server.add_interaction,
        )
        self.server.request_handler = self.request_handler
        self.resources.server = self.server


def start():
    global _state
    if _state is not None:
        return _state
    gamethread.install_pump()
    _state = _Plugin()
    if _state.settings.server_enabled:
        result = _state.server.start()
        if result.get("ok"):
            unreal.log(
                "[FunplayMCP] ready at %s (profile=%s, %d tools registered)"
                % (
                    _state.server.endpoint(),
                    _state.settings.tool_profile,
                    len(_state.registry.names()),
                )
            )
            if _state.settings.auth_token:
                unreal.log("[FunplayMCP] auth token: %s" % _state.settings.auth_token)
        else:
            unreal.log_warning(
                "[FunplayMCP] server failed to start: %s" % result.get("error")
            )
    else:
        unreal.log("[FunplayMCP] server disabled in settings; not started.")
    try:
        ui.register_menus()
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning("[FunplayMCP] menu registration failed: %s" % exc)
    return _state


def stop():
    global _state
    if _state is not None:
        try:
            _state.server.stop()
        except Exception:  # noqa: BLE001
            pass
    try:
        ui.unregister_menus()
    except Exception:  # noqa: BLE001
        pass
    gamethread.remove_pump()
    _state = None


def get_state():
    return _state


# -- editor menu actions (invoked from ui.py menu entries) -----------------
def menu_start_server():
    state = _state or start()
    result = state.server.start()
    unreal.log("[FunplayMCP] start: %s" % result)


def menu_stop_server():
    if _state:
        _state.server.stop()
        unreal.log("[FunplayMCP] server stopped.")


def menu_log_connection():
    if not _state:
        unreal.log_warning("[FunplayMCP] not started.")
        return
    unreal.log("[FunplayMCP] endpoint: %s" % _state.server.endpoint())
    unreal.log("[FunplayMCP] auth token: %s" % _state.settings.auth_token)
    unreal.log(
        "[FunplayMCP] %s env: %s=%s  %s=%s"
        % (
            constants.WRAPPER_PACKAGE_NAME,
            constants.ENV_URL,
            _state.server.endpoint(),
            constants.ENV_TOKEN,
            _state.settings.auth_token,
        )
    )


def menu_configure(client):
    if not _state:
        unreal.log_warning("[FunplayMCP] not started.")
        return
    from .client_config import ClientConfigWriter

    writer = ClientConfigWriter()
    result = writer.configure(
        client, _state.server.endpoint(), _state.settings.auth_token
    )
    unreal.log("[FunplayMCP] configure %s: %s" % (client, result))


def menu_generate_skills():
    if not _state:
        unreal.log_warning("[FunplayMCP] not started.")
        return
    from .skill_manager import SkillManager

    result = SkillManager(_state).generate()
    unreal.log("[FunplayMCP] skills: %s" % result)


def menu_check_updates():
    from .update_checker import check_for_updates

    result = check_for_updates()
    unreal.log("[FunplayMCP] update check: %s" % result)
