import os
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_ROOT = os.path.join(ROOT, "FunplayMCP", "Content", "Python")
sys.path.insert(0, PY_ROOT)

unreal = types.ModuleType("unreal")


class _Any:
    def __getattr__(self, _name):
        return _Any()

    def __call__(self, *args, **kwargs):
        return _Any()


unreal.__getattr__ = lambda _name: _Any()
sys.modules["unreal"] = unreal

from funplay_mcp.client_config import _write_toml  # noqa: E402


class ClientConfigTests(unittest.TestCase):
    def test_write_toml_replaces_existing_section_and_env_child(self):
        existing = """[profile]
model = "gpt-5"

[mcp_servers."funplay-unreal"]
command = "npx"
args = ["-y", "funplay-unreal-mcp@0.1.0"]

[mcp_servers."funplay-unreal".env]
FUNPLAY_UNREAL_MCP_URL = "http://127.0.0.1:8765/"
FUNPLAY_UNREAL_MCP_TOKEN = "old-token"

[mcp_servers."other"]
command = "other"
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.toml")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(existing)

            _write_toml(path, "http://127.0.0.1:8999/", "new-token")

            with open(path, "r", encoding="utf-8") as handle:
                updated = handle.read()

        self.assertIn('[mcp_servers."other"]', updated)
        self.assertIn('FUNPLAY_UNREAL_MCP_URL = "http://127.0.0.1:8999/"', updated)
        self.assertIn('FUNPLAY_UNREAL_MCP_TOKEN = "new-token"', updated)
        self.assertNotIn("old-token", updated)
        self.assertEqual(updated.count('[mcp_servers."funplay-unreal".env]'), 1)


if __name__ == "__main__":
    unittest.main()
