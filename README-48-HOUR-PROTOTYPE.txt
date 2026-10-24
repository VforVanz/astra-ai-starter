ASTRA AI — 48-HOUR LOCAL TRAFFIC DETECTION PROTOTYPE

GOAL
This is a practical prototype for local testing: ingest HTTP/auth events, apply lightweight rules, show traffic summaries and alerts, and ask local Ollama to explain an alert. It does not guarantee detection of every attack and does not passively capture network packets.

PATCH CONTENTS
- backend/app.py, database.py, detector.py, parser.py: HTTP/auth event ingest, rule detections, traffic summary API.
- backend/alert_analysis.py: evidence-grounded Indonesian explanations using local Ollama and matching labeled examples.
- backend/labeled_examples.example.jsonl: example dataset format.
- frontend/index.html, frontend/app.js, frontend/style.css: traffic panel and alert analysis UI.
- test_detection.ps1: sends a small batch of synthetic local HTTP events; it does not generate network flood traffic.

INSTALL SAFELY
1. Stop Flask with Ctrl+C.
2. Back up backend\app.py, backend\database.py, backend\detector.py, backend\parser.py, frontend\index.html, frontend\app.js, and frontend\style.css.
3. Extract this ZIP into a temporary folder. Copy its backend files into the existing backend folder and frontend files into the existing frontend folder, preserving paths.
4. Do NOT delete or replace astra_ai.db, .venv, data, login/register/profile files, or existing config. Existing SQLite DB is reused.
5. Copy backend\labeled_examples.example.jsonl to backend\labeled_examples.jsonl, then merge your labeled examples into that new file. Keep one valid JSON object per line. Each row should include a label and ideally rule_id or event_type matching an alert.
6. Start backend: .\.venv\Scripts\python.exe -m backend.app
7. Open http://127.0.0.1:5500 and refresh. Select an alert, then press “Analisis dengan Ollama”.
8. For a local synthetic check, run: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\test_detection.ps1

CHECKS
- GET http://127.0.0.1:5000/api/health
- GET http://127.0.0.1:5000/api/traffic/summary
- GET http://127.0.0.1:5000/api/alerts
- POST http://127.0.0.1:5000/api/ingest using web-server events

LIMITS
Astra only analyzes events sent to /api/ingest (or sample ingestion). To observe a real site, configure a web server/reverse proxy to export access logs and a local adapter to send normalized events. A traffic spike rule is a heuristic, not proof of DDoS. SQLi/XSS/path traversal matches are indicators, not proof of successful exploitation. Port scanning requires network/firewall/IDS connection logs. Do not test against systems you do not own or have permission to monitor.

AI EXPLANATION NOTE
Labeled examples are retrieved as prompt context. This is not fine-tuning and does not change model weights. Keep training/evaluation examples separate from held-out test examples.
