import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request

try:
    from .database import (
        init_db, list_alerts, get_alert, update_alert_status,
        insert_events, create_alert, fetch_events, dashboard_summary, traffic_summary,
    )
    from .parser import validate_event, parse_jsonl
    from .detector import run_detection
    from .alert_analysis import analyze_alert, AlertAnalysisError
except ImportError:
    from database import (
        init_db, list_alerts, get_alert, update_alert_status,
        insert_events, create_alert, fetch_events, dashboard_summary, traffic_summary,
    )
    from parser import validate_event, parse_jsonl
    from detector import run_detection
    from alert_analysis import analyze_alert, AlertAnalysisError

app = Flask(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_TIMEOUT = 120
SAMPLE_FILE = Path(__file__).with_name("sample.jsonl")

ALLOWED_STATUSES = {"new", "investigating", "resolved"}


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, OPTIONS"
    return response


@app.get("/")
def home():
    return jsonify({
        "name": "ASTRA AI",
        "message": "Backend Astra AI aktif.",
        "status": "online",
        "model": OLLAMA_MODEL,
    })


@app.get("/api/health")
def health():
    return jsonify({
        "status": "online",
        "service": "Astra AI API",
        "model": OLLAMA_MODEL,
    })


@app.post("/api/chat")
def chat():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Request harus berupa JSON yang valid."}), 400

    message = body.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Pesan tidak boleh kosong."}), 400

    messages = [{
        "role": "system",
        "content": (
            "Kamu adalah Astra AI, asisten yang ramah, jelas, dan membantu. "
            "Jawab dalam bahasa pengguna."
        ),
    }]

    history = body.get("history", [])
    if isinstance(history, list):
        for item in history[-12:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({
                    "role": role,
                    "content": content.strip()[:8000],
                })

    messages.append({"role": "user", "content": message.strip()[:8000]})

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }).encode("utf-8")

    req = Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=OLLAMA_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))

        reply = result.get("message", {}).get("content", "")
        if not isinstance(reply, str) or not reply.strip():
            return jsonify({"error": "Ollama tidak memberikan jawaban."}), 502

        return jsonify({
            "reply": reply.strip(),
            "model": result.get("model", OLLAMA_MODEL),
        })

    except HTTPError as exc:
        return jsonify({"error": f"Ollama mengembalikan HTTP {exc.code}."}), 502
    except (URLError, TimeoutError) as exc:
        return jsonify({
            "error": "Ollama tidak dapat dihubungi. Pastikan Ollama sedang berjalan.",
            "detail": str(exc),
        }), 502
    except (json.JSONDecodeError, AttributeError):
        return jsonify({"error": "Respons Ollama tidak valid."}), 502


# =========================
# DASHBOARD & ALERTS
# =========================

init_db()


@app.get("/api/dashboard")
def dashboard_endpoint():
    return jsonify(dashboard_summary())


@app.get("/api/traffic/summary")
def traffic_summary_endpoint():
    return jsonify(traffic_summary())


@app.get("/api/alerts")
def alerts_endpoint():
    return jsonify({
        "alerts": list_alerts(),
        "summary": dashboard_summary(),
    })


@app.get("/api/alerts/<int:alert_id>")
def alert_detail_endpoint(alert_id):
    alert = get_alert(alert_id)
    if alert is None:
        return jsonify({"error": "Alert tidak ditemukan."}), 404
    return jsonify({"alert": alert})




@app.post("/api/alerts/<int:alert_id>/explain")
def explain_alert_endpoint(alert_id):
    """Explain an existing alert using evidence and matching labeled examples."""
    alert = get_alert(alert_id)
    if alert is None:
        return jsonify({"error": "Alert tidak ditemukan."}), 404

    related_events = [
        {"timestamp": e.get("timestamp"), "event_type": e.get("event_type"), "outcome": e.get("outcome")}
        for e in fetch_events() if e.get("source_ip") == alert.get("source_ip")
    ][-10:]
    try:
        result = analyze_alert(alert, related_events)
        return jsonify({"success": True, "alert_id": alert_id, **result})
    except AlertAnalysisError as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/alerts/<int:alert_id>/status", methods=["POST", "PUT", "PATCH"])
def alert_status_endpoint(alert_id):
    if get_alert(alert_id) is None:
        return jsonify({"error": "Alert tidak ditemukan."}), 404

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Body harus berupa JSON."}), 400

    status = body.get("status")
    if status not in ALLOWED_STATUSES:
        return jsonify({
            "error": "Status tidak valid.",
            "allowed_statuses": sorted(ALLOWED_STATUSES),
        }), 400

    update_alert_status(alert_id, status)
    return jsonify({"success": True, "alert": get_alert(alert_id)})


# =========================
# INGEST + DETECTION
# =========================

def ingest_and_detect(events):
    inserted = insert_events(events)

    # Jalankan detector terhadap seluruh event tersimpan.
    # Dengan begitu event sample yang baru masuk langsung terlihat oleh rule.
    stored_events = fetch_events()
    detections = run_detection(stored_events)

    alerts_created = 0
    for alert in detections:
        if create_alert(alert):
            alerts_created += 1

    return {
        "received": len(events),
        "inserted": inserted,
        "alerts_created": alerts_created,
    }


@app.post("/api/ingest")
def ingest_endpoint():
    body = request.get_json(silent=True)

    try:
        if isinstance(body, dict) and isinstance(body.get("events"), list):
            events = [validate_event(item) for item in body["events"]]
        elif isinstance(body, list):
            events = [validate_event(item) for item in body]
        else:
            events = parse_jsonl(request.get_data(as_text=True))

        return jsonify({"success": True, **ingest_and_detect(events)})

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/ingest/sample")
def ingest_sample_endpoint():
    if not SAMPLE_FILE.is_file():
        return jsonify({
            "error": "File sampel tidak ditemukan.",
            "expected_file": str(SAMPLE_FILE),
        }), 404

    try:
        # utf-8-sig menerima file UTF-8 biasa maupun file yang masih memiliki BOM.
        events = parse_jsonl(SAMPLE_FILE.read_text(encoding="utf-8-sig"))
        return jsonify({"success": True, **ingest_and_detect(events)})
    except (ValueError, OSError) as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    print("===================================")
    print("       ASTRA AI BACKEND")
    print("===================================")
    print("API     : http://127.0.0.1:5000")
    print("Health  : http://127.0.0.1:5000/api/health")
    print(f"Model   : {OLLAMA_MODEL}")
    print("===================================")
    app.run(host="127.0.0.1", port=5000, debug=True)
