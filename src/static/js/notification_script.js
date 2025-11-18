/**
 * SMMS Notification System JavaScript
 * User Story 5.1: Notify users of publishing status and Team requests
 * 
 * Features:
 * - Real-time notification updates (auto-refresh every 30s)
 * - Search through notifications
 * - Filter by category: All, System, Team
 * - Mark as read (individual and bulk)
 * - Unread notifications in bold
 * - Clear all notifications
 */

// Configuration - IMPORTANT: This must match where notifapp.py is running
const NOTIF_SERVICE_URL = "http://127.0.0.1:5001";
const REFRESH_INTERVAL = 30000; // 30 seconds

// State
let allNotifications = [];
let currentFilter = "all";
let searchQuery = "";
let currentUserId = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    initializeUser();
    setupEventListeners();
    setInterval(loadNotifications, REFRESH_INTERVAL);
});

function initializeUser() {
    fetch("/api/current-user")
        .then(res => {
            if (!res.ok) throw new Error("Not logged in");
            return res.json();
        })
        .then(data => {
            if (data.user_id) {
                currentUserId = data.user_id;
                const userNameEl = document.getElementById("userName");
                const userAvatarEl = document.getElementById("userAvatar");
                if (userNameEl) userNameEl.textContent = data.full_name || "User";
                if (userAvatarEl) {
                    userAvatarEl.textContent = (data.full_name || "U")
                        .charAt(0)
                        .toUpperCase();
                }
                loadNotifications();
            }
        })
        .catch(err => {
            console.error("Could not fetch current user:", err);
            showLoginRequired();
        });
}

function setupEventListeners() {
    const markReadBtn = document.getElementById("markReadBtn");
    const clearAllBtn = document.getElementById("clearAllBtn");
    const settingsBtn = document.getElementById("settingsBtn");
    const bellBtn = document.getElementById("bellBtn");

    if (markReadBtn) {
        markReadBtn.addEventListener("click", markAllAsRead);
    }

    if (clearAllBtn) {
        clearAllBtn.addEventListener("click", clearAllNotifications);
    }

    if (settingsBtn) {
        settingsBtn.addEventListener("click", () => {
            alert(
                "Notification Settings\n\n" +
                    "• Email notifications: Configure in .env file\n" +
                    "• Notification preferences coming soon!\n\n" +
                    "Set EMAIL_ENABLED=true in your environment to receive email alerts."
            );
        });
    }

    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const active = document.querySelector(".tab.active");
            if (active) active.classList.remove("active");
            tab.classList.add("active");
            currentFilter = tab.dataset.filter;
            applyFilters();
        });
    });

    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener("input", e => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchQuery = e.target.value.trim();
                loadNotifications();
            }, 300);
        });
    }

    if (bellBtn) {
        bellBtn.addEventListener("click", () => {
            const content = document.querySelector(".content-area");
            if (content) {
                content.scrollTo({ top: 0, behavior: "smooth" });
            }
        });
    }
}

async function loadNotifications() {
    if (!currentUserId) {
        console.log("No user ID yet, waiting...");
        return;
    }

    try {
        showLoadingState();
        const params = new URLSearchParams();
        params.append("user_id", currentUserId);
        if (searchQuery) params.append("search", searchQuery);
        if (currentFilter !== "all") params.append("type", currentFilter);

        const response = await fetch(
            `${NOTIF_SERVICE_URL}/api/notifications?${params.toString()}`
        );

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        allNotifications = data.notifications || [];

        if (data.counts) {
            const notifCountEl = document.getElementById("notifCount");
            const countAllEl = document.getElementById("countAll");
            const countSystemEl = document.getElementById("countSystem");
            const countTeamEl = document.getElementById("countTeam");

            if (notifCountEl) notifCountEl.textContent = data.counts.unread;
            if (countAllEl) countAllEl.textContent = `(${data.counts.total})`;
            if (countSystemEl) countSystemEl.textContent = `(${data.counts.system})`;
            if (countTeamEl) countTeamEl.textContent = `(${data.counts.team})`;
        }

        renderNotifications(allNotifications);
    } catch (err) {
        console.error("Error loading notifications:", err);
        showErrorState(err.message);
    }
}

function showLoginRequired() {
    const container = document.getElementById("notificationsList");
    if (!container) return;

    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">🔒</div>
            <h3>Please log in</h3>
            <p>You need to be logged in to view your notifications.</p>
            <a href="/auth/login" class="btn-action">Login</a>
        </div>
    `;
}

function showLoadingState() {
    const container = document.getElementById("notificationsList");
    if (!container) return;

    if (allNotifications.length === 0) {
        container.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Loading notifications...</p>
            </div>
        `;
    }
}

