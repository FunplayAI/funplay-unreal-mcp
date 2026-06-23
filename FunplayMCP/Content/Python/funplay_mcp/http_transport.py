"""Loopback HTTP/1.1 transport for the in-editor MCP server.

Runs on a daemon thread (ThreadingHTTPServer) so the editor never blocks. The
request handler NEVER touches ``unreal.*`` directly -- it calls Server.handle(),
which dispatches tool work onto the game thread via the registry."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: F401
from urllib.parse import urlparse

from . import constants

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
MAX_BODY_BYTES = 8 * 1024 * 1024


def _extract_host(value):
    value = (value or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = "//" + value
    return (urlparse(value).hostname or "").lower()


def _jsonrpc_error(code, message):
    return {"jsonrpc": "2.0", "id": None, "error": {"code": code, "message": message}}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "FunplayMCP/" + constants.SERVER_VERSION

    @property
    def funplay(self):
        return self.server.funplay

    def log_message(self, *_args):  # silence the default stderr access log
        return

    # -- response helper ---------------------------------------------------
    def _write(self, status, payload, content_type="application/json"):
        if payload is None:
            body = b""
        elif isinstance(payload, (dict, list)):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        else:
            body = str(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if body:
            self.wfile.write(body)

    # -- security ----------------------------------------------------------
    def _origin_ok(self):
        for key in ("host", "origin", "referer"):
            host = _extract_host(self.headers.get(key))
            if host and host not in LOOPBACK_HOSTS:
                return False
        return True

    def _authenticated(self):
        token = self.funplay.settings.auth_token
        if not token:
            return True
        provided = self.headers.get(constants.AUTH_HEADER)
        if not provided:
            auth = self.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                provided = auth[7:].strip()
        return provided == token

    # -- routes ------------------------------------------------------------
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/health"):
            self._write(200, self.funplay.health(self._authenticated()))
        elif path == "/tools":
            if not self._authenticated():
                self._write(401, {"error": "unauthorized"})
                return
            self._write(200, {"tools": self.funplay.registry.list_tools()})
        else:
            self._write(404, {"error": "Not found"})

    def do_POST(self):
        if not self._origin_ok():
            self._write(403, _jsonrpc_error(-32001, "Forbidden non-loopback origin"))
            return
        if not self._authenticated():
            self._write(
                401,
                _jsonrpc_error(-32001, "Missing or invalid Funplay MCP auth token."),
            )
            return

        proto = self.headers.get("mcp-protocol-version")
        if proto and proto not in constants.SUPPORTED_PROTOCOL_VERSIONS:
            self._write(
                400, _jsonrpc_error(-32600, "Unsupported MCP-Protocol-Version: %s" % proto)
            )
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._write(400, _jsonrpc_error(-32600, "Invalid Content-Length"))
            return
        if length > MAX_BODY_BYTES:
            self._write(413, _jsonrpc_error(-32600, "Request body too large"))
            return
        raw = self.rfile.read(length) if length else b""

        try:
            message = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            self._write(400, _jsonrpc_error(-32700, "Parse error"))
            return
        if not isinstance(message, (dict, list)):
            self._write(400, _jsonrpc_error(-32700, "Parse error"))
            return

        if isinstance(message, list):
            responses = [
                r for r in (self.funplay.handle(m) for m in message) if r is not None
            ]
            self._write(200 if responses else 204, responses if responses else None)
            return

        response = self.funplay.handle(message)
        self._write(204 if response is None else 200, response)
