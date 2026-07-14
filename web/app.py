"""Flask web UI for the GTM agent ecosystem."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.router import GTMRouter
from story_library.competitive_brief import generate_competitive_brief
from story_library.discovery_brief import generate_discovery_brief
from story_library.generator import generate_proposal

app = Flask(__name__)
router = GTMRouter()
outputs: dict[str, Path] = {}

GENERATORS = {
    "proposal": generate_proposal,
    "discovery": generate_discovery_brief,
    "competitive": generate_competitive_brief,
}

GENERATE_LABELS = {
    "proposal": "Generate Proposal Document",
    "discovery": "Generate Discovery Brief",
    "competitive": "Generate Competitive Brief",
}


def _response_payload(session_id: str, resp) -> dict:
    phase = resp.phase.value if hasattr(resp.phase, "value") else str(resp.phase)
    payload = {
        "session_id": session_id,
        "workflow": resp.workflow,
        "message": resp.message,
        "phase": phase,
        "awaiting_input": resp.awaiting_input,
        "done": resp.done,
        "mode": "public",
    }
    if resp.summary:
        payload["summary"] = resp.summary
    if resp.json_output:
        payload["json_output"] = resp.json_output
    if resp.tool_call:
        payload["tool_call"] = resp.tool_call
    if resp.workflow:
        payload["generate_label"] = GENERATE_LABELS.get(resp.workflow, "Generate Document")
    return payload


@app.get("/")
def index():
    return render_template("index.html", workflows=router.list_workflows())


@app.get("/api/workflows")
def list_workflows():
    return jsonify({"workflows": router.list_workflows()})


@app.post("/api/session/start")
def start_session():
    data = request.get_json(silent=True) or {}
    customer = (data.get("customer_account") or "").strip()
    workflow = (data.get("workflow") or "proposal").strip()
    if not customer:
        return jsonify({"error": "customer_account is required"}), 400

    session_id = str(uuid.uuid4())
    try:
        resp = router.start(workflow, customer, session_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_response_payload(session_id, resp))


@app.post("/api/session/<session_id>/message")
def send_message(session_id: str):
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    try:
        resp = router.process(session_id, message)
    except KeyError:
        return jsonify({"error": "Session not found. Start a new session."}), 404
    return jsonify(_response_payload(session_id, resp))


@app.post("/api/session/<session_id>/generate")
def generate_document(session_id: str):
    assistant = router.get_assistant(session_id)
    workflow = router.get_workflow(session_id)
    if not assistant or not getattr(assistant, "_final_json", None):
        return jsonify({"error": "Complete the intake and confirm the summary first."}), 400

    generator = GENERATORS.get(workflow or "proposal", generate_proposal)
    path = generator(assistant._final_json)
    outputs[session_id] = path
    return jsonify({
        "session_id": session_id,
        "workflow": workflow,
        "path": str(path),
        "filename": path.name,
        "download_url": f"/api/session/{session_id}/download",
        "data_source": "public",
    })


@app.get("/api/session/<session_id>/download")
def download_document(session_id: str):
    path = outputs.get(session_id)
    if not path or not path.exists():
        return jsonify({"error": "No generated document for this session."}), 404
    return send_file(path, as_attachment=True, download_name=path.name)


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "mode": "public",
        "workflows": [w["id"] for w in router.list_workflows()],
        "message": "Using public Cisco content and seller-provided inputs only. No API credentials required.",
    })


def main():
    app.run(host="127.0.0.1", port=8080, debug=True)


if __name__ == "__main__":
    main()
