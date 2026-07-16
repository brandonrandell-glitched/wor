"""
MCP Server Template — Copy this file to create a new MCP server for Claude Desktop.

Quick start:
    1. Copy this file:  cp mcp_template.py servers/my_server.py
    2. Edit the TOOLS list and TOOL_HANDLERS dict below
    3. Register with Claude:  python3 setup_claude.py my_server --name my-server
    4. Restart Claude Desktop

Convention:
    - Each tool is a plain Python function that returns a JSON string
    - TOOLS: list of MCP tool definitions (name, description, inputSchema)
    - TOOL_HANDLERS: dict mapping tool name → callable(args_dict) → str
    - Optional SERVER_NAME: human-readable name for the server
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Union

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Human-readable server name (shows in Claude's MCP logs)
SERVER_NAME = "my-server"

# Where to store data (relative to this file)
DATA_PATH = Path(__file__).parent / "data" / "my_data.json"

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load() -> Union[list, dict]:
    """Load data from the JSON file."""
    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _save(data: Union[list, dict]):
    """Save data to the JSON file."""
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------
# Each tool is a plain function that:
#   - Takes typed arguments
#   - Returns a JSON string (success or error)
#   - Handles its own exceptions

def add_item(name: str, category: str = "general") -> str:
    """Add a new item to the collection."""
    data = _load()
    item = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "category": category,
        "created_at": datetime.now().isoformat(),
    }
    data.append(item)
    _save(data)
    return json.dumps({"success": True, "item": item})

def list_items(category: str = None) -> str:
    """List all items, optionally filtered by category."""
    data = _load()
    if category:
        data = [i for i in data if i.get("category") == category]
    return json.dumps({"count": len(data), "items": data})

def delete_item(item_id: str) -> str:
    """Delete an item by ID."""
    data = _load()
    original_count = len(data)
    data = [i for i in data if i["id"] != item_id]

    if len(data) == original_count:
        return json.dumps({"error": f"Item '{item_id}' not found."})

    _save(data)
    return json.dumps({"success": True, "deleted": item_id})

# ---------------------------------------------------------------------------
# MCP Tool Definitions — Claude reads these to understand your tools
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "add_item",
        "description": "Add a new item to the collection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the item.",
                },
                "category": {
                    "type": "string",
                    "description": "Category for the item.",
                    "default": "general",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_items",
        "description": "List all items, optionally filtered by category.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category. Omit to list all.",
                },
            },
        },
    },
    {
        "name": "delete_item",
        "description": "Delete an item by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "The ID of the item to delete.",
                },
            },
            "required": ["item_id"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool Handlers — Maps tool names to callables
# ---------------------------------------------------------------------------
TOOL_HANDLERS = {
    "add_item": lambda args: add_item(args["name"], args.get("category", "general")),
    "list_items": lambda args: list_items(args.get("category")),
    "delete_item": lambda args: delete_item(args["item_id"]),
}
