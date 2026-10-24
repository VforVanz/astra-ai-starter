"use strict";

const API = "http://127.0.0.1:5000/api";
const SESSION_KEY = "astra_session";
const CHAT_HISTORY_LIMIT = 6;
const CHAT_TIMEOUT_MS = 45000;
const $ = (id) => document.getElementById(id);
let alerts = [];
let selectedAlert = null;
let chatHistory = [];
let chatBusy = false;

function sessionData() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || "null"); }
  catch { return null; }
}

const session = sessionData();
if (!session) window.location.replace("login.html");

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    ...options,
    headers: { Accept: "application/json", ...(options.body ? {"Content-Type":"application/json"} : {}), ...(options.headers || {}) }
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function animateNumber(el, value) {
  if (!el) return;
  const end = Number(value) || 0;
  const start = Number(el.dataset.value || 0);
  const duration = 650;
  const t0 = performance.now();
  function frame(now) {
    const p = Math.min(1, (now - t0) / duration);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(start + (end - start) * eased);
    if (p < 1) requestAnimationFrame(frame); else el.dataset.value = String(end);
  }
  requestAnimationFrame(frame);
}

function setupUser() {
  if (!session) return;
  const name = String(session.name || session.email || "Member").split("@")[0];
  const role = session.role || "Member";
  $("userName") && ($("userName").textContent = name);
  $("userRole") && ($("userRole").textContent = role);
  $("userAvatar") && ($("userAvatar").textContent = name.charAt(0).toUpperCase() || "M");
  $("userButton")?.addEventListener("click", (e) => {
    e.stopPropagation();
    $("userDropdown")?.classList.toggle("show");
  });
  document.addEventListener("click", () => $("userDropdown")?.classList.remove("show"));
  $("logoutBtn")?.addEventListener("click", () => {
    localStorage.removeItem(SESSION_KEY);
    location.href = "login.html";
  });
}

function setConnection(ok, text) {
  const box = $("connectionStatus");
  if (!box) return;
  box.classList.toggle("ok", ok);
  box.classList.toggle("error", !ok);
  box.innerHTML = `<span class="banner-icon">${ok ? "✓" : "!"}</span><span>${text}</span>`;
  $("apiStatus") && ($("apiStatus").textContent = ok ? "ONLINE" : "OFFLINE");
  $("healthApi") && ($("healthApi").textContent = ok ? "Online" : "Offline");
  $("healthApi")?.classList.toggle("online", ok);
}

function riskClass(risk) { return `risk-${String(risk || "low").toLowerCase()}`; }
function statusClass(status) { return `status-${String(status || "new").toLowerCase()}`; }

function renderAlerts() {
  const query = ($( "searchInput")?.value || "").toLowerCase().trim();
  const risk = $("riskFilter")?.value || "all";
  const status = $("statusFilter")?.value || "all";
  const filtered = alerts.filter(a => {
    const text = `${a.source_ip} ${a.event_type} ${a.evidence} ${a.status}`.toLowerCase();
    return (!query || text.includes(query)) && (risk === "all" || a.risk === risk) && (status === "all" || a.status === status);
  });
  const tbody = $("alertsTable");
  if (!tbody) return;
  $("alertCount") && ($("alertCount").textContent = `${filtered.length} alert${filtered.length === 1 ? "" : "s"}`);
  if (!filtered.length) {
    tbody.innerHTML = "";
    $("alertMessage").textContent = alerts.length ? "Tidak ada alert yang cocok." : "Belum ada alert.";
    return;
  }
  $("alertMessage").textContent = "";
  tbody.innerHTML = filtered.map((a, i) => `
    <tr class="alert-row" data-id="${a.id}" style="--row-delay:${i * 45}ms">
      <td>${formatDate(a.timestamp)}</td>
      <td><span class="ip-chip">${escapeHtml(a.source_ip)}</span></td>
      <td><b>${escapeHtml(a.event_type)}</b></td>
      <td><span class="risk-pill ${riskClass(a.risk)}"><i></i>${escapeHtml(a.risk)}</span></td>
      <td><span class="status-pill ${statusClass(a.status)}">${escapeHtml(a.status)}</span></td>
      <td class="evidence-cell">${escapeHtml(a.evidence)}</td>
      <td><button class="row-open" data-id="${a.id}">View</button></td>
    </tr>`).join("");
  tbody.querySelectorAll(".alert-row, .row-open").forEach(el => el.addEventListener("click", e => {
    const id = Number(e.currentTarget.dataset.id || e.target.dataset.id);
    if (id) selectAlert(id);
  }));
}

function formatDate(value) {
  try { return new Date(value).toLocaleString("id-ID", {day:"2-digit", month:"short", hour:"2-digit", minute:"2-digit"}); }
  catch { return value || "-"; }
}
function escapeHtml(v) { return String(v ?? "").replace(/[&<>\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c])); }

