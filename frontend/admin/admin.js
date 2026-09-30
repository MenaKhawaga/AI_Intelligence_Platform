"use strict";


/* =========================
   API
========================= */

const API_BASE = window.location.origin;

const TOKEN_KEY = "aip_token";
const USER_EMAIL_KEY = "aip_email";


async function api(path, options = {}) {

    const token = localStorage.getItem(TOKEN_KEY);

    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(
        `${API_BASE}${path}`,
        {
            ...options,
            headers
        }
    );

    if (response.status === 401) {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_EMAIL_KEY);

        window.location.href = "../index.html";

        throw new Error("Authentication required");
    }

    if (response.status === 403) {
        throw new Error("Admin access required");
    }

    if (!response.ok) {

        let message = `Request failed: ${response.status}`;

        try {
            const data = await response.json();

            if (data.detail) {
                message = data.detail;
            }

        } catch (_) {
            // Keep default error message
        }

        throw new Error(message);
    }

    return response.json();
}


/* =========================
   Helpers
========================= */

function esc(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatDate(value) {

    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString();
}


function formatNumber(value) {

    const number = Number(value || 0);

    return number.toLocaleString();
}


/* =========================
   Theme
========================= */

const THEME_KEY = "aip_theme";


function applyTheme(theme) {

    document.documentElement.dataset.theme = theme;

    localStorage.setItem(THEME_KEY, theme);
}


function loadTheme() {

    const savedTheme = localStorage.getItem(THEME_KEY);

    if (savedTheme === "dark" || savedTheme === "light") {
        applyTheme(savedTheme);
        return;
    }

    const prefersDark =
        window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: dark)").matches;

    applyTheme(prefersDark ? "dark" : "light");
}


function setupTheme() {

    const button = document.getElementById("themeToggle");

    if (!button) {
        return;
    }

    button.addEventListener("click", () => {

        const current =
            document.documentElement.dataset.theme || "light";

        applyTheme(
            current === "dark"
                ? "light"
                : "dark"
        );
    });
}


/* =========================
   Admin User
========================= */

function setupAdminUser() {

    const email =
        localStorage.getItem(USER_EMAIL_KEY);

    const emailElement =
        document.getElementById("adminEmail");

    const avatarElement =
        document.getElementById("adminAvatar");

    if (emailElement) {
        emailElement.textContent =
            email || "Administrator";
    }

    if (avatarElement) {

        const firstLetter =
            email
                ? email.charAt(0).toUpperCase()
                : "A";

        avatarElement.textContent = firstLetter;
    }
}


/* =========================
   Logout
========================= */

function setupLogout() {

    const button =
        document.getElementById("logoutBtn");

    if (!button) {
        return;
    }

    button.addEventListener("click", () => {

        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_EMAIL_KEY);

        window.location.href = "../index.html";
    });
}

/* =========================
   Open User Platform
========================= */

function setupOpenUserPlatform() {

    const button =
        document.getElementById("openUserPlatform");

    if (!button) {
        return;
    }

    button.addEventListener("click", () => {

        sessionStorage.setItem(
            "aip_user_mode",
            "true"
        );

        window.location.href = `${API_BASE}/`;
    });
}


/* =========================
   Navigation
========================= */

function showAdminView(viewName) {

    document
        .querySelectorAll(".admin-view")
        .forEach(view => {

            view.classList.toggle(
                "active",
                view.id === `admin-view-${viewName}`
            );

        });


    document
        .querySelectorAll(".admin-nav-btn")
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.adminView === viewName
            );

        });


    loadAdminView(viewName);
}


function setupNavigation() {

    document
        .querySelectorAll(".admin-nav-btn")
        .forEach(button => {

            button.addEventListener("click", () => {

                showAdminView(
                    button.dataset.adminView
                );

            });

        });


    document
        .querySelectorAll("[data-admin-view-link]")
        .forEach(button => {

            button.addEventListener("click", () => {

                showAdminView(
                    button.dataset.adminViewLink
                );

            });

        });
}


/* =========================
   Overview
========================= */

async function loadStats() {

    const data =
        await api("/admin/stats");


    document.getElementById("statUsers").textContent =
        formatNumber(data.total_users);


    document.getElementById("statArticles").textContent =
        formatNumber(data.total_articles);


    document.getElementById("statTopics").textContent =
        formatNumber(data.total_topics);


    document.getElementById("statActivities").textContent =
        formatNumber(data.total_agent_activities);
}


