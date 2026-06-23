"""Persistent settings + per-project auth token.

Stored as JSON under ``<Project>/Saved/FunplayMCP/funplay_mcp_settings.json``.
Mirrors the Funplay-family settings schema (server_enabled, server_port,
auth_token, tool_profile, debug/safety toggles, disabled_tools)."""

import hashlib
import json
import os
import secrets

import unreal

from . import constants

_VALID_PROFILES = ("core", "full")


def _full_path(relative_or_abs):
    return os.path.abspath(unreal.Paths.convert_relative_path_to_full(relative_or_abs))


class Settings:
    def __init__(self):
        self.dir = os.path.join(
            _full_path(unreal.Paths.project_saved_dir()), constants.SETTINGS_SUBDIR
        )
        self.path = os.path.join(self.dir, constants.SETTINGS_FILENAME)

        self.project_dir = _full_path(unreal.Paths.project_dir())
        project_file = unreal.Paths.get_project_file_path()
        self.project_name = unreal.Paths.get_base_filename(project_file) or "Unreal"
        self.project_identity = hashlib.sha256(
            self.project_dir.encode("utf-8")
        ).hexdigest()[:16]

        self.data = {
            "server_enabled": True,
            "server_port": constants.DEFAULT_PORT,
            "auth_token": "",
            "tool_profile": "core",
            "debug_logging_enabled": False,
            "execute_python_safety_checks_enabled": True,
            "disabled_tools": [],
        }
        self.load()
        if not self.data.get("auth_token"):
            self.data["auth_token"] = self._generate_token()
            self.save()

    # -- persistence -------------------------------------------------------
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                stored = json.load(fh)
            if isinstance(stored, dict):
                for key in self.data:
                    if key in stored:
                        self.data[key] = stored[key]
        except FileNotFoundError:
            pass
        except (ValueError, OSError) as exc:
            unreal.log_warning("[FunplayMCP] could not read settings: %s" % exc)
        self.data["disabled_tools"] = sorted(
            set(str(t) for t in self.data.get("disabled_tools", []))
        )
        if self.data.get("tool_profile") not in _VALID_PROFILES:
            self.data["tool_profile"] = "core"

    def save(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2, sort_keys=True)
                fh.write("\n")
        except OSError as exc:
            unreal.log_warning("[FunplayMCP] could not write settings: %s" % exc)

    def _generate_token(self):
        seed = "%s:%s" % (self.project_dir, secrets.token_hex(32))
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    # -- typed accessors ---------------------------------------------------
    @property
    def server_enabled(self):
        return bool(self.data.get("server_enabled", True))

    @property
    def server_port(self):
        try:
            return max(1, int(self.data.get("server_port", constants.DEFAULT_PORT)))
        except (TypeError, ValueError):
            return constants.DEFAULT_PORT

    @property
    def auth_token(self):
        return str(self.data.get("auth_token", ""))

    @property
    def tool_profile(self):
        profile = self.data.get("tool_profile", "core")
        return profile if profile in _VALID_PROFILES else "core"

    @property
    def debug_logging_enabled(self):
        return bool(self.data.get("debug_logging_enabled", False))

    @property
    def execute_python_safety_checks_enabled(self):
        return bool(self.data.get("execute_python_safety_checks_enabled", True))

    @property
    def disabled_tools(self):
        return list(self.data.get("disabled_tools", []))

    def is_tool_disabled(self, name):
        return name in self.data.get("disabled_tools", [])

    # -- mutators (persist + return whether something changed) -------------
    def _update(self, key, value):
        if self.data.get(key) == value:
            return False
        self.data[key] = value
        self.save()
        return True

    def set_server_enabled(self, value):
        return self._update("server_enabled", bool(value))

    def set_server_port(self, value):
        try:
            value = max(1, int(value))
        except (TypeError, ValueError):
            return False
        return self._update("server_port", value)

    def set_tool_profile(self, value):
        if value not in _VALID_PROFILES:
            value = "core"
        return self._update("tool_profile", value)

    def set_debug_logging_enabled(self, value):
        return self._update("debug_logging_enabled", bool(value))

    def set_execute_python_safety_checks_enabled(self, value):
        return self._update("execute_python_safety_checks_enabled", bool(value))

    def rotate_auth_token(self):
        self.data["auth_token"] = self._generate_token()
        self.save()
        return self.data["auth_token"]

    def set_tool_disabled(self, name, disabled):
        current = set(self.data.get("disabled_tools", []))
        if disabled:
            current.add(name)
        else:
            current.discard(name)
        return self._update("disabled_tools", sorted(current))
