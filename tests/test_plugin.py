"""Editor-side tests that run without Unreal by stubbing the `unreal` module.

Covers the tool registry assembly and the JSON-RPC / MCP request handler
envelopes. Only the game_thread=False core tool (get_tool_catalog) is exercised
through tools/call, since other tools require the editor's game-thread pump."""

import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_ROOT = os.path.join(ROOT, "FunplayMCP", "Content", "Python")


def _install_unreal_stub():
    unreal = types.ModuleType("unreal")

    class _Any:
        def __getattr__(self, _n):
            return _Any()

        def __call__(self, *a, **k):
            return _Any()

    unreal.__getattr__ = lambda _name: _Any()
    sys.modules["unreal"] = unreal


_install_unreal_stub()
sys.path.insert(0, PY_ROOT)

from funplay_mcp.context import ToolContext  # noqa: E402
from funplay_mcp.request_handler import RequestHandler  # noqa: E402
from funplay_mcp.tool_registry import ToolRegistry  # noqa: E402
from funplay_mcp import tools as tools_pkg  # noqa: E402


class _Settings:
    tool_profile = "full"
    debug_logging_enabled = False
    execute_python_safety_checks_enabled = True
    project_name = "TestProject"
    project_identity = "deadbeefdeadbeef"

    def is_tool_disabled(self, _name):
        return False


class _StubProvider:
    def list_resources(self):
        return []

    def list_resource_templates(self):
        return []

    def list_prompts(self):
        return []


def _build():
    settings = _Settings()
    ctx = ToolContext(settings)
    registry = ToolRegistry(ctx)
    ctx.registry = registry
    tools_pkg.register_all(registry)
    handler = RequestHandler(
        settings, registry, _StubProvider(), _StubProvider(),
        "Funplay MCP Server - Unreal", "0.1.0", "TestProject", "deadbeefdeadbeef",
    )
    return registry, handler


def _req(method, params=None, rid=1):
    return {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.registry, self.handler = _build()

    def test_registry_has_62_tools_25_core(self):
        names = self.registry.names()
        self.assertEqual(len(names), 62)
        self.assertEqual(len(set(names)), 62)
        core = [n for n in names if "core" in self.registry.get(n)["profiles"]]
        self.assertEqual(len(core), 25)

    def test_initialize(self):
        resp = self.handler.handle_request(_req("initialize"))
        self.assertEqual(resp["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(resp["result"]["serverInfo"]["name"], "Funplay MCP Server - Unreal")

    def test_tools_list_full_profile(self):
        resp = self.handler.handle_request(_req("tools/list"))
        self.assertEqual(len(resp["result"]["tools"]), 62)

    def test_tools_call_get_tool_catalog(self):
        resp = self.handler.handle_request(
            _req("tools/call", {"name": "get_tool_catalog", "arguments": {}})
        )
        self.assertFalse(resp["result"]["isError"])
        self.assertIn("tools", resp["result"]["structuredContent"])

    def test_ping(self):
        self.assertEqual(self.handler.handle_request(_req("ping"))["result"], {})

    def test_unknown_method(self):
        resp = self.handler.handle_request(_req("does/not/exist"))
        self.assertEqual(resp["error"]["code"], -32601)

    def test_tools_call_unknown_tool(self):
        resp = self.handler.handle_request(_req("tools/call", {"name": "nope"}))
        self.assertEqual(resp["error"]["code"], -32602)

    def test_notification_returns_none(self):
        self.assertIsNone(self.handler.handle_request(_req("notifications/initialized", rid=None)))

    def test_invalid_jsonrpc(self):
        resp = self.handler.handle_request({"method": "x"})
        self.assertEqual(resp["error"]["code"], -32600)


if __name__ == "__main__":
    unittest.main()