async function loadOverviewArticles() {

    const container =
        document.getElementById("overviewArticles");

    try {

        const data =
            await api("/intelligence/articles?limit=5");

        const articles =
            Array.isArray(data)
                ? data
                : data.items || data.articles || [];


        if (!articles.length) {

            container.innerHTML =
                `<div class="empty-state">
                    No intelligence articles found.
                </div>`;

            return;
        }


        container.innerHTML =
            articles.map(article => {

                return `
                    <div class="overview-item">

                        <div class="overview-title">
                            ${esc(article.title)}
                        </div>

                        <div class="overview-meta">
                            ${esc(article.source || "Unknown source")}
                            ·
                            ${formatDate(article.published_at)}
                        </div>

                    </div>
                `;

            }).join("");

    } catch (error) {

        container.innerHTML =
            `<div class="empty-state">
                ${esc(error.message)}
            </div>`;
    }
}


async function loadOverviewActivity() {

    const container =
        document.getElementById("overviewActivity");

    try {

        const activities =
            await api("/admin/agent-activity");


        if (!activities.length) {

            container.innerHTML =
                `<div class="empty-state">
                    No agent activity has been recorded yet.
                </div>`;

            return;
        }


        container.innerHTML =
            activities.slice(0, 5).map(activity => {

                return `
                    <div class="overview-item">

                        <div class="overview-query">
                            ${esc(activity.query)}
                        </div>

                        <div class="overview-meta">
                            User #${esc(activity.user_id)}
                            ·
                            ${formatDate(activity.created_at)}
                        </div>

                    </div>
                `;

            }).join("");

    } catch (error) {

        container.innerHTML =
            `<div class="empty-state">
                ${esc(error.message)}
            </div>`;
    }
}


async function loadOverview() {

    try {
        await loadStats();
    } catch (error) {

        console.error(
            "Failed to load admin stats:",
            error
        );
    }

    await Promise.all([
        loadOverviewArticles(),
        loadOverviewActivity()
    ]);
}


/* =========================
   Users
========================= */

async function loadUsers() {

    const tbody =
        document.getElementById("usersTableBody");

    const count =
        document.getElementById("usersCount");


    try {

        const users =
            await api("/admin/users");


        count.textContent =
            `${users.length} user${users.length === 1 ? "" : "s"}`;


        if (!users.length) {

            tbody.innerHTML =
                `<tr>
                    <td colspan="5" class="table-empty">
                        No users found.
                    </td>
                </tr>`;

            return;
        }


        tbody.innerHTML =
            users.map(user => {

                return `
                    <tr>

                        <td>
                            ${esc(user.id)}
                        </td>

                        <td>
                            ${esc(user.email)}
                        </td>

                        <td>
                            ${
                                user.active
                                    ? `<span class="admin-badge badge-active">
                                            Active
                                       </span>`
                                    : `<span class="admin-badge badge-inactive">
                                            Inactive
                                       </span>`
                            }
                        </td>

                        <td>
                            ${
                                user.is_admin
                                    ? `<span class="admin-badge badge-admin">
                                            Admin
                                       </span>`
                                    : "User"
                            }
                        </td>

                        <td>
                            ${formatDate(user.created_at)}
                        </td>

                    </tr>
                `;

            }).join("");

    } catch (error) {

        tbody.innerHTML =
            `<tr>
                <td colspan="5" class="table-empty">
                    ${esc(error.message)}
                </td>
            </tr>`;
    }
}


/* =========================
   Articles
========================= */

async function loadArticles() {

    const tbody =
        document.getElementById("articlesTableBody");

    const count =
        document.getElementById("articlesCount");


    try {

        const data =
            await api("/intelligence/articles?limit=100");


        const articles =
            Array.isArray(data)
                ? data
                : data.items || data.articles || [];


        count.textContent =
            `${articles.length} article${articles.length === 1 ? "" : "s"}`;


        if (!articles.length) {

            tbody.innerHTML =
                `<tr>
                    <td colspan="6" class="table-empty">
                        No articles found.
                    </td>
                </tr>`;

            return;
        }


        tbody.innerHTML =
            articles.map(article => {

                return `
                    <tr>

                        <td>
                            ${esc(article.id ?? "—")}
                        </td>

                        <td>
                            <div class="table-title">
                                ${esc(article.title)}
                            </div>
                        </td>

                        <td>
                            ${esc(article.source || "—")}
                        </td>

                        <td>
                            ${esc(
                                article.primary_category ||
                                article.category ||
                                "—"
                            )}
                        </td>

                        <td>
                            ${esc(
                                article.relevance_score ??
                                article.score ??
                                "—"
                            )}
                        </td>

                        <td>
                            ${formatDate(article.published_at)}
                        </td>

                    </tr>
                `;

            }).join("");

    } catch (error) {

        tbody.innerHTML =
            `<tr>
                <td colspan="6" class="table-empty">
                    ${esc(error.message)}
                </td>
            </tr>`;
    }
}


/* =========================
   Sources
========================= */


