import json
import sys


def run_server(tools, handler, server_name="gtm-mcp"):
    """Standard MCP JSON-RPC 2.0 stdio loop. All GTM servers import this."""
    while True:
        line = sys.stdin.readline().strip()
        if not line:
            break
        req = json.loads(line)
        method = req.get("method")
        req_id = req.get("id")

        if method == "notifications/initialized":
            continue

        if method == "initialize":
            resp = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": server_name, "version": "1.0.0"},
            }
        elif method == "tools/list":
            resp = {"tools": tools}
        elif method == "tools/call":
            name = req["params"]["name"]
            args = req["params"].get("arguments", {})
            try:
                result = handler(name, args)
                text = result if isinstance(result, str) else json.dumps(result)
                resp = {
                    "content": [{"type": "text", "text": text}],
                    "isError": False,
                }
            except Exception as e:
                resp = {
                    "content": [{"type": "text", "text": f"Error: {e}"}],
                    "isError": True,
                }
        else:
            if req_id is not None:
                sys.stdout.write(json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method '{method}' not found."},
                }) + "\n")
                sys.stdout.flush()
            continue

        if req_id is not None:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": resp}) + "\n")
            sys.stdout.flush()
