"""Validation and parsing for JSON Lines (JSONL) security event logs."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

REQUIRED_FIELDS = ("timestamp", "source_ip", "event_type")


def validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError("Setiap event harus berupa objek JSON.")

    missing = [field for field in REQUIRED_FIELDS if not event.get(field)]
    if missing:
        raise ValueError("Field wajib belum ada: " + ", ".join(missing))

    try:
        parsed = datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Format timestamp tidak valid: {event['timestamp']}") from exc

    event_type = str(event["event_type"]).strip().lower()
    normalized = {
        "timestamp": parsed.isoformat(),
        "source_ip": str(event["source_ip"]).strip(),
        "event_type": event_type,
        "username": str(event["username"]).strip() if event.get("username") is not None else None,
        "outcome": str(event["outcome"]).strip().lower() if event.get("outcome") is not None else None,
    }
    if not normalized["source_ip"] or not normalized["event_type"]:
        raise ValueError("source_ip dan event_type tidak boleh kosong.")
    return normalized


def parse_jsonl(contents: str) -> list[dict[str, Any]]:
    events = []
    for line_number, line in enumerate(contents.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            raw = json.loads(line)
            events.append(validate_event(raw))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Baris {line_number}: {exc}") from exc
    return events
