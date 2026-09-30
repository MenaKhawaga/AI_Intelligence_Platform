// ===================================================================
// AI Intelligence Platform — Frontend Controller
// Pure Vanilla JS (no build step, no framework)
// ===================================================================

const API_BASE = (() => {
  const { protocol, hostname, port } = window.location;
  if (port === "8000" || hostname === "") {
    return `${protocol}//${hostname}:8000`;
  }
  return "http://127.0.0.1:8000";
})();

let TOKEN = localStorage.getItem("aip_token") || null;
let USER_EMAIL = localStorage.getItem("aip_email") || "";

// Centralized API fetch helper
async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (TOKEN) headers["Authorization"] = `Bearer ${TOKEN}`;
  if (opts.body && typeof opts.body !== "string") {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.body);
  }
  let res;
  try {
    res = await fetch(API_BASE + path, { ...opts, headers });
  } catch (networkErr) {
    throw new Error(`Could not reach the API at ${API_BASE}. Is the backend running?`);
  }
  let data = {};
  try {
    data = await res.json();
  } catch (_) {
    /* empty response body */
  }
  if (!res.ok) {
    if (res.status === 401) {
      logout();
      throw new Error("Your session expired. Please log in again.");
    }
    const detail = data && data.detail;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${res.status})`);
  }
  return data;
}

const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));

// ------------------------------------------------------------------ Theme Management (Apple Light Default / Dark Toggle)
function initTheme() {
  const saved = localStorage.getItem("aip_theme") || "light";
  applyTheme(saved);
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("aip_theme", theme);
  updateThemeUI(theme);
}

function updateThemeUI(theme) {
  const isDark = theme === "dark";
  document.querySelectorAll(".theme-icon-moon").forEach((el) => {
    el.style.display = isDark ? "none" : "inline-block";
  });
  document.querySelectorAll(".theme-icon-sun").forEach((el) => {
    el.style.display = isDark ? "inline-block" : "none";
  });
  document.querySelectorAll(".theme-text").forEach((el) => {
    el.textContent = isDark ? "Light" : "Dark";
  });
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "light" ? "dark" : "light";
  applyTheme(next);
}

const themeBtn = $("themeToggle");
if (themeBtn) themeBtn.onclick = toggleTheme;
const authThemeBtn = $("authThemeToggle");
if (authThemeBtn) authThemeBtn.onclick = toggleTheme;

// Source Color & Badge Helpers
function getSourceBadge(source) {
  const s = String(source || "").toLowerCase();
  let cls = "gray";
  let label = source || "Unknown";

  if (s.includes("hacker") || s.includes("hn")) {
    cls = "orange";
    label = "Hacker News";
  } else if (s.includes("github")) {
    cls = "teal";
    label = "GitHub";
  } else if (s.includes("arxiv")) {
    cls = "cyan";
    label = "arXiv";
  } else if (s.includes("reddit")) {
    cls = "amber";
    label = "Reddit";
  } else if (s.includes("rss")) {
    cls = "emerald";
    label = "RSS";
  }
  return `<span class="badge ${cls}">${esc(label)}</span>`;
}

// ------------------------------------------------------------------ Authentication
let authMode = "login";

$("loginTab").onclick = () => setAuthMode("login");
$("registerTab").onclick = () => setAuthMode("register");

function setAuthMode(mode) {
  authMode = mode;
  $("loginTab").classList.toggle("active", mode === "login");
  $("registerTab").classList.toggle("active", mode === "register");
  $("authBtnLabel").textContent = mode === "login" ? "Log In" : "Create Account";
  $("password").setAttribute("autocomplete", mode === "login" ? "current-password" : "new-password");
  hideAuthMsg();
}

function showAuthMsg(text, kind) {
  const box = $("authMsg");
  box.textContent = text;
  box.className = `msg-box ${kind}`;
  box.hidden = false;
  box.style.display = "flex";
}
function hideAuthMsg() {
  const box = $("authMsg");
  box.hidden = true;
  box.style.display = "none";
}

function setAuthLoading(loading) {
  $("authBtn").disabled = loading;
  $("authSpinner").hidden = !loading;
  $("authSpinner").style.display = loading ? "inline-block" : "none";
}

$("authForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAuthMsg();

  const email = $("email").value.trim();
  const password = $("password").value;

  if (!email || !email.includes("@")) {
    showAuthMsg("Please enter a valid email address.", "error");
    return;
  }
  if (password.length < 8) {
    showAuthMsg("Password must contain at least 8 characters.", "error");
    return;
  }

  setAuthLoading(true);
  try {
    if (authMode === "register") {
      await api("/auth/register", { method: "POST", body: { email, password } });
      showAuthMsg("Account created! Signing you in...", "success");
    }
    const login = await api("/auth/login", { method: "POST", body: { email, password } });
    TOKEN = login.access_token;
    localStorage.setItem("aip_token", TOKEN);
    await afterLogin();
  } catch (err) {
    showAuthMsg(err.message, "error");
  } finally {
    setAuthLoading(false);
  }
});


async function afterLogin() {
  const me = await api("/auth/me");

  console.log("AUTH ME:", me);
  console.log("IS ADMIN:", me.is_admin);
  console.log("CURRENT PATH:", window.location.pathname);

  setupAdminNavigation(me);

  USER_EMAIL = me.email;
  localStorage.setItem("aip_email", USER_EMAIL);

  // If an admin clicked "Open User Platform",
  // allow the admin to stay on the normal user platform.
  const userMode =
    sessionStorage.getItem("aip_user_mode") === "true";

  // Admin users go directly to the Admin Dashboard
  // unless they intentionally chose User Platform.
  if (
    me.is_admin &&
    !userMode &&
    (
      window.location.pathname === "/" ||
      window.location.pathname === "/index.html"
    )
  ) {
    window.location.href = `${API_BASE}/admin/`;
    return;
  }

  // The user-platform mode is only needed once.
  sessionStorage.removeItem("aip_user_mode");

  $("userEmail").textContent = USER_EMAIL;

  if ($("userAvatarChar")) {
    $("userAvatarChar").textContent =
      (USER_EMAIL[0] || "U").toUpperCase();
  }

  $("auth").hidden = true;
  $("auth").style.display = "none";

  $("shell").hidden = false;
  $("shell").style.display = "block";

  await loadDashboard();
}

function setupAdminNavigation(me) {

    const button = $("openAdminPanel");

    if (!button) {
        return;
    }

    if (me && me.is_admin) {

        button.hidden = false;

        button.addEventListener("click", () => {

            sessionStorage.removeItem(
                "aip_user_mode"
            );

            window.location.href =
                `${API_BASE}/admin/`;
        });

    } else {

        button.hidden = true;
    }
}

function logout() {
  TOKEN = null;
  localStorage.removeItem("aip_token");
  localStorage.removeItem("aip_email");
  $("shell").hidden = true;
  $("shell").style.display = "none";
  $("auth").hidden = false;
  $("auth").style.display = "flex";
  $("password").value = "";
  hideAuthMsg();
}
$("logout").onclick = logout;

// ------------------------------------------------------------------ Navigation
document.querySelectorAll(".navbtn").forEach((btn) => {
  btn.onclick = () => switchView(btn.dataset.view);
});

const loaders = {
  dashboard: loadDashboard,
  intelligence: loadIntelligence,
  trends: loadTrendsView,
  analytics: loadAnalytics,
};

function switchView(name) {
  document.querySelectorAll(".navbtn").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
  if (name !== "trends") clearInterval(trendsPollTimer);
  if (loaders[name]) loaders[name]();
  if (name === "dashboard") triggerCountUps($("dashCards"));
  if (name === "analytics") triggerCountUps($("analyticsBox"));
}
window.switchView = switchView;

// ------------------------------------------------------------------ UI Helpers
function loadingHtml(text = "Loading data...") {
  return `<div class="loading-state"><span class="spinner" style="border-color: rgba(13,148,136,0.3); border-top-color: var(--primary); width: 22px; height: 22px; display: inline-block;"></span><div>${esc(text)}</div></div>`;
}

// ------------------------------------------------------------------ Count-Up Stat Animations
function animateCountUp(el, duration = 800) {
  if (!el) return;
  const targetStr = el.getAttribute("data-target");
  if (targetStr === null || targetStr === undefined) return;
  const target = parseFloat(targetStr);
  if (isNaN(target)) return;

  const decimals = parseInt(el.getAttribute("data-decimals") || "0", 10);
  const prefix = el.getAttribute("data-prefix") || "";
  const suffix = el.getAttribute("data-suffix") || "";

  let startTime = null;

  function step(timestamp) {
    if (!startTime) startTime = timestamp;
    const elapsed = timestamp - startTime;
    const progress = Math.min(elapsed / duration, 1);

    // easeOutCubic curve: smooth decelerating approach to destination
    const ease = 1 - Math.pow(1 - progress, 3);
    const current = target * ease;

    if (decimals > 0) {
      el.textContent = `${prefix}${current.toFixed(decimals)}${suffix}`;
    } else {
      el.textContent = `${prefix}${Math.round(current).toLocaleString()}${suffix}`;
    }

    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      if (decimals > 0) {
        el.textContent = `${prefix}${target.toFixed(decimals)}${suffix}`;
      } else {
        el.textContent = `${prefix}${Math.round(target).toLocaleString()}${suffix}`;
      }
    }
  }

  requestAnimationFrame(step);
}

function triggerCountUps(container = document) {
  const elements = container.querySelectorAll(".count-up-val");
  elements.forEach((el) => animateCountUp(el, 850));
}

function emptyHtml(text) {
  return `
    <div class="empty-state">
      <div class="empty-state-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
      </div>
      <div>${esc(text)}</div>
    </div>`;
}

function errorHtml(text) {
  return `
    <div class="error-state">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="15" y1="9" x2="9" y2="15"></line>
        <line x1="9" y1="9" x2="15" y2="15"></line>
      </svg>
      <div>${esc(text)}</div>
    </div>`;
}

function fmtDate(v) {
  if (!v) return "Recent";
  try {
    return new Date(v).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch (_) {
    return v;
  }
}

function fmtDateTime(v) {
  if (!v) return "Recent";
  try {
    return new Date(v).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch (_) {
    return v;
  }
}

// ------------------------------------------------------------------ Dashboard View
async function loadDashboard() {
  const cards = $("dashCards");
  const recent = $("dashRecent");
  cards.innerHTML = loadingHtml("Loading platform metrics...");
  recent.innerHTML = "";

  try {
    const overview = await api("/analytics/overview");
    const sourceCount = Object.keys(overview.sources || {}).length;

    cards.innerHTML = `
      <div class="card stat-card">
        <div class="stat-header">
          <span class="stat-label">Total Volume</span>
          <div class="stat-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
            </svg>
          </div>
        </div>
        <div class="stat-value count-up-val" data-target="${overview.total_articles || 0}">${esc(overview.total_articles)}</div>
        <div class="stat-subtext">Ingested articles across channels</div>
      </div>

      <div class="card stat-card">
        <div class="stat-header">
          <span class="stat-label">Active Topics</span>
          <div class="stat-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
              <polyline points="17 6 23 6 23 12"></polyline>
            </svg>
          </div>
        </div>
        <div class="stat-value count-up-val" data-target="${overview.total_topics || 0}">${esc(overview.total_topics)}</div>
        <div class="stat-subtext">Single-link clustered clusters</div>
      </div>

      <div class="card stat-card">
        <div class="stat-header">
          <span class="stat-label">Avg. Relevance</span>
          <div class="stat-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <polygon points="12 6 12 12 16 14"></polygon>
            </svg>
          </div>
        </div>
        <div class="stat-value count-up-val" data-target="${overview.average_relevance || 0}" data-decimals="2">${esc(overview.average_relevance)}</div>
        <div class="stat-subtext">Quality signal distribution index</div>
      </div>

      <div class="card stat-card">
        <div class="stat-header">
          <span class="stat-label">Monitored Feeds</span>
          <div class="stat-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 11a9 9 0 0 1 9 9"></path>
              <path d="M4 4a16 16 0 0 1 16 16"></path>
              <circle cx="5" cy="19" r="1"></circle>
            </svg>
          </div>
        </div>
        <div class="stat-value count-up-val" data-target="${sourceCount}">${esc(sourceCount)}</div>
        <div class="stat-subtext">arXiv, GitHub, Hacker News, Reddit, RSS</div>
      </div>
    `;
    triggerCountUps(cards);

    recent.innerHTML = (overview.recent_intelligence || []).length
      ? overview.recent_intelligence
          .map(
            (a) => `
          <div class="item-card">
            <div class="item-title">${esc(a.title)}</div>
            <div class="item-meta">
              ${getSourceBadge(a.source)}
              <span class="badge gray">Relevance: ${esc(a.relevance_score)}</span>
            </div>
            <a class="item-link" href="${esc(a.url)}" target="_blank" rel="noopener">
              <span>Read article</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="7" y1="17" x2="17" y2="7"></line>
                <polyline points="7 7 17 7 17 17"></polyline>
              </svg>
            </a>
          </div>`
          )
          .join("")
      : emptyHtml("No intelligence collected yet. Trigger fresh research or verify background collector.");
  } catch (err) {
    cards.innerHTML = errorHtml(err.message);
  }
}
$("dashRefresh").onclick = loadDashboard;

// ------------------------------------------------------------------ AI Agent Chat View
const SUGGESTED_QUESTIONS = [
  "What are the current AI trends?",
  "What does our knowledge base say about AI trends?",
  "Search stored articles about LangGraph",
  "Run fresh research and summarize the results",
];

function renderSuggested() {
  $("suggested").innerHTML = SUGGESTED_QUESTIONS
    .map(
      (q) => `
    <button type="button" data-q="${esc(q)}">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <polyline points="12 16 16 12 12 8"></polyline>
        <line x1="8" y1="12" x2="16" y2="12"></line>
      </svg>
      <span>${esc(q)}</span>
    </button>`
    )
    .join("");

  $("suggested").querySelectorAll("button").forEach((b) => {
    b.onclick = () => {
      $("query").value = b.dataset.q;
      $("chatForm").requestSubmit();
    };
  });
}
renderSuggested();

// Format assistant text (paragraphs, bold, list items)
function formatAgentText(text) {
  if (!text) return "No response generated.";
  let lines = text.split("\n");
  let html = "";
  let inList = false;

  for (let line of lines) {
    let trimmed = line.trim();
    if (!trimmed) {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      continue;
    }

    let formatted = esc(trimmed).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${formatted.slice(2)}</li>`;
    } else {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      html += `<p>${formatted}</p>`;
    }
  }

  if (inList) html += "</ul>";
  return html;
}

