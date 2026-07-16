"""
Continuity — cross-chat project memory for Claude Desktop.

Save a recap at the end of any chat; resume with full context in the next one.
Tracks per-project recaps, decisions, and open next steps.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

SERVER_NAME = "continuity"
DATA_PATH = Path(__file__).parent / "data" / "continuity.json"

# ---------------------------------------------------------------- storage

def _load() -> dict:
    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"projects": {}}

def _save(data: dict):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _slug(name: str) -> str:
    return "-".join(name.strip().lower().split())

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _find_project(data: dict, project: str) -> Optional[str]:
    """Resolve a project reference: exact slug, then case-insensitive substring."""
    slug = _slug(project)
    if slug in data["projects"]:
        return slug
    needle = project.strip().lower()
    matches = [
        key for key, p in data["projects"].items()
        if needle in p["name"].lower() or needle in key
    ]
    return matches[0] if len(matches) == 1 else None

def _ensure_project(data: dict, project: str) -> str:
    key = _find_project(data, project)
    if key:
        return key
    key = _slug(project)
    data["projects"][key] = {
        "name": project.strip(),
        "created_at": _now(),
        "updated_at": _now(),
        "tags": [],
        "recaps": [],
        "decisions": [],
        "next_steps": [],
    }
    return key

# ---------------------------------------------------------------- tools

def save_recap(project: str, summary: str, decisions: Optional[list] = None,
               next_steps: Optional[list] = None, tags: Optional[list] = None) -> str:
    data = _load()
    key = _ensure_project(data, project)
    p = data["projects"][key]

    recap = {"at": _now(), "summary": summary}
    p["recaps"].append(recap)

    for d in decisions or []:
        p["decisions"].append({"at": _now(), "decision": d, "context": ""})
    if next_steps is not None:
        p["next_steps"] = list(next_steps)
    for t in tags or []:
        if t not in p["tags"]:
            p["tags"].append(t)
    p["updated_at"] = _now()

    _save(data)
    return json.dumps({
        "success": True,
        "project": p["name"],
        "recaps_saved": len(p["recaps"]),
        "open_next_steps": len(p["next_steps"]),
        "hint": "Start a future chat with: resume this project by name.",
    })

def resume(project: str) -> str:
    data = _load()
    key = _find_project(data, project)
    if not key:
        names = [p["name"] for p in data["projects"].values()]
        return json.dumps({
            "error": "Project '{}' not found or ambiguous.".format(project),
            "known_projects": names,
        })
    p = data["projects"][key]
    return json.dumps({
        "project": p["name"],
        "last_updated": p["updated_at"],
        "tags": p["tags"],
        "latest_recap": p["recaps"][-1] if p["recaps"] else None,
        "open_next_steps": p["next_steps"],
        "recent_decisions": p["decisions"][-10:],
        "recap_count": len(p["recaps"]),
    }, ensure_ascii=False)

def log_decision(project: str, decision: str, context: str = "") -> str:
    data = _load()
    key = _ensure_project(data, project)
    p = data["projects"][key]
    p["decisions"].append({"at": _now(), "decision": decision, "context": context})
    p["updated_at"] = _now()
    _save(data)
    return json.dumps({"success": True, "project": p["name"],
                       "decisions_logged": len(p["decisions"])})

def update_next_steps(project: str, next_steps: list) -> str:
    data = _load()
    key = _find_project(data, project)
    if not key:
        return json.dumps({"error": "Project '{}' not found.".format(project)})
    p = data["projects"][key]
    p["next_steps"] = list(next_steps)
    p["updated_at"] = _now()
    _save(data)
    return json.dumps({"success": True, "project": p["name"],
                       "open_next_steps": p["next_steps"]})

def list_projects() -> str:
    data = _load()
    projects = sorted(data["projects"].values(),
                      key=lambda p: p["updated_at"], reverse=True)
    return json.dumps({
        "count": len(projects),
        "projects": [
            {
                "name": p["name"],
                "last_updated": p["updated_at"],
                "tags": p["tags"],
                "open_next_steps": len(p["next_steps"]),
                "latest_summary": (p["recaps"][-1]["summary"][:160]
                                   if p["recaps"] else None),
            }
            for p in projects
        ],
    }, ensure_ascii=False)

def search(query: str) -> str:
    q = query.strip().lower()
    data = _load()
    hits = []
    for p in data["projects"].values():
        for r in p["recaps"]:
            if q in r["summary"].lower():
                hits.append({"project": p["name"], "type": "recap",
                             "at": r["at"], "text": r["summary"]})
        for d in p["decisions"]:
            if q in d["decision"].lower() or q in d.get("context", "").lower():
                hits.append({"project": p["name"], "type": "decision",
                             "at": d["at"], "text": d["decision"]})
        for s in p["next_steps"]:
            if q in s.lower():
                hits.append({"project": p["name"], "type": "next_step",
                             "at": p["updated_at"], "text": s})
        if q in p["name"].lower() or any(q in t.lower() for t in p["tags"]):
            hits.append({"project": p["name"], "type": "project",
                         "at": p["updated_at"], "text": p["name"]})
    return json.dumps({"query": query, "count": len(hits), "results": hits},
                      ensure_ascii=False)

# ---------------------------------------------------------------- MCP exports

TOOLS = [
    {
        "name": "save_recap",
        "description": (
            "Save an end-of-chat recap for a project so a future chat can resume with "
            "full context. Use when a conversation is ending, the chat is getting long, "
            "or the user says 'save a recap' / 'remember where we are'. Creates the "
            "project if it doesn't exist. next_steps REPLACES the open list."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project name, e.g. 'PC Build'."},
                "summary": {"type": "string", "description": "Detailed recap of state, context, and where things left off. Include specifics (part lists, file paths, versions) — this is all a future chat will see."},
                "decisions": {"type": "array", "items": {"type": "string"}, "description": "Decisions made this session."},
                "next_steps": {"type": "array", "items": {"type": "string"}, "description": "Open next steps (replaces the previous list)."},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags, e.g. ['hardware', 'consulting']."},
            },
            "required": ["project", "summary"],
        },
    },
    {
        "name": "resume",
        "description": (
            "Load a project's saved context: latest recap, open next steps, and recent "
            "decisions. Use at the start of a chat when the user wants to continue or "
            "resume previous work. Accepts partial names ('pc' matches 'PC Build')."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project name or partial match."},
            },
            "required": ["project"],
        },
    },
    {
        "name": "log_decision",
        "description": "Record a single decision mid-conversation without writing a full recap. Creates the project if needed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project name."},
                "decision": {"type": "string", "description": "The decision made."},
                "context": {"type": "string", "description": "Optional reasoning or context."},
            },
            "required": ["project", "decision"],
        },
    },
    {
        "name": "update_next_steps",
        "description": "Replace a project's open next-steps list (e.g. after completing some items).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project name or partial match."},
                "next_steps": {"type": "array", "items": {"type": "string"}, "description": "The new complete list of open next steps."},
            },
            "required": ["project", "next_steps"],
        },
    },
    {
        "name": "list_projects",
        "description": "List all tracked projects with last-updated time, tags, and latest summary. Use when the user asks 'what was I working on?'",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "search",
        "description": "Full-text search across all recaps, decisions, and next steps in every project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to search for."},
            },
            "required": ["query"],
        },
    },
]

TOOL_HANDLERS = {
    "save_recap": lambda args: save_recap(
        args["project"], args["summary"], args.get("decisions"),
        args.get("next_steps"), args.get("tags")),
    "resume": lambda args: resume(args["project"]),
    "log_decision": lambda args: log_decision(
        args["project"], args["decision"], args.get("context", "")),
    "update_next_steps": lambda args: update_next_steps(
        args["project"], args["next_steps"]),
    "list_projects": lambda args: list_projects(),
    "search": lambda args: search(args["query"]),
}
