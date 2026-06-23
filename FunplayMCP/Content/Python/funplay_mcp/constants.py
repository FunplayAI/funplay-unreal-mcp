"""Shared constants for the Funplay MCP Unreal plugin.

Keep these in sync with stdio-wrapper/package.json, server.json, FunplayMCP.uplugin
and the README tool counts (scripts/validate_repo.py enforces version sync)."""

SERVER_NAME = "Funplay MCP Server - Unreal"
SERVER_VERSION = "0.2.0"

# Networking -- loopback only, default port shared across the Funplay family.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PORT_SCAN_RANGE = 100  # scan DEFAULT_PORT+1 .. DEFAULT_PORT+99 when the port is busy

# MCP protocol negotiation (newest first; index 0 is the default).
SUPPORTED_PROTOCOL_VERSIONS = [
    "2025-11-25",
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
]
DEFAULT_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]

# Tool-result -> MCP content conventions.
IMAGE_DATA_URI_PREFIX = "data:image/png;base64,"
ERROR_PREFIX = "Error:"

# npm stdio bridge that AI clients launch to reach this HTTP server.
WRAPPER_PACKAGE_NAME = "funplay-unreal-mcp"
WRAPPER_PACKAGE = WRAPPER_PACKAGE_NAME + "@" + SERVER_VERSION
SERVER_JSON_NAME = "io.github.FunplayAI/funplay-unreal-mcp"
GITHUB_REPO = "FunplayAI/funplay-unreal-mcp"

# Environment variables understood by the stdio bridge.
ENV_URL = "FUNPLAY_UNREAL_MCP_URL"
ENV_TOKEN = "FUNPLAY_UNREAL_MCP_TOKEN"
ENV_URL_COMPAT = "UNREAL_MCP_URL"
ENV_TOKEN_COMPAT = "UNREAL_MCP_TOKEN"

# Auth header accepted on POST requests (also Authorization: Bearer <token>).
AUTH_HEADER = "x-funplay-mcp-token"

# Project-local skill / settings locations.
SETTINGS_SUBDIR = "FunplayMCP"
SETTINGS_FILENAME = "funplay_mcp_settings.json"
