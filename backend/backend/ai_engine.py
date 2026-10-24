"""Ollama AI engine for the ASTRA AI backend."""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434/api/chat",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:latest",
)

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

SYSTEM_PROMPT = """
Kamu adalah ASTRA AI, asisten keamanan siber yang ramah dan membantu.
Jawab dalam bahasa yang digunakan pengguna.
Berikan penjelasan yang jelas, akurat, dan terstruktur.
Untuk pertanyaan keamanan, utamakan analisis defensif, deteksi,
pencegahan, dan rekomendasi mitigasi.
Jangan mengklaim telah memeriksa sistem atau log jika data tersebut
belum diberikan kepadamu.
""".strip()


class AIEngineError(RuntimeError):
    """Raised when the AI engine cannot produce a valid response."""


def chat(
    message: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Send a chat message to Ollama and return its reply."""
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Pesan tidak boleh kosong.")

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    if isinstance(history, list):
        for item in history[-12:]:
            if not isinstance(item, dict):
                continue

            role = item.get("role")
            content = item.get("content")

            if (
                role in {"user", "assistant"}
                and isinstance(content, str)
                and content.strip()
            ):
                messages.append({
                    "role": role,
                    "content": content.strip()[:8000],
                })

    messages.append({
        "role": "user",
        "content": message.strip()[:8000],
    })

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }).encode("utf-8")

    request = Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=OLLAMA_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))

    except HTTPError as exc:
        raise AIEngineError(
            f"Ollama mengembalikan HTTP {exc.code}."
        ) from exc

    except (URLError, TimeoutError, OSError) as exc:
        raise AIEngineError(
            "Ollama tidak dapat dihubungi. Pastikan Ollama berjalan "
            "dan model sudah tersedia."
        ) from exc

    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AIEngineError(
            "Respons Ollama bukan JSON yang valid."
        ) from exc

    if not isinstance(result, dict):
        raise AIEngineError("Format respons Ollama tidak valid.")

    response_message = result.get("message")
    reply = (
        response_message.get("content", "")
        if isinstance(response_message, dict)
        else ""
    )

    if not isinstance(reply, str) or not reply.strip():
        raise AIEngineError("Ollama tidak memberikan jawaban.")

    return {
        "reply": reply.strip(),
        "model": str(result.get("model") or OLLAMA_MODEL),
    }


def check_connection() -> dict[str, Any]:
    """Check whether Ollama is reachable and the configured model exists."""
    tags_url = OLLAMA_URL.rsplit("/", 2)[0] + "/tags"
    request = Request(tags_url, method="GET")

    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))

    except (HTTPError, URLError, TimeoutError, OSError,
            json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {
            "connected": False,
            "model": OLLAMA_MODEL,
            "error": str(exc),
        }

    models = result.get("models", []) if isinstance(result, dict) else []
    available = [
        item.get("name", "")
        for item in models
        if isinstance(item, dict)
    ]

    model_available = OLLAMA_MODEL in available

    return {
        "connected": True,
        "model": OLLAMA_MODEL,
        "model_available": model_available,
        "available_models": available,
    }