// Add chat message row with avatars
function appendMessageRow(role, contentHtml) {
  // Remove welcome hero once conversation starts
  const welcome = $("chatWelcomeHero");
  if (welcome) welcome.remove();

  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = `msg-avatar ${role === "user" ? "user-avatar" : "agent-avatar"}`;

  if (role === "user") {
    avatar.textContent = (USER_EMAIL[0] || "U").toUpperCase();
  } else {
    avatar.innerHTML = `
      <svg class="radar-icon-svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.2" stroke-opacity="0.25" fill="none"></circle>
        <circle cx="12" cy="12" r="6" stroke="currentColor" stroke-width="1.2" stroke-opacity="0.35" class="radar-concentric-pulse" fill="none"></circle>
        <g class="radar-sweep-beam">
          <path d="M12 2a10 10 0 0 1 10 10" stroke-width="2.4" stroke="currentColor" fill="none"></path>
          <line x1="12" y1="12" x2="22" y2="12" stroke="currentColor" stroke-width="1.8"></line>
        </g>
        <circle cx="12" cy="12" r="2.5" fill="currentColor"></circle>
      </svg>`;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "msg-content-wrapper";
  wrapper.innerHTML = contentHtml;

  row.appendChild(avatar);
  row.appendChild(wrapper);

  $("messages").appendChild(row);
  $("messages").scrollTop = $("messages").scrollHeight;
  return row;
}

// Add typing/thinking indicator
function showTypingIndicator() {
  const row = document.createElement("div");
  row.className = "msg-row agent";
  row.id = "typingIndicator";

  const avatar = document.createElement("div");
  avatar.className = "msg-avatar agent-avatar";
  avatar.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="10"></circle>
      <polyline points="12 6 12 12 16 14"></polyline>
    </svg>`;

  const indicator = document.createElement("div");
  indicator.className = "typing-indicator";
  indicator.innerHTML = `
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <span class="typing-text">Evaluating stored evidence &amp; agent tools...</span>
  `;

  row.appendChild(avatar);
  row.appendChild(indicator);
  $("messages").appendChild(row);
  $("messages").scrollTop = $("messages").scrollHeight;
  return row;
}

function removeTypingIndicator() {
  const el = $("typingIndicator");
  if (el) el.remove();
}

// Submit chat query
$("chatForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("query").value.trim();
  if (!q) return;

  $("query").value = "";
  // Render user message
  appendMessageRow("user", `<div class="msg-bubble">${esc(q)}</div>`);

  // Show typing indicator
  showTypingIndicator();
  $("send").disabled = true;

  try {
    const data = await api("/chat", { method: "POST", body: { query: q } });
    removeTypingIndicator();

    let bubbleContent = formatAgentText(data.answer);

    // Build tool calls tag
    let toolBadge = "";
    if (data.tool_calls > 0) {
      toolBadge = `
        <div class="tool-call-pill">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
            <polyline points="17 6 23 6 23 12"></polyline>
          </svg>
          <span>${data.tool_calls} tool call(s) executed</span>
        </div>`;
    }

    // Build grounded sources
    let sourcesContent = "";
    if (data.sources && data.sources.length) {
      sourcesContent = `
        <div class="msg-sources-card">
          <div class="msg-sources-title">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
            </svg>
            Grounded Reference Sources
          </div>
          <div class="msg-sources-list">
            ${data.sources
              .map(
                (s) => `
              <a class="source-chip" href="${esc(s)}" target="_blank" rel="noopener">
                <span>${esc(s)}</span>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="7" y1="17" x2="17" y2="7"></line>
                  <polyline points="7 7 17 7 17 17"></polyline>
                </svg>
              </a>`
              )
              .join("")}
          </div>
        </div>`;
    }

    const fullContentHtml = `
      <div class="msg-bubble">
        ${bubbleContent}
        ${sourcesContent}
      </div>
      ${toolBadge}
    `;

    appendMessageRow("agent", fullContentHtml);
  } catch (err) {
    removeTypingIndicator();

    // Graceful error state card
    const errorCardHtml = `
      <div class="agent-error-card">
        <div class="agent-error-header">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>AI Agent Temporarily Unavailable</span>
        </div>
        <div class="agent-error-body">
          The agent could not complete this request. The backend LLM provider is currently unconfigured or unreachable.
        </div>
        <div class="agent-error-details">
          ${esc(err.message)}
        </div>
        <div style="margin-top: 4px;">
          <button class="btn ghost small" style="background: var(--bg-card); border-color: rgba(225,29,72,0.3);" onclick="retryQuery('${esc(q)}')">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="23 4 23 10 17 10"></polyline>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
            </svg>
            <span>Retry Prompt</span>
          </button>
        </div>
      </div>
    `;

    appendMessageRow("agent", errorCardHtml);
  } finally {
    $("send").disabled = false;
  }
});

window.retryQuery = function (text) {
  $("query").value = text;
  $("chatForm").requestSubmit();
};

$("clearChat").onclick = () => {
  $("messages").innerHTML = `
    <div class="chat-welcome-hero" id="chatWelcomeHero">
      <div class="chat-welcome-icon" title="Multi-Source Signal Radar">
        <svg class="radar-icon-svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.2" stroke-opacity="0.25" fill="none"></circle>
          <circle cx="12" cy="12" r="6" stroke="currentColor" stroke-width="1.2" stroke-opacity="0.35" class="radar-concentric-pulse" fill="none"></circle>
          <g class="radar-sweep-beam">
            <path d="M12 2a10 10 0 0 1 10 10" stroke-width="2.4" stroke="currentColor" fill="none"></path>
            <line x1="12" y1="12" x2="22" y2="12" stroke="currentColor" stroke-width="1.8"></line>
            <polygon points="12,12 22,12 19,5" fill="currentColor" fill-opacity="0.16" stroke="none"></polygon>
          </g>
          <circle cx="12" cy="12" r="2.5" fill="currentColor"></circle>
        </svg>
      </div>
      <h3>AI Intelligence Platform Assistant</h3>
      <p>I can autonomously search stored articles, examine emerging trend velocity, retrieve grounded knowledge from the local RAG store, or run fresh multi-source research.</p>
    </div>
  `;
};

// ------------------------------------------------------------------ Intelligence Feed
async function loadIntelligence() {
  const box = $("articles");
  box.innerHTML = loadingHtml("Loading intelligence feed...");
  try {
    const rows = await api("/intelligence/articles?limit=30");
    box.innerHTML = rows.length
      ? rows
          .map(
            (a) => `
        <div class="card item-card">
          <div class="item-title">${esc(a.title)}</div>
          <div class="item-meta">
            ${getSourceBadge(a.source)}
            <span class="badge gray">Score: ${esc(a.relevance_score)}</span>
          </div>
          <a class="item-link" href="${esc(a.url)}" target="_blank" rel="noopener">
            <span>Read source article</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="7" y1="17" x2="17" y2="7"></line>
              <polyline points="7 7 17 7 17 17"></polyline>
            </svg>
          </a>
        </div>`
          )
          .join("")
      : emptyHtml("No articles collected yet. Trigger a research run or verify collector settings.");
  } catch (err) {
    box.innerHTML = errorHtml(err.message);
  }
}
$("intelRefresh").onclick = loadIntelligence;

// ------------------------------------------------------------------ Trends View
let trendsPollTimer = null;

async function loadTrendsView() {
  await Promise.all([loadTrends(), loadTrendsStatus()]);
  clearInterval(trendsPollTimer);
  trendsPollTimer = setInterval(loadTrendsStatus, 30_000);
}

async function loadTrends() {
  const box = $("trendList");
  box.innerHTML = loadingHtml("Analyzing and ranking topic clusters...");
  try {
    const rows = await api("/trends");
    box.innerHTML = rows.length
      ? rows.map((t, i) => trendCardHtml(t, i)).join("")
      : emptyHtml(
          "No trends detected yet. Trends appear once fresh research has been clustered — you can trigger it now from the AI Agent tab."
        );
  } catch (err) {
    box.innerHTML = errorHtml(err.message);
  }
}
$("trendsRefresh").onclick = loadTrendsView;

// Trend Card with 0-100 Score, Visual Progress Bar, Source Diversity, and Explanations
function trendCardHtml(t, index) {
  // Parse 0-100 score from explanation string
  const desc = t.description || "";
  let score = 50;
  const scoreMatch = desc.match(/trend strength=([\d.]+)\/100/i);
  if (scoreMatch) {
    score = parseFloat(scoreMatch[1]);
  }

  // Determine score severity level
  let level = "low";
  let label = "Emerging Signal";
  if (score >= 70) {
    level = "high";
    label = "High Velocity";
  } else if (score >= 40) {
    level = "medium";
    label = "Active Trend";
  }

  // Parse source diversity & signals
  const articles = t.articles || [];
  const uniqueSources = [...new Set(articles.map((a) => a.source).filter(Boolean))];
  const sourceBadges = uniqueSources.length
    ? uniqueSources.map((s) => getSourceBadge(s)).join(" ")
    : '<span class="badge gray">Multi-Source</span>';

  // Format articles list
  const articlesHtml = articles
    .map(
      (a) => `
    <div class="trend-article-item">
      <div class="trend-article-left">
        ${getSourceBadge(a.source)}
        <a class="trend-article-title" href="${esc(a.url)}" target="_blank" rel="noopener" title="${esc(a.title)}">
          ${esc(a.title)}
        </a>
      </div>
      <div class="trend-article-date">${esc(fmtDate(a.published_at))}</div>
    </div>`
    )
    .join("");

  const articlesContainerId = `trend-arts-${index}`;

  return `
    <div class="card trend-card">
      <div class="trend-card-top">
        <div class="trend-title-group">
          <h3 class="trend-title">${esc(t.name)}</h3>
          <span class="badge ${level === "high" ? "emerald" : level === "medium" ? "amber" : "teal"}">
            ${esc(t.article_count)} article${t.article_count === 1 ? "" : "s"}
          </span>
          <span class="badge gray">First: ${esc(fmtDate(t.first_seen_at))} &middot; Last: ${esc(fmtDate(t.last_seen_at))}</span>
        </div>

        <!-- 0-100 Score Badge -->
        <div class="score-badge ${level}">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
            <polyline points="17 6 23 6 23 12"></polyline>
          </svg>
          <span>Score: ${score.toFixed(1)}/100 &middot; ${label}</span>
        </div>
      </div>

      <!-- Visual Progress Meter -->
      <div class="trend-progress-track">
        <div class="trend-progress-bar ${level}" style="width: ${Math.min(100, Math.max(8, score))}%;"></div>
      </div>

      <!-- Human-readable Explanation -->
      <div class="trend-explanation">
        <strong>Signal Analysis:</strong> ${esc(desc || "Automated cluster analysis.")}
      </div>

      <!-- Source Diversity Chips -->
      <div class="trend-diversity-group">
        <span class="trend-diversity-label">Contributing Sources:</span>
        ${sourceBadges}
      </div>

      <!-- Collapsible Articles -->
      ${
        articles.length
          ? `
      <div class="trend-articles-container">
        <button class="trend-articles-toggle" onclick="toggleTrendArticles('${articlesContainerId}', this)">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
          <span>Show ${articles.length} Supporting Articles</span>
        </button>
        <div id="${articlesContainerId}" class="trend-articles-list" style="display: none;">
          ${articlesHtml}
        </div>
      </div>`
          : ""
      }
    </div>`;
}

window.toggleTrendArticles = function (id, btn) {
  const el = $(id);
  if (!el) return;
  const isHidden = el.style.display === "none";
  el.style.display = isHidden ? "flex" : "none";
  btn.querySelector("span").textContent = isHidden ? "Hide Supporting Articles" : "Show Supporting Articles";
  btn.querySelector("svg").style.transform = isHidden ? "rotate(180deg)" : "none";
};

async function loadTrendsStatus() {
  const el = $("trendsStatus");
  try {
    const s = await api("/trends/status");
    if (!s.scheduler_enabled) {
      el.textContent = "Automatic background scheduler is disabled in settings.";
      return;
    }
    const parts = [`Auto-collecting every ${s.collection_interval_minutes} min`];
    if (s.status === "running") {
      parts.push("Collection in progress\u2026");
    } else if (s.finished_at) {
      parts.push(`Last run: ${fmtDateTime(s.finished_at)} (${s.status === "ok" ? `${s.persisted_articles} article(s) stored` : "run failed"})`);
    }
    if (s.next_run_at) parts.push(`Next run: ${fmtDateTime(s.next_run_at)}`);
    el.textContent = parts.join(" \u00b7 ");
  } catch (_) {
    el.textContent = "";
  }
}

// ------------------------------------------------------------------ Knowledge Base / RAG View
$("rebuildKb").onclick = async () => {
  const status = $("kbStatus");
  $("rebuildKb").disabled = true;
  status.textContent = "Rebuilding TF-IDF vector index and chunk mappings...";
  try {
    const res = await api("/knowledge/rebuild", { method: "POST" });
    status.innerHTML = `<span style="color: var(--success); font-weight: 600;">✓ Indexed ${res.indexed_articles} article(s) into ${res.indexed_chunks} chunks.</span>`;
  } catch (err) {
    status.innerHTML = `<span style="color: var(--danger); font-weight: 600;">✗ Failed: ${esc(err.message)}</span>`;
  } finally {
    $("rebuildKb").disabled = false;
  }
};

$("ragForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = $("ragQuery").value.trim();
  if (!query) return;

  const box = $("ragResults");
  box.innerHTML = loadingHtml("Searching vector knowledge base and computing cosine similarities...");
  try {
    const res = await api("/rag/search", { method: "POST", body: { query, limit: 8 } });
    box.innerHTML = res.results && res.results.length
      ? res.results
          .map(
            (r) => `
        <div class="rag-chunk-card">
          <div class="rag-chunk-header">
            <div style="font-weight: 700; font-size: 15px; color: var(--text-main);">
              ${esc(r.title)}
            </div>
            <div class="score-badge ${r.score >= 0.5 ? "high" : r.score >= 0.2 ? "medium" : "low"}">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
              <span>Match: ${(r.score * 100).toFixed(1)}%</span>
            </div>
          </div>
          
          <div class="rag-chunk-meta">
            ${getSourceBadge(r.source)}
            ${r.category ? `<span class="badge teal">${esc(r.category)}</span>` : ""}
            <span class="badge gray">Chunk ID: ${esc(r.id || "chunk")}</span>
            <span class="muted" style="font-size: 12px; margin-left: auto;">${esc(fmtDate(r.published_at))}</span>
          </div>

          <div class="rag-chunk-text">${esc(r.text || "No text available for this chunk.")}</div>

          <a class="item-link" href="${esc(r.url)}" target="_blank" rel="noopener">
            <span>View source publication</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="7" y1="17" x2="17" y2="7"></line>
              <polyline points="7 7 17 7 17 17"></polyline>
            </svg>
          </a>
        </div>`
          )
          .join("")
      : emptyHtml("No matching knowledge base passages found. Try rebuilding the index or using broader search terms.");
  } catch (err) {
    box.innerHTML = errorHtml(err.message);
  }
});

// ------------------------------------------------------------------ Analytics View
async function loadAnalytics() {
  const box = $("analyticsBox");
  box.innerHTML = loadingHtml("Compiling platform analytics and distribution charts...");

  try {
    const a = await api("/analytics/overview");
    const totalArticles = a.total_articles || 1;

    // Visual bar charts for Sources
    const sourceEntries = Object.entries(a.sources || {}).sort((x, y) => y[1] - x[1]);
    const sourceChartHtml = sourceEntries.length
      ? sourceEntries
          .map(([source, count]) => {
            const pct = Math.round((count / totalArticles) * 100);
            return `
          <div class="bar-chart-row">
            <div class="bar-chart-info">
              <span class="bar-chart-label">${getSourceBadge(source)}</span>
              <span class="bar-chart-count">${count} items (${pct}%)</span>
            </div>
            <div class="bar-chart-track">
              <div class="bar-chart-fill" style="width: ${pct}%; background: linear-gradient(90deg, #0d9488, #06b6d4);"></div>
            </div>
          </div>`;
          })
          .join("")
      : '<p class="muted">No sources recorded yet.</p>';

    // Visual bar charts for Categories
    const categoryEntries = Object.entries(a.categories || {}).sort((x, y) => y[1] - x[1]);
    const categoryChartHtml = categoryEntries.length
      ? categoryEntries
          .map(([category, count]) => {
            const pct = Math.round((count / totalArticles) * 100);
            return `
          <div class="bar-chart-row">
            <div class="bar-chart-info">
              <span class="bar-chart-label"><span class="badge teal">${esc(category)}</span></span>
              <span class="bar-chart-count">${count} items (${pct}%)</span>
            </div>
            <div class="bar-chart-track">
              <div class="bar-chart-fill" style="width: ${pct}%; background: linear-gradient(90deg, #10b981, #06b6d4);"></div>
            </div>
          </div>`;
          })
          .join("")
      : '<p class="muted">No categories assigned yet.</p>';

    box.innerHTML = `
      <!-- KPI Cards -->
      <div class="card stat-card">
        <div class="stat-header">
          <span class="stat-label">Total Articles</span>
          <div class="stat-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
              <line x1="8" y1="21" x2="16" y2="21"></line>
              <line x1="12" y1="17" x2="12" y2="21"></line>
            </svg>
          </div>
        </div>
        <div class="stat-value count-up-val" data-target="${a.total_articles || 0}">${esc(a.total_articles)}</div>
        <div class="stat-subtext">Articles indexed in PostgreSQL</div>
      </div>

      <div class="card stat-card">
        <div class="stat-header">
          <span class="stat-label">Identified Topics</span>
          <div class="stat-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
          </div>
        </div>
        <div class="stat-value count-up-val" data-target="${a.total_topics || 0}">${esc(a.total_topics)}</div>
        <div class="stat-subtext">Emerging trend clusters</div>
      </div>

      <div class="card stat-card">
        <div class="stat-header">
          <span class="stat-label">Average Quality</span>
          <div class="stat-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
            </svg>
          </div>
        </div>
        <div class="stat-value count-up-val" data-target="${a.average_relevance || 0}" data-decimals="2">${esc(a.average_relevance)}</div>
        <div class="stat-subtext">Calculated relevance index</div>
      </div>

      <!-- Charts Section -->
      <div style="grid-column: 1 / -1;" class="chart-panel-grid">
        <div class="visual-chart-card">
          <div class="visual-chart-header">
            <div class="visual-chart-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 11a9 9 0 0 1 9 9"></path>
                <path d="M4 4a16 16 0 0 1 16 16"></path>
                <circle cx="5" cy="19" r="1"></circle>
              </svg>
              <span>Sources Distribution</span>
            </div>
            <span class="badge gray">${sourceEntries.length} Active Feeds</span>
          </div>
          ${sourceChartHtml}
        </div>

        <div class="visual-chart-card">
          <div class="visual-chart-header">
            <div class="visual-chart-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
              <span>Topic Categories Breakdown</span>
            </div>
            <span class="badge teal">${categoryEntries.length} Categories</span>
          </div>
          ${categoryChartHtml}
        </div>
      </div>
    `;
    triggerCountUps(box);
  } catch (err) {
    box.innerHTML = errorHtml(err.message);
  }
}
$("analyticsRefresh").onclick = loadAnalytics;

// ------------------------------------------------------------------ Faint Animated Knowledge Graph Background
function initKnowledgeGraph() {
  const canvas = $("graphCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  let width = 0;
  let height = 0;
  let dpr = window.devicePixelRatio || 1;
  let nodes = [];
  const NODE_COUNT = 38;
  const MAX_DIST = 145;

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
  }

  function createNodes() {
    nodes = [];
    for (let i = 0; i < NODE_COUNT; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.32,
        vy: (Math.random() - 0.5) * 0.32,
        radius: Math.random() * 1.5 + 1.2,
        pulse: Math.random() * Math.PI * 2,
        pulseSpeed: 0.015 + Math.random() * 0.02,
        isAccent: Math.random() > 0.65
      });
    }
  }

  window.addEventListener("resize", () => {
    resize();
    createNodes();
  });

  resize();
  createNodes();

  function draw() {
    if (document.hidden) {
      requestAnimationFrame(draw);
      return;
    }

    ctx.clearRect(0, 0, width, height);
    const theme = document.documentElement.getAttribute("data-theme") || "light";
    const isDark = theme === "dark";

    // Colors: subtle teal/cyan in dark mode, soft slate/teal in light mode
    const baseNodeColor = isDark ? "45, 212, 191" : "148, 163, 184";
    const accentNodeColor = isDark ? "34, 211, 238" : "13, 148, 136";
    const lineColor = isDark ? "20, 184, 166" : "203, 213, 225";

    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      n.x += n.vx;
      n.y += n.vy;
      n.pulse += n.pulseSpeed;

      if (n.x < -20) n.x = width + 20;
      else if (n.x > width + 20) n.x = -20;
      if (n.y < -20) n.y = height + 20;
      else if (n.y > height + 20) n.y = -20;

      const currentRadius = n.radius + Math.sin(n.pulse) * 0.45;
      const rgb = n.isAccent ? accentNodeColor : baseNodeColor;
      const alpha = isDark ? (n.isAccent ? 0.48 : 0.32) : (n.isAccent ? 0.38 : 0.26);

      ctx.beginPath();
      ctx.arc(n.x, n.y, Math.max(0.6, currentRadius), 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${rgb}, ${alpha})`;
      ctx.fill();

      for (let j = i + 1; j < nodes.length; j++) {
        const n2 = nodes[j];
        const dx = n.x - n2.x;
        const dy = n.y - n2.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < MAX_DIST) {
          const lineAlpha = (1 - dist / MAX_DIST) * (isDark ? 0.20 : 0.16);
          ctx.beginPath();
          ctx.moveTo(n.x, n.y);
          ctx.lineTo(n2.x, n2.y);
          ctx.strokeStyle = `rgba(${lineColor}, ${lineAlpha})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    }

    requestAnimationFrame(draw);
  }

  draw();
}

// ------------------------------------------------------------------ Initial App Boot
(async function boot() {
  initTheme();
  initKnowledgeGraph();
  setAuthMode("login");
  setAuthLoading(false);
  hideAuthMsg();
  if (TOKEN) {
    try {
      await afterLogin();
      return;
    } catch (_) {
      logout();
    }
  }
  $("auth").hidden = false;
  $("auth").style.display = "flex";
  $("shell").hidden = true;
  $("shell").style.display = "none";
})();
