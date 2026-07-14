"""Flask web UI for the proposal-building assistant."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.proposal_assistant import AssistantResponse, ProposalAssistant
from story_library.generator import generate_proposal

app = Flask(__name__)

sessions: dict[str, ProposalAssistant] = {}
outputs: dict[str, Path] = {}


def _response_payload(session_id: str, resp: AssistantResponse) -> dict:
    payload = {
        "session_id": session_id,
        "message": resp.message,
        "phase": resp.phase.value,
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
    return payload


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/session/start")
def start_session():
    data = request.get_json(silent=True) or {}
    customer = (data.get("customer_account") or "").strip()
    if not customer:
        return jsonify({"error": "customer_account is required"}), 400

    session_id = str(uuid.uuid4())
    assistant = ProposalAssistant()
    resp = assistant.start(customer)
    sessions[session_id] = assistant
    return jsonify(_response_payload(session_id, resp))


@app.post("/api/session/<session_id>/message")
def send_message(session_id: str):
    assistant = sessions.get(session_id)
    if not assistant:
        return jsonify({"error": "Session not found. Start a new session."}), 404

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    resp = assistant.process_input(message)
    return jsonify(_response_payload(session_id, resp))


@app.post("/api/session/<session_id>/generate")
def generate_document(session_id: str):
    assistant = sessions.get(session_id)
    if not assistant or not assistant._final_json:
        return jsonify({"error": "Complete the intake and confirm the summary first."}), 400

    path = generate_proposal(assistant._final_json)
    outputs[session_id] = path
    return jsonify({
        "session_id": session_id,
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
        "message": "Using public Cisco content and seller-provided inputs only. No API credentials required.",
    })


def main():
    app.run(host="127.0.0.1", port=8080, debug=True)


if __name__ == "__main__":
    main()
