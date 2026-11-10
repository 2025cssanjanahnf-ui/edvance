/**
 * EDVANCE Notifications Manager
 */

document.addEventListener("DOMContentLoaded", () => {
  initNotifications();
});

let notificationsData = [];

function initNotifications() {
  const bellBtn = document.getElementById("notifBellBtn");
  const dropdown = document.getElementById("notifDropdown");
  const markAllBtn = document.getElementById("markAllReadBtn");

  if (bellBtn && dropdown) {
    bellBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.toggle("active");
    });

    document.addEventListener("click", (e) => {
      if (!dropdown.contains(e.target) && !bellBtn.contains(e.target)) {
        dropdown.classList.remove("active");
      }
    });
  }

  if (markAllBtn) {
    markAllBtn.addEventListener("click", markAllNotificationsRead);
  }

  fetchNotifications();
}

async function fetchNotifications() {
  try {
    const res = await fetch("/api/notifications");
    if (!res.ok) return;
    const data = await res.json();
    notificationsData = data.notifications || [];
    renderNotificationBadge(data.unread_count || 0);
    renderNotificationList(notificationsData);
  } catch (err) {
    console.error("Failed to load notifications", err);
  }
}

function renderNotificationBadge(count) {
  const badge = document.getElementById("notifBadge");
  if (!badge) return;
  if (count > 0) {
    badge.textContent = count > 9 ? "9+" : count;
    badge.style.display = "flex";
  } else {
    badge.style.display = "none";
  }
}

function renderNotificationList(items) {
  const listEl = document.getElementById("notifList");
  if (!listEl) return;

  if (items.length === 0) {
    listEl.innerHTML = `
      <div class="notif-empty">
        <p>No notifications right now.</p>
      </div>
    `;
    return;
  }

  listEl.innerHTML = items
    .map(
      (n) => `
      <li class="notif-item ${n.is_read ? "" : "unread"}" onclick="handleNotifClick(${n.id}, '${escapeHtml(n.link || "")}')">
        <div class="notif-item-title">${escapeHtml(n.title)}</div>
        <div class="notif-item-msg">${escapeHtml(n.message)}</div>
        <div class="notif-item-time">${formatDateTime(n.created_at)}</div>
      </li>
    `
    )
    .join("");
}

async function handleNotifClick(notifId, link) {
  try {
    await fetch(`/api/notifications/${notifId}/read`, { method: "PATCH" });
    fetchNotifications();
    if (link) {
      window.location.href = link;
    }
  } catch (err) {
    console.error("Error reading notification", err);
  }
}

async function markAllNotificationsRead() {
  try {
    const res = await fetch("/api/notifications/read-all", { method: "POST" });
    if (res.ok) {
      fetchNotifications();
      showToast("All notifications marked as read.", "success");
    }
  } catch (err) {
    console.error("Error marking all read", err);
  }
}