function updateSeverity() {
  const counts = {critical:0, high:0, medium:0, low:0};
  alerts.forEach(a => counts[a.risk] = (counts[a.risk] || 0) + 1);
  ["critical","high","medium","low"].forEach(k => { const el = $(k + "Count"); if (el) animateNumber(el, counts[k]); });
  animateNumber($("severityTotal"), alerts.length);
  const total = alerts.length || 1;
  const c = Math.round(counts.critical / total * 360);
  const h = Math.round(counts.high / total * 360);
  $("severityRing")?.style.setProperty("--severity-angle", `${c + h}deg`);
}

async function loadTraffic() {
  try {
    const data = await api("/traffic/summary");
    animateNumber($("trafficMinute"), data.requests_last_minute);
    animateNumber($("trafficFive"), data.requests_last_5_minutes);
    animateNumber($("trafficSources"), data.unique_sources_last_5_minutes);
    animateNumber($("trafficErrors"), data.http_errors_last_5_minutes);
    const note = $("trafficNote");
    if (note) note.textContent = `Sumber: ${data.source || "local logs"}. Hanya request yang tercatat melalui log/event yang dikirim ke backend yang dihitung.`;
    const latest = $("trafficLatest");
    if (latest) {
      const rows = Array.isArray(data.latest_requests) ? data.latest_requests : [];
      latest.innerHTML = rows.length ? `<div class="muted" style="font-size:12px;margin-bottom:3px">Request terbaru</div>` + rows.map(r => `<div class="traffic-row"><span>${escapeHtml(r.method || "-")} · ${escapeHtml(String(r.status_code ?? "-"))}</span><span title="${escapeHtml(r.path || "-")}">${escapeHtml(r.path || "-")} <span class="muted">· ${escapeHtml(r.source_ip || "-")}</span></span><span class="traffic-status">${escapeHtml(String(r.status_code ?? "-"))}</span></div>`).join("") : `<div class="muted" style="font-size:12px">Belum ada event HTTP. Kirim log melalui POST /api/ingest untuk mulai memantau.</div>`;
    }
  } catch (e) {
    const note = $("trafficNote");
    if (note) note.textContent = `Traffic Monitor tidak tersedia: ${e.message}`;
  }
}

async function loadDashboard() {
  try {
    const data = await api("/alerts");
    alerts = Array.isArray(data.alerts) ? data.alerts : [];
    const s = data.summary || {};
    animateNumber($("totalAlerts"), s.total_alerts);
    animateNumber($("highRisk"), s.high_risk_alerts);
    animateNumber($("openIncidents"), s.open_incidents);
    animateNumber($("eventsIngested"), s.events_ingested);
    updateSeverity();
    renderAlerts();
    setConnection(true, "Terhubung ke backend ASTRA AI · data live");
    loadTraffic();
    $("lastUpdated") && ($("lastUpdated").textContent = `Diperbarui ${new Date().toLocaleTimeString("id-ID", {hour:"2-digit", minute:"2-digit"})}`);
  } catch (e) {
    setConnection(false, `Backend tidak dapat dihubungi · ${e.message}`);
    renderAlerts();
  }
}

async function selectAlert(id) {
  const local = alerts.find(a => a.id === id);
  if (!local) return;
  try {
    const data = await api(`/alerts/${id}`);
    selectedAlert = data.alert || local;
  } catch { selectedAlert = local; }
  const a = selectedAlert;
  $("alertDetail").innerHTML = `
    <div class="detail-kicker">INCIDENT #${a.id}</div>
    <div class="detail-head"><div><h3>${escapeHtml(a.event_type)}</h3><p>${formatDate(a.timestamp)} · ${escapeHtml(a.source_ip)}</p></div><span class="risk-pill ${riskClass(a.risk)}"><i></i>${escapeHtml(a.risk)}</span></div>
    <div class="detail-grid"><div><span>Source IP</span><b>${escapeHtml(a.source_ip)}</b></div><div><span>Status</span><b>${escapeHtml(a.status)}</b></div><div><span>Rule</span><b>${escapeHtml(a.rule_id || "detection-rule")}</b></div><div><span>Window</span><b>${formatDate(a.window_start || a.timestamp)}</b></div></div>
    <div class="evidence-box"><span>DETECTION EVIDENCE</span><p>${escapeHtml(a.evidence)}</p></div>`;
  $("assessmentContent").innerHTML = `
    <div class="assessment-live"><div class="assessment-icon">AI</div><div><strong>Prioritas ${escapeHtml(a.risk)}</strong><p>Indikator ini perlu diverifikasi. Jalankan analisis lokal untuk mendapatkan penjelasan berbasis bukti.</p></div></div>
    <button type="button" id="explainAlertBtn" class="row-open" style="margin-top:12px">Analisis dengan Ollama</button>
    <div id="ollamaExplanation" class="evidence-box" style="margin-top:12px;white-space:pre-wrap;display:none"></div>`;
  $("explainAlertBtn")?.addEventListener("click", async () => {
    const btn = $("explainAlertBtn"), output = $("ollamaExplanation");
    btn.disabled = true; btn.textContent = "Ollama sedang menganalisis…";
    output.style.display = "block"; output.textContent = "Menganalisis bukti alert dan contoh dataset yang relevan…";
    try {
      const result = await api(`/alerts/${a.id}/explain`, {method:"POST"});
      output.textContent = `${result.analysis}\n\nModel: ${result.model || "lokal"} · Contoh berlabel cocok: ${result.matching_examples_used ?? 0}\n${result.note || ""}`;
    } catch (err) {
      output.textContent = `Analisis gagal: ${err.message}. Pastikan Ollama aktif dan model llama3.2:latest tersedia.`;
    } finally { btn.disabled = false; btn.textContent = "Analisis ulang dengan Ollama"; }
  });
  document.querySelector("#analysis")?.scrollIntoView({behavior:"smooth", block:"start"});
}

