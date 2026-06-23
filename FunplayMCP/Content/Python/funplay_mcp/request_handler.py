"""JSON-RPC 2.0 / MCP dispatch.

Maps MCP methods to the tool registry and the resource/prompt providers, and
converts a tool's string result into MCP content / structuredContent / isError.
Envelope shapes and error codes match the Funplay family exactly."""

import json

from . import constants


class RequestHandler:
    def __init__(
        self,
        settings,
        registry,
        resource_provider,
        prompt_provider,
        server_name,
        server_version,
        project_name,
        project_identity,
        log_interaction=None,
    ):
        self.settings = settings
        self.registry = registry
        self.resources = resource_provider
        self.prompts = prompt_provider
        self.server_name = server_name
        self.server_version = server_version
        self.project_name = project_name
        self.project_identity = project_identity
        self._log_interaction = log_interaction

    # -- envelopes ---------------------------------------------------------
    @staticmethod
    def _result(request_id, result):
        return {"id": request_id, "jsonrpc": "2.0", "result": result}

    @staticmethod
    def _error(request_id, code, message):
        return {
            "id": request_id,
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
        }

    # -- top-level dispatch ------------------------------------------------
    def handle_request(self, request):
        if not isinstance(request, dict) or not request:
            return self._error(None, -32600, "Invalid Request")
        if request.get("jsonrpc") != "2.0":
            return self._error(request.get("id"), -32600, "Invalid Request")

        method = request.get("method")
        if not isinstance(method, str) or not method:
            return self._error(request.get("id"), -32600, "Invalid Request")

        params = request.get("params")
        if not isinstance(params, dict):
            params = {}
        request_id = request.get("id")

        if method.startswith("notifications/"):
            return None  # notifications get HTTP 204 / no body

        try:
            if method == "initialize":
                return self._result(request_id, self._handle_initialize(params))
            if method == "ping":
                return self._result(request_id, {})
            if method == "tools/list":
                return self._result(
                    request_id, {"tools": self.registry.list_tools()}
                )
            if method == "tools/call":
                return self._handle_tool_call(request_id, params)
            if method == "resources/list":
                return self._result(
                    request_id, {"resources": self.resources.list_resources()}
                )
            if method == "resources/templates/list":
                return self._result(
                    request_id,
                    {"resourceTemplates": self.resources.list_resource_templates()},
                )
            if method == "resources/read":
                uri = params.get("uri")
                if not uri:
                    return self._error(request_id, -32602, "Missing required param: uri")
                return self._result(request_id, self.resources.read_resource(uri))
            if method == "prompts/list":
                return self._result(
                    request_id, {"prompts": self.prompts.list_prompts()}
                )
            if method == "prompts/get":
                name = params.get("name")
                if not name:
                    return self._error(
                        request_id, -32602, "Missing required param: name"
                    )
                return self._result(
                    request_id,
                    self.prompts.get_prompt(name, params.get("arguments") or {}),
                )
        except Exception as exc:  # noqa: BLE001
            return self._error(request_id, -32603, "Internal error: %s" % exc)

        return self._error(request_id, -32601, "Method not found: %s" % method)

    # -- handlers ----------------------------------------------------------
    def _handle_initialize(self, params):
        requested = params.get("protocolVersion")
        if requested in constants.SUPPORTED_PROTOCOL_VERSIONS:
            protocol = requested
        else:
            protocol = constants.DEFAULT_PROTOCOL_VERSION
        return {
            "protocolVersion": protocol,
            "serverInfo": {
                "name": self.server_name,
                "version": self.server_version,
                "projectName": self.project_name,
                "projectIdentity": self.project_identity,
            },
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
        }

    def _handle_tool_call(self, request_id, params):
        name = params.get("name")
        if not name:
            return self._error(request_id, -32602, "Missing required param: name")
        if not self.registry.has(name):
            return self._error(request_id, -32602, "Unknown tool: %s" % name)
        if not self.registry.is_allowed(name, self.settings.tool_profile):
            return self._error(
                request_id,
                -32602,
                "Tool '%s' is not available in the '%s' profile."
                % (name, self.settings.tool_profile),
            )

        arguments = params.get("arguments")
        if not isinstance(arguments, dict):
            arguments = {}

        result_text = self.registry.call_tool(name, arguments)
        if not isinstance(result_text, str):
            result_text = "" if result_text is None else str(result_text)

        structured = self._build_structured_content(result_text)
        is_error = self._is_tool_error(result_text, structured)
        if callable(self._log_interaction):
            try:
                self._log_interaction(name, "error" if is_error else "success")
            except Exception:  # noqa: BLE001
                pass

        result = {
            "content": self._build_content(result_text),
            "isError": is_error,
        }
        if structured:
            result["structuredContent"] = structured
        return self._result(request_id, result)

    # -- tool-result conversion -------------------------------------------
    @staticmethod
    def _build_content(result_text):
        if result_text.startswith(constants.IMAGE_DATA_URI_PREFIX):
            data = result_text[len(constants.IMAGE_DATA_URI_PREFIX):]
            return [
                {"type": "image", "data": data, "mimeType": "image/png"},
                {"type": "text", "text": "Screenshot captured successfully."},
            ]
        return [{"type": "text", "text": result_text}]

    @staticmethod
    def _build_structured_content(result_text):
        if result_text.startswith(constants.IMAGE_DATA_URI_PREFIX):
            return {}
        if result_text.startswith(constants.ERROR_PREFIX):
            return {
                "success": False,
                "code": "TOOL_ERROR",
                "error": result_text[len(constants.ERROR_PREFIX):].strip(),
            }
        stripped = result_text.lstrip()
        if stripped[:1] in ("{", "["):
            try:
                parsed = json.loads(result_text)
            except ValueError:
                return {}
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {"items": parsed}
        return {}

    @staticmethod
    def _is_tool_error(result_text, structured):
        if result_text.startswith(constants.ERROR_PREFIX):
            return True
        if isinstance(structured, dict):
            if structured.get("success") is False:
                return True
            if structured.get("isError") is True:
                return True
        return False