async function loadSources() {

    const container =
        document.getElementById("sourcesGrid");

    const count =
        document.getElementById("sourcesCount");

    try {

        const sources =
            await api("/admin/sources");

        count.textContent =
            `${sources.length} source${sources.length === 1 ? "" : "s"}`;

        if (!sources.length) {

            container.innerHTML =
                `<div class="empty-state">
                    No sources found.
                </div>`;

            return;
        }

        container.innerHTML =
            sources.map(source => {

                return `
                    <div class="source-card">

                        <div class="source-name">
                            ${esc(source.name)}
                        </div>

                        <div class="source-count">
                            ${esc(source.source_type || "Unknown type")}
                        </div>

                        <div class="source-url">
                            ${esc(source.url || "—")}
                        </div>

                        <div class="source-status">
                            ${
                                source.is_active
                                    ? `<span class="admin-badge badge-active">
                                            Active
                                       </span>`
                                    : `<span class="admin-badge badge-inactive">
                                            Inactive
                                       </span>`
                            }
                        </div>

                    </div>
                `;

            }).join("");

    } catch (error) {

        container.innerHTML =
            `<div class="empty-state">
                ${esc(error.message)}
            </div>`;
    }
}

/* =========================
   Topics
========================= */
async function loadTopics() {
    const container = document.getElementById("topicsGrid");
    const count = document.getElementById("topicsCount");

    try {
        const topics = await api("/trends");

        count.textContent =
            `${topics.length} topic${topics.length === 1 ? "" : "s"}`;

        if (!topics.length) {
            container.innerHTML = `
                <div class="empty-state">
                    No topics found.
                </div>
            `;
            return;
        }

        container.innerHTML = topics.map(topic => {
            const description = topic.description || "";

            // Extract values already returned by the existing API description.
            const scoreMatch =
                description.match(/trend strength\s*=\s*([\d.]+)\s*\/\s*100/i);

            const recentMatch =
                description.match(/recent activity\s*=\s*(\d+)/i);

            const baselineMatch =
                description.match(/baseline activity\s*=\s*(\d+)/i);

            const relatedMatch =
                description.match(/([\d,]+)\s+related item/i);

            const sourcesMatch =
                description.match(/across\s+(\d+)\s+source/i);

            const score = scoreMatch
                ? Number(scoreMatch[1])
                : 0;

            const recentActivity = recentMatch
                ? recentMatch[1]
                : "—";

            const baselineActivity = baselineMatch
                ? baselineMatch[1]
                : "—";

            const relatedItems = relatedMatch
                ? relatedMatch[1]
                : "—";

            const sourceCount = sourcesMatch
                ? sourcesMatch[1]
                : "—";

            let scoreClass = "low";

            if (score >= 70) {
                scoreClass = "high";
            } else if (score >= 40) {
                scoreClass = "medium";
            }

            return `
                <article class="admin-topic-card">

                    <div class="admin-topic-header">

                        <div class="admin-topic-title-group">
                            <h3 class="admin-topic-title">
                                ${esc(topic.name)}
                            </h3>

                            <span class="admin-topic-count">
                                ${formatNumber(topic.article_count || 0)}
                                article${topic.article_count === 1 ? "" : "s"}
                            </span>
                        </div>

                        <div class="admin-topic-score ${scoreClass}">
                            ${score.toFixed(2)}
                            <span>/ 100</span>
                        </div>

                    </div>

                    <div class="admin-topic-progress">
                        <div
                            class="admin-topic-progress-bar ${scoreClass}"
                            style="width: ${Math.min(Math.max(score, 0), 100)}%;"
                        ></div>
                    </div>

                    <div class="admin-topic-metrics">

                        <div class="admin-topic-metric">
                            <span class="admin-topic-metric-label">
                                Recent activity
                            </span>
                            <strong>
                                ${recentActivity}
                            </strong>
                        </div>

                        <div class="admin-topic-metric">
                            <span class="admin-topic-metric-label">
                                Baseline activity
                            </span>
                            <strong>
                                ${baselineActivity}
                            </strong>
                        </div>

                        <div class="admin-topic-metric">
                            <span class="admin-topic-metric-label">
                                Related items
                            </span>
                            <strong>
                                ${relatedItems}
                            </strong>
                        </div>

                        <div class="admin-topic-metric">
                            <span class="admin-topic-metric-label">
                                Sources
                            </span>
                            <strong>
                                ${sourceCount}
                            </strong>
                        </div>

                    </div>

                    <div class="admin-topic-description">
                        ${esc(description)}
                    </div>

                </article>
            `;
        }).join("");

    } catch (error) {
        container.innerHTML = `
            <div class="empty-state">
                ${esc(error.message)}
            </div>
        `;
    }
}


