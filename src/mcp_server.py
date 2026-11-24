import sys
import json
import os
from typing import Dict, Any, List, Optional
from src.parser import Parser
from src.runner import Runner, SynapRuntimeError, OutOfFuelError
from src.ail_ast import Module, Function, Type

def type_to_json_schema(t: str) -> dict:
    if t == Type.I32:
        return {"type": "integer", "description": "32-bit signed integer"}
    elif t == Type.F64:
        return {"type": "number", "description": "64-bit float"}
    elif t == Type.BOOL:
        return {"type": "boolean", "description": "Boolean value"}
    elif t == Type.STRING:
        return {"type": "string", "description": "UTF-8 string"}
    elif t == Type.ARR_I32:
        return {"type": "array", "items": {"type": "integer"}, "description": "Array of i32 integers"}
    return {"type": "string", "description": f"Custom type: {t}"}

class SynapMCPServer:
    def __init__(self, source_code: str, fuel: int = 1_000_000):
        self.source_code = source_code
        self.fuel = fuel
        self.parser = Parser()
        self.runner = Runner(default_fuel=fuel)
        self.module = self.parser.parse(source_code)
        self.tools = self._extract_tools()

    def _extract_tools(self) -> List[dict]:
        tools = []
        for fn in self.module.functions:
            properties = {}
            required = []
            for p in fn.params:
                properties[p.name] = type_to_json_schema(p.type_name)
                required.append(p.name)

            tool = {
                "name": fn.name,
                "description": f"SynapLang compiled Wasm tool '{fn.name}' returning '{fn.return_type}'",
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
            tools.append(tool)
        return tools

    def handle_message(self, message_str: str) -> Optional[dict]:
        message_str = message_str.strip()
        if not message_str:
            return None

        try:
            req = json.loads(message_str)
        except json.JSONDecodeError as e:
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"}
            }

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        # Handle MCP Methods
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "synap-mcp-server",
                        "version": "0.4.0"
                    }
                }
            }

        elif method == "notifications/initialized":
            # Notifications require no response
            return None

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": self.tools
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args_dict = params.get("arguments", {})

            # Locate function signature
            target_fn = None
            for fn in self.module.functions:
                if fn.name == tool_name:
                    target_fn = fn
                    break

            if not target_fn:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Tool '{tool_name}' not found."}],
                        "isError": True
                    }
                }

            # Map arguments in parameter order
            call_args = []
            for p in target_fn.params:
                if p.name in args_dict:
                    val = args_dict[p.name]
                    if p.type_name == Type.I32:
                        val = int(val)
                    elif p.type_name == Type.F64:
                        val = float(val)
                    elif p.type_name == Type.BOOL:
                        val = bool(val)
                    call_args.append(val)
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Missing required parameter '{p.name}' for tool '{tool_name}'"}],
                            "isError": True
                        }
                    }

            try:
                res = self.runner.execute_function(self.source_code, tool_name, *call_args, fuel=self.fuel, capture_stdout=True)
                output_text = str(res)
                if self.runner.captured_output:
                    stdout_str = "".join(self.runner.captured_output)
                    output_text = f"{stdout_str}\n=> {output_text}".strip()

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": output_text}],
                        "isError": False
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Execution error in '{tool_name}': {e}"}],
                        "isError": True
                    }
                }

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found."}
            }

def serve_stdio(source_file_path: str, fuel: int = 1_000_000):
    with open(source_file_path, "r", encoding="utf-8") as f:
        source = f.read()

    server = SynapMCPServer(source, fuel=fuel)
    sys.stderr.write(f"[Synap MCP Server] Serving {len(server.tools)} tools from '{source_file_path}' (Fuel: {fuel})\n")
    sys.stderr.flush()

    for line in sys.stdin:
        resp = server.handle_message(line)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
