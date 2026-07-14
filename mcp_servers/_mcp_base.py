import json, sys

def run_server(tools, handler):
    """Standard MCP JSON-RPC 2.0 stdio loop. All servers import this."""
    while True:
        line = sys.stdin.readline().strip()
        if not line:
            break
        req = json.loads(line)
        method = req.get("method")
        if method == "initialize":
            resp = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
        elif method == "tools/list":
            resp = {"tools": tools}
        elif method == "tools/call":
            name = req["params"]["name"]
            args = req["params"]["arguments"]
            resp = handler(name, args)   # returns dict
        else:
            resp = {"error": f"Unknown method: {method}"}
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req.get("id"), "result": resp}) + "\n")
        sys.stdout.flush()
