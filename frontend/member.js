"use strict";

/* ==========================================
   ASTRA AI - MEMBER JAVASCRIPT
   Frontend: HTML, CSS, JavaScript
   Backend: Flask + Ollama
   ========================================== */

const SESSION_KEY = "astra_session";
const API_BASE = "http://127.0.0.1:5000/api";

/* ==========================================
   APPLICATION STATE
   ========================================== */

let session = null;
let allAlerts = [];
let selectedAlert = null;

/* ==========================================
   DOM HELPER
   ========================================== */

const $ = (id) => document.getElementById(id);

/* ==========================================
   SESSION MANAGEMENT
   ========================================== */

function getSession() {
  try {
    const savedSession = localStorage.getItem(SESSION_KEY);

    if (!savedSession) return null;

    const parsed = JSON.parse(savedSession);

    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      localStorage.removeItem(SESSION_KEY);
      return null;
    }

    return parsed;
  } catch (error) {
    console.error("Astra AI: Invalid session.", error);
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

function requireLogin() {
  session = getSession();

  if (!session) {
    window.location.replace("login.html");
    return false;
  }

  return true;
}

/* ==========================================
   API CONNECTION
   ========================================== */

async function apiRequest(endpoint, options = {}) {
  if (!session) {
    throw new Error("Silakan login terlebih dahulu.");
  }

  if (
    typeof endpoint !== "string" ||
    !endpoint.startsWith("/") ||
    endpoint.startsWith("//")
  ) {
    throw new Error("Endpoint API tidak valid.");
  }

  const headers = new Headers(options.headers || {});

  headers.set("Accept", "application/json");

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal
    });

    const contentType = response.headers.get("content-type") || "";

    const data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const message =
        typeof data === "object" && data !== null
          ? data.error || data.message
          : null;

      throw new Error(message || `HTTP ${response.status}`);
    }

    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Koneksi ke server timeout.");
    }

    console.error("Astra AI API:", error);
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

/* ==========================================
   MEMBER PROFILE
   ========================================== */

function setupMemberUI() {
  if (!session) return;

  const name =
    (typeof session.name === "string" && session.name.trim()) ||
    (
      typeof session.email === "string" &&
      session.email.includes("@")
        ? session.email.split("@")[0]
        : "Member"
    );

  const role =
    typeof session.role === "string" && session.role.trim()
      ? session.role
      : "Member";

  const initial = name.charAt(0).toUpperCase() || "M";

  if ($("userName")) {
    $("userName").textContent = name;
  }

  if ($("userRole")) {
    $("userRole").textContent = role;
  }

  if ($("userAvatar")) {
    $("userAvatar").textContent = initial;
  }

  setupUserDropdown();
}

/* ==========================================
   USER DROPDOWN
   ========================================== */

function setupUserDropdown() {
  const button = $("userButton");
  const dropdown = $("userDropdown");

  if (!button || !dropdown) return;

  button.setAttribute("aria-haspopup", "true");
  button.setAttribute("aria-expanded", "false");

  function closeDropdown() {
    dropdown.classList.remove("show");
    button.setAttribute("aria-expanded", "false");
  }

  button.addEventListener("click", (event) => {
    event.stopPropagation();

    const isOpen = dropdown.classList.toggle("show");

    button.setAttribute("aria-expanded", String(isOpen));
  });

  dropdown.addEventListener("click", (event) => {
    event.stopPropagation();
  });

  document.addEventListener("click", closeDropdown);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeDropdown();
    }
  });
}

/* ==========================================
   LOGOUT
   ========================================== */

function logout() {
  localStorage.removeItem(SESSION_KEY);
  session = null;

  window.location.replace("login.html");
}

/* ==========================================
   ALERT DATA
   ========================================== */

async function loadAlerts() {
  try {
    const data = await apiRequest("/alerts");

    allAlerts = Array.isArray(data)
      ? data
      : Array.isArray(data.alerts)
        ? data.alerts
        : [];

    return allAlerts;
  } catch (error) {
    console.error("Gagal memuat alert:", error);
    throw error;
  }
}

/* ==========================================
   INITIALIZE MEMBER PAGE
   ========================================== */

function initMemberPage() {
  if (!requireLogin()) return;

  setupMemberUI();

  console.info("Astra AI member page initialized.");
}

/* ==========================================
   START APPLICATION
   ========================================== */

if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded",
    initMemberPage,
    { once: true }
  );
} else {
  initMemberPage();
}
