"""Generate a project-local skill file + AGENTS.md bridge block.

Writes <Project>/.funplay/skills/funplay-unreal-project.md and manifest.json,
and a marker-delimited block in <Project>/AGENTS.md so coding agents discover the
MCP server and its conventions."""

import json
import os
import re

from . import constants

_BEGIN = "<!-- FUNPLAY_MCP_SKILL_BEGIN -->"
_END = "<!-- FUNPLAY_MCP_SKILL_END -->"


class SkillManager:
    def __init__(self, state):
        self.state = state
        self.project_dir = state.settings.project_dir
        self.skill_dir = os.path.join(self.project_dir, ".funplay", "skills")

    def generate(self, include_agents_bridge=True):
        try:
            os.makedirs(self.skill_dir, exist_ok=True)
            skill_path = os.path.join(self.skill_dir, "funplay-unreal-project.md")
            with open(skill_path, "w", encoding="utf-8") as fh:
                fh.write(self._skill_markdown())

            manifest_path = os.path.join(self.skill_dir, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as fh:
                json.dump(self._manifest(), fh, indent=2)
                fh.write("\n")

            paths = {"skill": skill_path, "manifest": manifest_path}
            if include_agents_bridge:
                paths["agents"] = self._write_agents_bridge()
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "paths": paths}

    def _manifest(self):
        s = self.state.settings
        summary = self.state.registry.exposure_summary()
        return {
            "name": "funplay-unreal-project",
            "version": 1,
            "endpoint": self.state.server.endpoint(),
            "tool_profile": s.tool_profile,
            "tool_count": summary["total_count"],
            "core_tool_count": summary["core_count"],
            "project_name": s.project_name,
            "project_identity": s.project_identity,
        }

    def _skill_markdown(self):
        s = self.state.settings
        summary = self.state.registry.exposure_summary()
        return "\n".join(
            [
                "# Funplay MCP -- %s" % s.project_name,
                "",
                "This project has the Funplay MCP server for Unreal running in the editor.",
                "",
                "## Connection",
                "- Endpoint: `%s`" % self.state.server.endpoint(),
                "- Tool profile: `%s` (%d of %d tools exposed)"
                % (s.tool_profile, summary["exposed_count"], summary["total_count"]),
                "- Transport: AI clients launch `npx -y %s` with `%s` / `%s`."
                % (constants.WRAPPER_PACKAGE, constants.ENV_URL, constants.ENV_TOKEN),
                "",
                "## Operating rules",
                "- Prefer dedicated tools; use `execute_python` for anything else.",
                "- Inspect before mutating: `get_level_info`, `list_actors`, `get_actor_info`.",
                "- Save your work with `save_current_level` / `save_asset`.",
                "- Verify visually with `take_screenshot` (best during Play-In-Editor).",
                "",
                "## High-value resources",
                "- `unreal://project/context` -- project + level + tool overview",
                "- `unreal://tools/catalog` -- full tool list",
            ]
        )

    def _write_agents_bridge(self):
        agents_path = os.path.join(self.project_dir, "AGENTS.md")
        block = "\n".join(
            [
                _BEGIN,
                "## Funplay MCP (Unreal)",
                "An in-editor MCP server is available at `%s`."
                % self.state.server.endpoint(),
                "See `.funplay/skills/funplay-unreal-project.md` for conventions.",
                _END,
            ]
        )
        existing = ""
        if os.path.isfile(agents_path):
            with open(agents_path, "r", encoding="utf-8") as fh:
                existing = fh.read()
        if _BEGIN in existing and _END in existing:
            merged = re.sub(
                re.escape(_BEGIN) + r".*?" + re.escape(_END), block, existing, flags=re.DOTALL
            )
        elif existing.strip():
            merged = existing.rstrip() + "\n\n" + block + "\n"
        else:
            merged = block + "\n"
        with open(agents_path, "w", encoding="utf-8") as fh:
            fh.write(merged)
        return agents_path
