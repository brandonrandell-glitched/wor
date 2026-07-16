#!/usr/bin/env python3
"""
MCP Runner — Universal JSON-RPC 2.0 stdio transport for Claude Desktop.

Takes any Python module that exports TOOLS (list) and TOOL_HANDLERS (dict),
and wraps it into a fully compliant MCP server over stdin/stdout.

Usage:
    python3 mcp_runner.py my_server            # loads my_server.py from servers/
    python3 mcp_runner.py servers.my_server     # dotted path also works
    python3 mcp_runner.py /absolute/path.py     # or an absolute file path

Claude Desktop config (claude_desktop_config.json):
    {
      "mcpServers": {
        "my-server": {
          "command": "python3",
          "args": ["/path/to/mcp_runner.py", "my_server"]
        }
      }
    }
"""
import importlib
import importlib.util
import json
import os
import sys
import traceback
from typing import Optional


# ---------------------------------------------------------------------------
# Logging (stderr only — stdout is reserved for JSON-RPC)
# ---------------------------------------------------------------------------
def log(message: str):
    sys.stderr.write(f"[MCP Runner] {message}\n")
    sys.stderr.flush()


# ---------------------------------------------------------------------------
# Module loader
# ---------------------------------------------------------------------------
def load_server_module(module_ref: str):
    """Load a server module by dotted path, bare name, or absolute file path."""

    # 1) Absolute file path
    if os.path.isfile(module_ref):
        spec = importlib.util.spec_from_file_location("_mcp_server", module_ref)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    # 2) Try as a dotted import relative to this project
    #    Ensure the project root is on sys.path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # If bare name (no dots), check if it lives in servers/
    if "." not in module_ref:
        servers_path = os.path.join(project_root, "servers", f"{module_ref}.py")
        if os.path.isfile(servers_path):
            module_ref = f"servers.{module_ref}"

    try:
        return importlib.import_module(module_ref)
    except ModuleNotFoundError:
        log(f"ERROR: Could not find module '{module_ref}'.")
        log(f"Looked in: {project_root}")
        log("Make sure the file exists in servers/ or provide a full dotted path.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 request handler
# ---------------------------------------------------------------------------
def handle_request(tools: list, handlers: dict, server_name: str, request: dict) -> Optional[dict]:
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params", {})

    # --- initialize ---
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": server_name,
                    "version": "1.0.0",
                },
            },
            "id": req_id,
        }

    # --- notifications/initialized (client ack, no response needed) ---
    if method == "notifications/initialized":
        return None

    # --- tools/list ---
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "result": {"tools": tools},
            "id": req_id,
        }

    # --- tools/call ---
    if method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        handler = handlers.get(tool_name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Error: Tool '{tool_name}' not found."}],
                },
                "id": req_id,
            }

        try:
            result_text = handler(tool_args)
            is_error = isinstance(result_text, str) and result_text.startswith("Error:")
            return {
                "jsonrpc": "2.0",
                "result": {
                    "isError": is_error,
                    "content": [{"type": "text", "text": result_text}],
                },
                "id": req_id,
            }
        except Exception as e:
            log(f"Error executing tool '{tool_name}': {traceback.format_exc()}")
            return {
                "jsonrpc": "2.0",
                "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                },
                "id": req_id,
            }

    # --- unknown method ---
    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found.",
            },
            "id": req_id,
        }

    return None


# ---------------------------------------------------------------------------
# Main loop — reads JSON-RPC messages from stdin, writes responses to stdout
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python3 mcp_runner.py <server_module>", file=sys.stderr)
        print("", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  python3 mcp_runner.py my_server          # loads servers/my_server.py", file=sys.stderr)
        print("  python3 mcp_runner.py servers.my_server   # dotted path", file=sys.stderr)
        print("  python3 mcp_runner.py /path/to/server.py  # absolute path", file=sys.stderr)
        sys.exit(1)

    module_ref = sys.argv[1]
    mod = load_server_module(module_ref)

    # Validate the module exports what we need
    tools = getattr(mod, "TOOLS", None)
    handlers = getattr(mod, "TOOL_HANDLERS", None)

    if tools is None or handlers is None:
        log(f"ERROR: Module '{module_ref}' must export TOOLS (list) and TOOL_HANDLERS (dict).")
        log("See mcp_template.py for the expected format.")
        sys.exit(1)

    # Derive a server name from the module
    server_name = getattr(mod, "SERVER_NAME", module_ref.replace(".", "-").replace("_", "-"))
    tool_names = [t["name"] for t in tools]
    log(f"Server '{server_name}' started with {len(tools)} tool(s): {', '.join(tool_names)}")

    # stdio loop
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            request = json.loads(line)
            response = handle_request(tools, handlers, server_name, request)

            if response:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

        except json.JSONDecodeError as e:
            log(f"Invalid JSON: {e}")
        except Exception as e:
            log(f"Unexpected error: {traceback.format_exc()}")


if __name__ == "__main__":
    main()
