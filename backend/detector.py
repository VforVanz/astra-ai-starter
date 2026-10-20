"""Deterministic starter detection rules for synthetic authentication logs."""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def detect_repeated_login_failures(
    events: list[dict[str, Any]], threshold: int = 5, window_minutes: int = 5
) -> list[dict[str, Any]]:
    """Alert on the first point at which an IP reaches threshold failed logins in a time window.

    The rule is a demo heuristic, not proof of an attack. Events are expected to have
    normalized timestamps and event_type/outcome fields.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        is_failure = (
            event.get("event_type", "").lower() in {"login_failure", "failed_login", "authentication_failure"}
            or (
                event.get("event_type", "").lower() in {"login", "authentication"}
                and event.get("outcome", "").lower() in {"failure", "failed", "denied"}
            )
        )
        if is_failure:
            grouped[event["source_ip"]].append(event)

    alerts: list[dict[str, Any]] = []
    window = timedelta(minutes=window_minutes)
    for source_ip, rows in grouped.items():
        rows.sort(key=lambda item: _parse_timestamp(item["timestamp"]))
        queue: deque[dict[str, Any]] = deque()
        already_alerted = False
        for event in rows:
            event_time = _parse_timestamp(event["timestamp"])
            queue.append(event)
            while queue and event_time - _parse_timestamp(queue[0]["timestamp"]) > window:
                queue.popleft()
            if len(queue) >= threshold and not already_alerted:
                start = _parse_timestamp(queue[0]["timestamp"])
                usernames = sorted({str(item.get("username")) for item in queue if item.get("username")})
                user_text = ", ".join(usernames) if usernames else "tidak tersedia"
                alerts.append({
                    "rule_id": "repeated_login_failure",
                    "timestamp": event["timestamp"],
                    "window_start": queue[0]["timestamp"],
                    "source_ip": source_ip,
                    "event_type": "repeated_login_failure",
                    "risk": "high",
                    "evidence": (
                        f"{len(queue)} kegagalan login dari sumber yang sama dalam "
                        f"maksimal {window_minutes} menit; username teramati: {user_text}. "
                        "Indikator ini perlu diverifikasi dan bukan bukti pasti serangan."
                    ),
                })
                already_alerted = True
    return alerts


def run_detection(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run all currently implemented rules."""
    return detect_repeated_login_failures(events)
