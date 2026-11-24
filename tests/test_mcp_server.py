import json
import pytest
from src.mcp_server import SynapMCPServer

SAMPLE_CODE = """
(module
  (fn add (a: i32 b: i32) -> i32
    (+ a b)
  )

  (fn infinite_loop () -> i32
    (while true
      (+ 1 1)
    )
    0
  )
)
"""

@pytest.fixture
def mcp_server():
    return SynapMCPServer(SAMPLE_CODE, fuel=10000)

def test_mcp_initialize(mcp_server):
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    resp = mcp_server.handle_message(json.dumps(req))
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "synap-mcp-server"
    assert "tools" in resp["result"]["capabilities"]

def test_mcp_tools_list(mcp_server):
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    resp = mcp_server.handle_message(json.dumps(req))
    assert resp["id"] == 2
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "add" in tool_names
    assert "infinite_loop" in tool_names

    # Check input schema for 'add'
    add_tool = next(t for t in tools if t["name"] == "add")
    assert "a" in add_tool["inputSchema"]["properties"]
    assert "b" in add_tool["inputSchema"]["properties"]
    assert add_tool["inputSchema"]["properties"]["a"]["type"] == "integer"

def test_mcp_tool_call_success(mcp_server):
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "add",
            "arguments": {"a": 25, "b": 17}
        }
    }
    resp = mcp_server.handle_message(json.dumps(req))
    assert resp["id"] == 3
    assert resp["result"]["isError"] is False
    assert resp["result"]["content"][0]["text"] == "42"

def test_mcp_tool_call_fuel_protection(mcp_server):
    """Verify that an infinite loop called via MCP is safely halted with isError=True."""
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "infinite_loop",
            "arguments": {}
        }
    }
    resp = mcp_server.handle_message(json.dumps(req))
    assert resp["id"] == 4
    assert resp["result"]["isError"] is True
    assert "fuel limit" in resp["result"]["content"][0]["text"]
