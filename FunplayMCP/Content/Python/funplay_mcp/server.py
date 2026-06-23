"""Server lifecycle: port resolution, attach-to-existing, request entry point."""

import collections
import json
import socket
import threading
import time
import urllib.request

from . import constants, http_transport


class Server:
    def __init__(self, settings, registry, request_handler):
        self.settings = settings
        self.registry = registry
        self.request_handler = request_handler
        self._httpd = None
        self._thread = None
        self.port = None
        self.is_running = False
        self.attached = False
        self._interactions = collections.deque(maxlen=50)

    # -- HTTP surface used by the transport --------------------------------
    def handle(self, message):
        return self.request_handler.handle_request(message)

    def health(self, authenticated):
        info = {
            "name": constants.SERVER_NAME,
            "version": constants.SERVER_VERSION,
            "endpoint": self.endpoint(),
            "tool_profile": self.settings.tool_profile,
            "debug_logging_enabled": self.settings.debug_logging_enabled,
            "execute_python_safety_checks_enabled": (
                self.settings.execute_python_safety_checks_enabled
            ),
            "auth_required": bool(self.settings.auth_token),
            "protocol_version": constants.DEFAULT_PROTOCOL_VERSION,
            "attached_to_existing": self.attached,
        }
        if authenticated:
            info["project_name"] = self.settings.project_name
            info["project_identity"] = self.settings.project_identity
        return info

    def endpoint(self):
        port = self.port or self.settings.server_port
        return "http://%s:%d/" % (constants.DEFAULT_HOST, port)

    # -- interaction log ---------------------------------------------------
    def add_interaction(self, name, status):
        self._interactions.appendleft(
            {"tool": name, "status": status, "time": time.strftime("%H:%M:%S")}
        )

    def interaction_log(self):
        return list(self._interactions)

    # -- lifecycle ---------------------------------------------------------
    def start(self):
        if self.is_running:
            return {"ok": True, "already_running": True, "endpoint": self.endpoint()}

        configured = self.settings.server_port or constants.DEFAULT_PORT
        if not self._port_free(configured) and self._probe_and_attach(configured):
            return {"ok": True, "attached": True, "endpoint": self.endpoint()}

        port = self._resolve_port(configured)
        if port is None:
            return {"ok": False, "error": "no free loopback port available"}

        try:
            httpd = http_transport.ThreadingHTTPServer(
                (constants.DEFAULT_HOST, port), http_transport.Handler
            )
        except OSError as exc:
            return {"ok": False, "error": "could not bind port %d: %s" % (port, exc)}
        httpd.daemon_threads = True
        httpd.funplay = self
        self._httpd = httpd
        self.port = port
        self.attached = False
        self._thread = threading.Thread(
            target=httpd.serve_forever, name="FunplayMCP-HTTP", daemon=True
        )
        self._thread.start()
        self.is_running = True
        if port != self.settings.server_port:
            self.settings.set_server_port(port)
        return {"ok": True, "port": port, "endpoint": self.endpoint()}

    def stop(self):
        if self._httpd is not None:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:  # noqa: BLE001
                pass
        self._httpd = None
        self._thread = None
        self.is_running = False
        self.attached = False

    def restart(self):
        was_attached = self.attached
        self.stop()
        if was_attached:
            self.is_running = False
        return self.start()

    # -- port helpers ------------------------------------------------------
    @staticmethod
    def _port_free(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((constants.DEFAULT_HOST, port))
            return True
        except OSError:
            return False
        finally:
            sock.close()

    def _resolve_port(self, configured):
        if self._port_free(configured):
            return configured
        start = constants.DEFAULT_PORT + 1
        for port in range(start, start + constants.PORT_SCAN_RANGE - 1):
            if self._port_free(port):
                return port
        return None

    def _probe_and_attach(self, port):
        try:
            url = "http://%s:%d/health" % (constants.DEFAULT_HOST, port)
            req = urllib.request.Request(url)
            if self.settings.auth_token:
                req.add_header(constants.AUTH_HEADER, self.settings.auth_token)
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            return False
        if (
            data.get("name") == constants.SERVER_NAME
            and data.get("project_identity") == self.settings.project_identity
        ):
            self.port = port
            self.is_running = True
            self.attached = True
            return True
        return False
