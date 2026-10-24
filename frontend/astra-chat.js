
"use strict";

/* ==========================================
   ASTRA AI CHAT - FLASK + OLLAMA
   API: POST /api/chat
   ========================================== */

const ASTRA_CHAT_API = "http://127.0.0.1:5000/api/chat";
const ASTRA_CHAT_HISTORY_LIMIT = 12;

let astraChatHistory = [];
let astraChatBusy = false;

const chat$ = (id) => document.getElementById(id);

/* ==========================================
   SEND REQUEST TO FLASK
   ========================================== */

async function requestAstraAI(message) {
  const response = await fetch(ASTRA_CHAT_API, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    body: JSON.stringify({
      message: message,
      history: astraChatHistory.slice(-ASTRA_CHAT_HISTORY_LIMIT)
    })
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.error || `Server error: HTTP ${response.status}`
    );
  }

  if (typeof data.reply !== "string" || !data.reply.trim()) {
    throw new Error("Astra AI tidak memberikan jawaban.");
  }

  return data;
}

/* ==========================================
   DISPLAY CHAT MESSAGE
   ========================================== */

function addAstraChatMessage(role, text) {
  const container = chat$("chatMessages");

  if (!container) {
    console.error('Elemen "#chatMessages" tidak ditemukan.');
    return null;
  }

  const messageElement = document.createElement("div");
  messageElement.className = `chat-message ${role}`;
  messageElement.setAttribute("data-role", role);

  const contentElement = document.createElement("div");
  contentElement.className = "chat-message-content";

  // textContent mencegah teks jawaban diproses sebagai HTML.
  contentElement.textContent = text;

  messageElement.appendChild(contentElement);
  container.appendChild(messageElement);

  container.scrollTop = container.scrollHeight;

  return messageElement;
}

/* ==========================================
   SEND CHAT MESSAGE
   ========================================== */

async function sendAstraChatMessage() {
  if (astraChatBusy) return;

  const input = chat$("chatInput");
  const sendButton = chat$("sendButton");

  if (!input) {
    console.error('Elemen "#chatInput" tidak ditemukan.');
    return;
  }

  const message = input.value.trim();

  if (!message) return;

  // Tampilkan pesan pengguna.
  addAstraChatMessage("user", message);

  // Kosongkan input dan aktifkan loading.
  input.value = "";
  astraChatBusy = true;

  if (sendButton) sendButton.disabled = true;
  input.disabled = true;

  const loadingMessage = addAstraChatMessage(
    "assistant",
    "Astra AI sedang berpikir..."
  );

  try {
    const data = await requestAstraAI(message);

    if (loadingMessage) {
      const content = loadingMessage.querySelector(
        ".chat-message-content"
      );

      if (content) {
        content.textContent = data.reply;
      }
    } else {
      addAstraChatMessage("assistant", data.reply);
    }

    // Simpan percakapan untuk konteks pesan berikutnya.
    astraChatHistory.push(
      { role: "user", content: message },
      { role: "assistant", content: data.reply }
    );

    astraChatHistory = astraChatHistory.slice(
      -ASTRA_CHAT_HISTORY_LIMIT
    );

    console.info("Astra AI model:", data.model || "unknown");
  } catch (error) {
    console.error("Astra AI chat error:", error);

    if (loadingMessage) {
      const content = loadingMessage.querySelector(
        ".chat-message-content"
      );

      if (content) {
        content.textContent = `Gagal mendapatkan jawaban: ${error.message}`;
      }
    } else {
      addAstraChatMessage(
        "assistant",
        `Gagal mendapatkan jawaban: ${error.message}`
      );
    }
  } finally {
    astraChatBusy = false;

    if (sendButton) sendButton.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

/* ==========================================
   INITIALIZE CHAT EVENTS
   ========================================== */

function initAstraChat() {
  const input = chat$("chatInput");
  const sendButton = chat$("sendButton");

  if (!input || !sendButton) {
    console.warn(
      "Astra AI Chat: chatInput atau sendButton belum tersedia."
    );
    return;
  }

  // Mencegah event terpasang berulang.
  if (sendButton.dataset.astraChatReady === "true") return;

  sendButton.dataset.astraChatReady = "true";

  sendButton.addEventListener("click", sendAstraChatMessage);

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendAstraChatMessage();
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAstraChat, {
    once: true
  });
} else {
  initAstraChat();
}
