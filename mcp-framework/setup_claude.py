#!/usr/bin/env python3
"""
Setup Claude — Registers an MCP server in Claude Desktop's config.

Usage:
    python3 setup_claude.py my_server                     # auto-name from module
    python3 setup_claude.py my_server --name my-server    # custom name
    python3 setup_claude.py /path/to/server.py            # absolute path
    python3 setup_claude.py --list                        # show registered servers
    python3 setup_claude.py --remove my-server            # unregister a server

What it does:
    1. Validates the module has TOOLS + TOOL_HANDLERS
    2. Adds an entry to Claude Desktop's claude_desktop_config.json
    3. Tells you to restart Claude Desktop
"""
import argparse
import importlib
import importlib.util
import json
import os
import sys
from pathlib import Path

# Claude Desktop config location (macOS)
CLAUDE_CONFIG_PATH = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
RUNNER_PATH = Path(__file__).parent / "mcp_runner.py"

def load_claude_config() -> dict:
    """Load the existing Claude Desktop config, or create a minimal one."""
    if CLAUDE_CONFIG_PATH.exists():
        with open(CLAUDE_CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

def save_claude_config(config: dict):
    """Write the config back to disk."""
    CLAUDE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CLAUDE_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def resolve_module_arg(module_ref: str) -> str:
    """Resolve a module reference to a form the runner can load."""
    # If it's an absolute path, return as-is
    if os.path.isabs(module_ref) and os.path.isfile(module_ref):
        return os.path.abspath(module_ref)

    # If bare name, check servers/ directory
    project_root = Path(__file__).parent
    if "." not in module_ref:
        server_file = project_root / "servers" / f"{module_ref}.py"
        if server_file.is_file():
            return f"servers.{module_ref}"
        # Also check if it's a file at project root
        root_file = project_root / f"{module_ref}.py"
        if root_file.is_file():
            return module_ref

    return module_ref

def validate_module(module_ref: str) -> tuple:
    """Import and validate the module exports TOOLS + TOOL_HANDLERS. Returns (tools, name)."""
    project_root = str(Path(__file__).parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    resolved = module_ref
    # Handle absolute path
    if os.path.isfile(module_ref):
        spec = importlib.util.spec_from_file_location("_validate", module_ref)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    else:
        # If bare name, try servers/ prefix
        if "." not in module_ref:
            servers_path = os.path.join(project_root, "servers", f"{module_ref}.py")
            if os.path.isfile(servers_path):
                resolved = f"servers.{module_ref}"
        mod = importlib.import_module(resolved)

    tools = getattr(mod, "TOOLS", None)
    handlers = getattr(mod, "TOOL_HANDLERS", None)
    server_name = getattr(mod, "SERVER_NAME", None)

    if tools is None or handlers is None:
        print(f"❌ Module '{module_ref}' is missing TOOLS or TOOL_HANDLERS.")
        print("   Copy mcp_template.py and follow the pattern.")
        sys.exit(1)

    return tools, server_name

def register_server(module_ref: str, name: str = None):
    """Register an MCP server in Claude Desktop config."""
    resolved = resolve_module_arg(module_ref)
    tools, module_name = validate_module(module_ref)

    # Derive server name
    if not name:
        name = module_name or module_ref.replace(".", "-").replace("_", "-").replace("/", "-")
        # Clean up path-based names
        if name.endswith("-py"):
            name = name[:-3]

    tool_names = [t["name"] for t in tools]

    config = load_claude_config()
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    runner_abs = str(RUNNER_PATH.resolve())

    config["mcpServers"][name] = {
        "command": sys.executable,  # Uses the same Python that ran this script
        "args": [runner_abs, resolved],
    }

    save_claude_config(config)

    print(f"✅ Registered '{name}' in Claude Desktop config.")
    print(f"   Runner:  {runner_abs}")
    print(f"   Module:  {resolved}")
    print(f"   Tools:   {', '.join(tool_names)}")
    print()
    print("👉 Restart Claude Desktop to pick up the changes.")
    print(f"   Config:  {CLAUDE_CONFIG_PATH}")

def list_servers():
    """List all currently registered MCP servers."""
    config = load_claude_config()
    servers = config.get("mcpServers", {})

    if not servers:
        print("No MCP servers registered in Claude Desktop.")
        return

    print(f"📋 Registered MCP Servers ({len(servers)}):\n")
    for name, entry in servers.items():
        cmd = entry.get("command", "?")
        args = " ".join(entry.get("args", []))
        print(f"   {name}")
        print(f"     → {cmd} {args}")
        print()

def remove_server(name: str):
    """Remove an MCP server from Claude Desktop config."""
    config = load_claude_config()
    servers = config.get("mcpServers", {})

    if name not in servers:
        print(f"❌ Server '{name}' not found in config.")
        print(f"   Registered: {', '.join(servers.keys()) or '(none)'}")
        return

    del servers[name]
    save_claude_config(config)
    print(f"✅ Removed '{name}' from Claude Desktop config.")
    print("👉 Restart Claude Desktop to apply changes.")

def main():
    parser = argparse.ArgumentParser(
        description="Register MCP servers with Claude Desktop.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 setup_claude.py my_server                   Register servers/my_server.py
  python3 setup_claude.py my_server --name my-tools   Register with custom name
  python3 setup_claude.py /path/to/server.py          Register by absolute path
  python3 setup_claude.py --list                      Show registered servers
  python3 setup_claude.py --remove my-server          Unregister a server
        """,
    )
    parser.add_argument("module", nargs="?", help="Server module to register (bare name, dotted path, or file path)")
    parser.add_argument("--name", "-n", help="Custom server name for Claude Desktop")
    parser.add_argument("--list", "-l", action="store_true", help="List registered servers")
    parser.add_argument("--remove", "-r", metavar="NAME", help="Remove a server by name")

    args = parser.parse_args()

    if args.list:
        list_servers()
    elif args.remove:
        remove_server(args.remove)
    elif args.module:
        register_server(args.module, args.name)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