function showErrorState(message) {
    const container = document.getElementById("notificationsList");
    if (!container) return;

    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">⚠️</div>
            <h3>Cannot load notifications</h3>
            <p>Error: ${message}</p>
            <p style="margin-top: 10px; font-size: 13px; color: #6b7280;">
                Make sure the notification service is running:<br>
                <code style="background: #f3f4f6; padding: 4px 8px; border-radius: 4px;">python notifapp.py</code>
            </p>
            <button onclick="loadNotifications()" class="btn-action" style="margin-top: 15px;">Retry</button>
        </div>
    `;
}

function applyFilters() {
    let filtered = [...allNotifications];

    if (currentFilter !== "all") {
        filtered = filtered.filter(n => n.notification_type === currentFilter);
    }

    if (searchQuery) {
        const query = searchQuery.toLowerCase();
        filtered = filtered.filter(
            n =>
                (n.title && n.title.toLowerCase().includes(query)) ||
                (n.message && n.message.toLowerCase().includes(query))
        );
    }

    renderNotifications(filtered);
}

function renderNotifications(list) {
    const container = document.getElementById("notificationsList");
    if (!container) return;

    if (!list || list.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📭</div>
                <h3>No notifications</h3>
                <p>You’ll see updates here when your team or system performs actions.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = "";
    list.forEach(notification => {
        container.appendChild(createNotificationCard(notification));
    });
}

/**
 * Formats timestamp as *IST* without manually adding +5:30.
 * We let the browser parse the string and then force display in Asia/Kolkata.
 *
 * This avoids double-shifting when the backend is already storing IST.
 */
function formatIST(timestamp) {
    if (!timestamp) return "Unknown time";

    // Some drivers return "YYYY-MM-DD HH:MM:SS" (with a space),
    // others "YYYY-MM-DDTHH:MM:SS". Normalize to something Date can parse.
    let ts = String(timestamp).trim();
    if (ts.includes(" ") && !ts.includes("T")) {
        ts = ts.replace(" ", "T");
    }

    const date = new Date(ts); // interpreted as local or UTC by engine
    if (isNaN(date.getTime())) {
        return "Unknown time";
    }

    const opts = {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
        timeZone: "Asia/Kolkata"
    };

    // Example: "18 Nov 2025, 04:58 pm IST"
    const parts = date.toLocaleString("en-IN", opts).replace(",", "");
    return `${parts} IST`;
}

/**
 * Returns display text for platform names (if you later wire platform through)
 */
function getPlatformLabel(platformRaw) {
    if (!platformRaw) return "";

    const p = platformRaw.toLowerCase();
    if (p.includes("linkedin")) return "LinkedIn";
    if (p.includes("twitter") || p.includes("x")) return "Twitter";
    if (p.includes("instagram")) return "Instagram";
    if (p.includes("facebook")) return "Facebook";
    return platformRaw;
}

/**
 * Builds the notification card DOM
 */
function createNotificationCard(n) {
    const card = document.createElement("div");
    card.className = `notification-card ${n.is_read ? "" : "unread"}`;

    const istTime = formatIST(n.created_at);
    // platform currently not provided reliably from backend, so we keep it optional
    const platformLabel = n.platform ? getPlatformLabel(n.platform) : "";

    card.innerHTML = `
        <div class="notif-left">
            <div class="notif-icon">
                ${n.notification_type === "team" ? "👥" : "🔔"}
            </div>
        </div>

        <div class="notif-content">
            <h4>${n.title || "Notification"}</h4>
            <p class="notif-message">
                ${n.message || ""}
            </p>

            <div class="notif-meta">
                <span class="notif-time">${istTime}</span>
                ${
                    n.post_id
                        ? `<span class="notif-post-id">Post ID: ${n.post_id}</span>`
                        : ""
                }
                ${
                    platformLabel
                        ? `<span class="notif-platform">${platformLabel}</span>`
                        : ""
                }
            </div>
        </div>

        <div class="notif-right">
            ${
                n.is_read
                    ? `<span class="read-indicator read">✓</span>`
                    : `<button class="mark-read-btn" data-id="${n.notification_id}">Mark Read</button>`
            }
        </div>
    `;
    const markBtn = card.querySelector(".mark-read-btn");
    if (markBtn) {
        markBtn.addEventListener("click", () => {
            markNotificationRead(n.notification_id);
        });
    }

    return card;
}

// Marks a single notification as read
async function markNotificationRead(id) {
    try {
        await fetch(`${NOTIF_SERVICE_URL}/api/notifications/${id}/read`, {
            method: "POST"
        });
        loadNotifications();
    } catch (err) {
        console.error("Failed to mark as read:", err);
        alert("Failed to mark notification as read.");
    }
}

async function markAllAsRead() {
    if (!currentUserId) return;

    try {
        await fetch(`${NOTIF_SERVICE_URL}/api/notifications/mark-all-read`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: currentUserId })
        });

        loadNotifications();
    } catch (err) {
        alert("Failed to mark all as read.");
        console.error(err);
    }
}

async function clearAllNotifications() {
    if (!currentUserId) return;

    if (!confirm("Clear ALL notifications? This cannot be undone.")) return;

    try {
        await fetch(`${NOTIF_SERVICE_URL}/api/notifications/clear-all`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: currentUserId })
        });

        loadNotifications();
    } catch (err) {
        alert("Failed to clear notifications.");
        console.error(err);
    }
}
