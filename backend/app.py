"""ASTRA AI starter API. Run from the project root with: python -m backend.app"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS

try:  # Supports running as python -m backend.app and direct `python backend/app.py`.
    from .database import (
        create_alert, dashboard_summary, fetch_events, get_alert, init_db,
        insert_events, list_alerts, update_alert_status,
    )
    from .detector import run_detection
    from .parser import parse_jsonl, validate_event
except ImportError:  # pragma: no cover - fallback for direct execution
    from database import (
        create_alert, dashboard_summary, fetch_events, get_alert, init_db,
        insert_events, list_alerts, update_alert_status,
    )
    from detector import run_detection
    from parser import parse_jsonl, validate_event

ROOT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_FILE = ROOT_DIR / "data" / "sample_logs.jsonl"
ALLOWED_STATUSES = {"new", "investigating", "resolved"}

app = Flask(__name__)
# Allow a local frontend served with VS Code Live Server / common local dev ports.
CORS(app, resources={r"/api/*": {"origins": [
    "http://127.0.0.1:5500", "http://localhost:5500",
    "http://127.0.0.1:3000", "http://localhost:3000",
]}})
app.json.sort_keys = False
init_db()


def ingest_and_detect(events: list[dict[str, Any]]) -> dict[str, int]:
    inserted = insert_events(events)
    all_events = fetch_events()
    alerts = run_detection(all_events)
    new_alerts = sum(1 for alert in alerts if create_alert(alert))
    return {"events_received": len(events), "events_inserted": inserted, "new_alerts": new_alerts}


@app.get("/")
def index():
    return jsonify({
        "name": "ASTRA AI API",
        "message": "Backend aktif. Lihat /api/health, /api/dashboard, dan /api/alerts.",
        "version": "0.1.0",
    })


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "astra-ai-backend", "ai_enabled": False})


@app.get("/api/dashboard")
def dashboard():
    return jsonify(dashboard_summary())


@app.get("/api/alerts")
def alerts():
    return jsonify({"alerts": list_alerts(), "count": len(list_alerts())})


@app.get("/api/alerts/<int:alert_id>")
def alert_detail(alert_id: int):
    item = get_alert(alert_id)
    if item is None:
        return jsonify({"error": "Alert tidak ditemukan."}), 404
    return jsonify(item)


@app.patch("/api/alerts/<int:alert_id>")
def change_alert_status(alert_id: int):
    body = request.get_json(silent=True) or {}
    status = body.get("status")
    if status not in ALLOWED_STATUSES:
        return jsonify({"error": "Status harus new, investigating, atau resolved."}), 400
    if not update_alert_status(alert_id, status):
        return jsonify({"error": "Alert tidak ditemukan."}), 404
    return jsonify(get_alert(alert_id))


@app.post("/api/ingest")
def ingest():
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("events"), list):
        return jsonify({"error": "Kirim JSON dengan properti 'events' berupa array."}), 400
    try:
        events = [validate_event(event) for event in body["events"]]
        result = ingest_and_detect(events)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result), 201


@app.post("/api/ingest/sample")
def ingest_sample():
    try:
        events = parse_jsonl(SAMPLE_FILE.read_text(encoding="utf-8"))
        result = ingest_and_detect(events)
    except (OSError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"sample_file": SAMPLE_FILE.name, **result}), 201


if __name__ == "__main__":
    print("ASTRA AI API berjalan di http://127.0.0.1:5000")
    print("Gunakan POST /api/ingest/sample untuk memuat log demo sintetis.")
    app.run(host="127.0.0.1", port=5000, debug=True)