/* =========================
   Summaries
========================= */
async function loadSummaries() {
    const container = document.getElementById("summariesTableBody");
    const count = document.getElementById("summariesCount");

    try {
        const summaries = await api("/admin/summaries");

        count.textContent =
            `${summaries.length} ${summaries.length === 1 ? "summary" : "summaries"}`;

        if (!summaries.length) {
            container.innerHTML = `
                <tr>
                    <td colspan="5" class="table-empty">
                        No summaries found.
                    </td>
                </tr>
            `;
            return;
        }

        container.innerHTML = summaries.map(summary => `
            <tr>
                <td>${summary.id}</td>
                <td>${summary.article_id}</td>
                <td>${esc(summary.headline)}</td>
                <td>${esc(summary.why_it_matters)}</td>
                <td>${formatDate(summary.generated_at)}</td>
            </tr>
        `).join("");

    } catch (error) {
        console.error("Failed to load summaries:", error);

        count.textContent = "0 summaries";

        container.innerHTML = `
            <tr>
                <td colspan="5" class="table-empty">
                    Failed to load summaries.
                </td>
            </tr>
        `;
    }
}


/* =========================
   Agent Activity
========================= */

async function loadActivity() {

    const tbody =
        document.getElementById("activityTableBody");

    const count =
        document.getElementById("activityCount");


    try {

        const activities =
            await api("/admin/agent-activity");


        count.textContent =
            `${activities.length} activit${activities.length === 1 ? "y" : "ies"}`;


        if (!activities.length) {

            tbody.innerHTML =
                `<tr>
                    <td colspan="6" class="table-empty">
                        No agent activity has been recorded yet.
                    </td>
                </tr>`;

            return;
        }


        tbody.innerHTML =
            activities.map(activity => {

                const tools =
                    Array.isArray(activity.tools_used)
                        ? activity.tools_used.join(", ")
                        : activity.tools_used || "—";


                return `
                    <tr>

                        <td>
                            ${esc(activity.id)}
                        </td>

                        <td>
                            #${esc(activity.user_id)}
                        </td>

                        <td>
                            <div class="table-query">
                                ${esc(activity.query)}
                            </div>
                        </td>

                        <td>
                            ${esc(tools)}
                        </td>

                        <td>
                            ${
                                activity.success
                                    ? `<span class="admin-badge badge-success">
                                            Success
                                       </span>`
                                    : `<span class="admin-badge badge-failed">
                                            Failed
                                       </span>`
                            }
                        </td>

                        <td>
                            ${formatDate(activity.created_at)}
                        </td>

                    </tr>
                `;

            }).join("");

    } catch (error) {

        tbody.innerHTML =
            `<tr>
                <td colspan="6" class="table-empty">
                    ${esc(error.message)}
                </td>
            </tr>`;
    }
}


/* =========================
   View Loader
========================= */

const loadedViews = new Set();


async function loadAdminView(viewName) {

    if (loadedViews.has(viewName)) {
        return;
    }


    switch (viewName) {

        case "overview":
            await loadOverview();
            break;

        case "users":
            await loadUsers();
            break;

        case "articles":
            await loadArticles();
            break;

        case "sources":
            await loadSources();
            break;

        case "topics":
            await loadTopics();
            break;

        case "summaries":
            loadSummaries();
            break;

        case "activity":
            await loadActivity();
            break;
    }


    loadedViews.add(viewName);
}


/* =========================
   Refresh
========================= */

function setupRefresh() {

    const button =
        document.getElementById("refreshOverviewBtn");

    if (!button) {
        return;
    }


    button.addEventListener("click", async () => {

        loadedViews.delete("overview");

        button.disabled = true;

        button.textContent = "Refreshing...";


        await loadOverview();


        loadedViews.add("overview");

        button.disabled = false;

        button.textContent = "Refresh";
    });
}


/* =========================
   Admin Access Check
========================= */

async function checkAdminAccess() {

    try {

        await api("/admin/stats");

        return true;

    } catch (error) {

        console.error(
            "Admin access check failed:",
            error
        );

        alert(
            error.message === "Admin access required"
                ? "You do not have administrator access."
                : "Unable to access the admin dashboard."
        );

        window.location.href = "../index.html";

        return false;
    }
}


/* =========================
   Boot
========================= */

async function boot() {

    loadTheme();

    setupTheme();

    setupAdminUser();

    setupLogout();

    setupOpenUserPlatform();

    setupNavigation();

    setupRefresh();


    const token =
        localStorage.getItem(TOKEN_KEY);

    if (!token) {

        window.location.href = "../index.html";

        return;
    }


    const allowed =
        await checkAdminAccess();

    if (!allowed) {
        return;
    }


    await loadAdminView("overview");
}


document.addEventListener(
    "DOMContentLoaded",
    boot
);