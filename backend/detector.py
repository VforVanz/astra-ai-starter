"""Rule-based security detections for authentication and web request logs."""
from __future__ import annotations

import re
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import unquote


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _field(event: dict[str, Any], key: str, default: Any = "") -> Any:
    if key in event and event[key] is not None:
        return event[key]
    raw = event.get("raw")
    if isinstance(raw, dict):
        return raw.get(key, default)
    return default


def _minute(value: str) -> str:
    dt = _parse_timestamp(value)
    return dt.replace(second=0, microsecond=0).isoformat()


def detect_repeated_login_failures(events: list[dict[str, Any]], threshold: int = 5, window_minutes: int = 5) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    failure_types = {"login_failure", "failed_login", "authentication_failure", "login_failed"}
    for event in events:
        event_type = str(_field(event, "event_type")).lower()
        outcome = str(_field(event, "outcome")).lower()
        if event_type in failure_types or (event_type in {"login", "authentication"} and outcome in {"failure", "failed", "denied"}):
            grouped[str(_field(event, "source_ip"))].append(event)

    alerts = []
    window = timedelta(minutes=window_minutes)
    for source_ip, rows in grouped.items():
        rows.sort(key=lambda item: _parse_timestamp(str(_field(item, "timestamp"))))
        queue: deque[dict[str, Any]] = deque()
        already_alerted = False
        for event in rows:
            event_time = _parse_timestamp(str(_field(event, "timestamp")))
            queue.append(event)
            while queue and event_time - _parse_timestamp(str(_field(queue[0], "timestamp"))) > window:
                queue.popleft()
            if len(queue) >= threshold and not already_alerted:
                usernames = sorted({str(_field(item, "username")) for item in queue if _field(item, "username")})
                alerts.append({
                    "rule_id": "repeated_login_failure", "timestamp": str(_field(event, "timestamp")),
                    "window_start": str(_field(queue[0], "timestamp")), "source_ip": source_ip,
                    "event_type": "repeated_login_failure", "risk": "high",
                    "evidence": f"{len(queue)} kegagalan login dari sumber yang sama dalam {window_minutes} menit; username: {', '.join(usernames) if usernames else 'tidak tersedia'}. Perlu verifikasi.",
                })
                already_alerted = True
    return alerts


def detect_web_threats(events: list[dict[str, Any]], spike_threshold: int = 30, window_seconds: int = 60) -> list[dict[str, Any]]:
    """Detect traffic spikes and common suspicious HTTP request indicators from logs."""
    web_events = [e for e in events if str(_field(e, "event_type")).lower() == "http_request"]
    alerts: list[dict[str, Any]] = []

    # Traffic spike: at least spike_threshold requests from one source in 60 seconds.
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in web_events:
        grouped[str(_field(event, "source_ip"))].append(event)
    window = timedelta(seconds=window_seconds)
    for source_ip, rows in grouped.items():
        rows.sort(key=lambda e: _parse_timestamp(str(_field(e, "timestamp"))))
        queue: deque[dict[str, Any]] = deque()
        fired = False
        for event in rows:
            now = _parse_timestamp(str(_field(event, "timestamp")))
            queue.append(event)
            while queue and now - _parse_timestamp(str(_field(queue[0], "timestamp"))) > window:
                queue.popleft()
            if len(queue) >= spike_threshold and not fired:
                first = str(_field(queue[0], "timestamp"))
                alerts.append({
                    "rule_id": "http_traffic_spike", "timestamp": str(_field(event, "timestamp")),
                    "window_start": _minute(first), "source_ip": source_ip,
                    "event_type": "http_traffic_spike", "risk": "high",
                    "evidence": f"{len(queue)} request HTTP dari satu sumber dalam {window_seconds} detik. Lonjakan trafik perlu diverifikasi; belum tentu DDoS.",
                })
                fired = True

    # Match common indicators; these are heuristics, not proof of exploitation.
    patterns = [
        ("sql_injection_indicator", "high", re.compile(r"(?:union\s+select|select\s+.+\s+from|\bor\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+|sleep\s*\()", re.I), "Pola mirip SQL injection terdeteksi pada URL request."),
        ("xss_indicator", "medium", re.compile(r"(?:<\s*script|javascript\s*:|onerror\s*=|onload\s*=)", re.I), "Pola mirip XSS terdeteksi pada URL request."),
        ("path_traversal_indicator", "high", re.compile(r"(?:\.\./|\.\.\\|%2e%2e(?:%2f|/|%5c))", re.I), "Percobaan path traversal terindikasi pada URL request."),
    ]
    for event in web_events:
        path = unquote(str(_field(event, "path")))[:2048]
        if not path:
            continue
        for rule_id, risk, pattern, evidence in patterns:
            if pattern.search(path):
                alerts.append({
                    "rule_id": rule_id, "timestamp": str(_field(event, "timestamp")),
                    "window_start": _minute(str(_field(event, "timestamp"))),
                    "source_ip": str(_field(event, "source_ip")), "event_type": rule_id,
                    "risk": risk, "evidence": f"{evidence} Path: {path[:240]}. Indikator perlu investigasi, bukan bukti kompromi.",
                })
                break

    # Repeated server errors from one source can indicate probing or application stress.
    error_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in web_events:
        try:
            status = int(_field(event, "status_code", 0))
        except (TypeError, ValueError):
            status = 0
        if status >= 500:
            error_groups[str(_field(event, "source_ip"))].append(event)
    for source_ip, rows in error_groups.items():
        if len(rows) >= 10:
            first = min(rows, key=lambda e: _parse_timestamp(str(_field(e, "timestamp"))))
            last = max(rows, key=lambda e: _parse_timestamp(str(_field(e, "timestamp"))))
            if _parse_timestamp(str(_field(last, "timestamp"))) - _parse_timestamp(str(_field(first, "timestamp"))) <= timedelta(minutes=2):
                alerts.append({
                    "rule_id": "http_server_error_spike", "timestamp": str(_field(last, "timestamp")),
                    "window_start": _minute(str(_field(first, "timestamp"))), "source_ip": source_ip,
                    "event_type": "http_server_error_spike", "risk": "medium",
                    "evidence": f"{len(rows)} respons HTTP 5xx terkait sumber ini dalam dua menit. Periksa log aplikasi dan kesehatan server.",
                })
    return alerts


def run_detection(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return detect_repeated_login_failures(events) + detect_web_threats(events)