function setupNavigation() {
  document.querySelectorAll(".nav-link").forEach(link => link.addEventListener("click", () => {
    document.querySelectorAll(".nav-link").forEach(x => x.classList.remove("active"));
    link.classList.add("active");
    $("sidebar")?.classList.remove("open");
  }));
  $("menuBtn")?.addEventListener("click", () => $("sidebar")?.classList.toggle("open"));
  ["searchInput","riskFilter","statusFilter"].forEach(id => $(id)?.addEventListener("input", renderAlerts));
  $("refreshBtn")?.addEventListener("click", async () => {
    const b = $("refreshBtn"); b.classList.add("is-loading"); await loadDashboard(); b.classList.remove("is-loading");
  });
}

function setupAmbientMotion() {
  const canvas = document.createElement("canvas");
  canvas.className = "ambient-canvas";
  document.body.prepend(canvas);
  const ctx = canvas.getContext("2d");
  const points = Array.from({length: 34}, () => ({x:Math.random(), y:Math.random(), s:.3+Math.random()*1.1, a:.12+Math.random()*.35}));
  function resize(){ canvas.width=innerWidth*devicePixelRatio; canvas.height=innerHeight*devicePixelRatio; ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0); }
  addEventListener("resize", resize); resize();
  let t=0;
  function draw(){
    t+=.003; ctx.clearRect(0,0,innerWidth,innerHeight);
    points.forEach(p=>{ p.y-=.00025*p.s; if(p.y<-.02)p.y=1.02; const x=p.x*innerWidth, y=p.y*innerHeight; ctx.beginPath(); ctx.arc(x,y,p.s,0,Math.PI*2); ctx.fillStyle=`rgba(57,230,208,${p.a})`; ctx.fill(); });
    requestAnimationFrame(draw);
  }
  draw();
}

async function sendChat() {
  if (chatBusy) return;
  const input=$("astraChatInput"), box=$("astraChatMessages"), button=$("astraChatSend"), status=$("astraChatStatus");
  const message=input?.value.trim(); if(!message) return;
  chatBusy=true; input.value=""; button.disabled=true; status.textContent="ASTRA sedang menganalisis...";
  addChat("user", message);
  const loading=addChat("assistant", "Menganalisis permintaan…");
  try {
    const data=await api("/chat", {method:"POST", body:JSON.stringify({message, history:chatHistory.slice(-12)})});
    loading.querySelector(".message-body").textContent=data.reply;
    chatHistory.push({role:"user",content:message},{role:"assistant",content:data.reply});
    status.textContent=`Model ${data.model || "local"} · siap`;
  } catch(e) { loading.querySelector(".message-body").textContent=`Gagal: ${e.message}`; status.textContent="Periksa backend / Ollama."; }
  finally { chatBusy=false; button.disabled=false; input.focus(); }
}
function addChat(role,text,allowHtml=false){
  const box=$("astraChatMessages");
  const el=document.createElement("div");
  el.className=`astra-chat-message ${role}`;
  el.innerHTML=`<span class="message-label">${role === "user" ? "YOU" : "ASTRA AI"}</span><div class="message-body"></div>`;
  const body=el.querySelector(".message-body");
  if(allowHtml) body.innerHTML=text; else body.textContent=text;
  box.appendChild(el);
  box.scrollTop=box.scrollHeight;
  return el;
}
function autoGrowChatInput(input){
  if(!input) return;
  input.style.height="auto";
  input.style.height=Math.min(input.scrollHeight,140)+"px";
}
function setupChat(){
  const input=$("astraChatInput");
  $("astraChatForm")?.addEventListener("submit", e=>{e.preventDefault();sendChat();});
  input?.addEventListener("input",()=>autoGrowChatInput(input));
  input?.addEventListener("keydown", e=>{
    if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendChat();}
  });
  document.querySelectorAll(".astra-quick-prompts button").forEach(btn=>{
    btn.addEventListener("click",()=>{
      if(!input) return;
      input.value=btn.dataset.prompt||"";
      autoGrowChatInput(input);
      input.focus();
    });
  });
}

function init(){
  setupUser(); setupNavigation(); setupChat(); setupAmbientMotion(); loadDashboard();
  window.setInterval(loadTraffic, 15000);
}
if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, {once:true}); else init();
