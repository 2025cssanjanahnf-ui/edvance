/**
 * EDVANCE Student Portal Logic & Interactive Calendar
 */

let currentCalendarMonth = new Date().getMonth();
let currentCalendarYear = new Date().getFullYear();
let studentCalendarEvents = [];

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("studentDashboardStats")) {
    loadStudentDashboard();
    initStudentCalendar();
  }

  if (document.getElementById("studentProfileForm")) {
    loadStudentProfile();
  }
});

// Load Student Dashboard Stats & Activities
async function loadStudentDashboard() {
  try {
    const res = await fetch("/api/student/dashboard-stats");
    if (!res.ok) return;
    const data = await res.json();

    // Populate Greeting & Department
    const greetingEl = document.getElementById("studentGreetingName");
    if (greetingEl) greetingEl.textContent = data.student_name;
    const deptEl = document.getElementById("studentMajorText");
    if (deptEl) deptEl.textContent = data.department;

    // Metrics
    document.getElementById("metricActiveAssignments").textContent = data.active_assignments_count;
    document.getElementById("metricOngoingProjects").textContent = data.ongoing_projects_count;
    document.getElementById("metricPendingSubmissions").textContent = data.pending_submissions_count;
    document.getElementById("metricFeedbackCount").textContent = data.feedback_received_count;

    // Upcoming Deadlines
    renderUpcomingDeadlines(data.upcoming_deadlines);

    // Recent Activities
    renderRecentActivities(data.recent_activities);
  } catch (err) {
    console.error("Failed to load student dashboard stats", err);
  }
}

function renderUpcomingDeadlines(deadlines) {
  const container = document.getElementById("upcomingDeadlinesList");
  if (!container) return;

  if (!deadlines || deadlines.length === 0) {
    container.innerHTML = `
      <tr>
        <td colspan="4" class="empty-state">
          <p>No upcoming deadlines. You're completely caught up!</p>
        </td>
      </tr>
    `;
    return;
  }

  container.innerHTML = deadlines
    .map(
      (d) => `
      <tr>
        <td>
          <div class="table-title">${escapeHtml(d.title)}</div>
          <div style="font-size: 0.775rem; color: var(--text-muted);">${escapeHtml(d.course)}</div>
        </td>
        <td>
          <span class="status-pill ${d.type.toLowerCase()}">${d.type}</span>
        </td>
        <td>${formatDateTime(d.deadline)}</td>
        <td>
          ${
            d.is_submitted
              ? '<span class="status-pill evaluated">Submitted</span>'
              : `<a href="${d.url}" class="btn btn-sm btn-primary">Submit</a>`
          }
        </td>
      </tr>
    `
    )
    .join("");
}

function renderRecentActivities(activities) {
  const container = document.getElementById("recentActivitiesList");
  if (!container) return;

  if (!activities || activities.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="padding: 1.5rem;">
        <p>No recent activity records found.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = activities
    .map(
      (a) => `
      <div style="padding: 0.85rem 0; border-bottom: 1px solid var(--border-subtle); display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div style="font-size:0.875rem; font-weight:600; color:var(--text-main);">${escapeHtml(a.title)}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${a.date} • ${escapeHtml(a.type)}</div>
        </div>
        <div>
          <span class="status-pill ${a.status.toLowerCase().replace(' ', '_')}">${escapeHtml(a.detail)}</span>
        </div>
      </div>
    `
    )
    .join("");
}

// ==========================================
// Integrated Interactive Monthly Calendar
// ==========================================

async function initStudentCalendar() {
  try {
    const res = await fetch("/api/student/calendar-events");
    if (res.ok) {
      studentCalendarEvents = await res.json();
    }
  } catch (e) {
    console.error("Calendar events error", e);
  }

  renderCalendar(currentCalendarMonth, currentCalendarYear);

  const prevBtn = document.getElementById("calPrevMonthBtn");
  const nextBtn = document.getElementById("calNextMonthBtn");

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      currentCalendarMonth--;
      if (currentCalendarMonth < 0) {
        currentCalendarMonth = 11;
        currentCalendarYear--;
      }
      renderCalendar(currentCalendarMonth, currentCalendarYear);
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      currentCalendarMonth++;
      if (currentCalendarMonth > 11) {
        currentCalendarMonth = 0;
        currentCalendarYear++;
      }
      renderCalendar(currentCalendarMonth, currentCalendarYear);
    });
  }
}

function renderCalendar(month, year) {
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  const titleEl = document.getElementById("calendarMonthTitle");
  if (titleEl) {
    titleEl.textContent = `${monthNames[month]} ${year}`;
  }

  const gridEl = document.getElementById("calendarDaysGrid");
  if (!gridEl) return;

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();

  let html = "";

  // Day header names
  const dayHeaders = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  dayHeaders.forEach((dh) => {
    html += `<div class="cal-day-header">${dh}</div>`;
  });

  // Empty cells before start of month
  for (let i = 0; i < firstDay; i++) {
    html += `<div class="cal-cell empty"></div>`;
  }

  // Days
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const isToday =
      today.getDate() === d &&
      today.getMonth() === month &&
      today.getFullYear() === year;

    // Check events for this date
    const dayEvents = studentCalendarEvents.filter((ev) => ev.date === dateStr);
    let dotsHtml = "";
    if (dayEvents.length > 0) {
      dotsHtml = `<div style="display:flex; gap:2px; justify-content:center;">`;
      dayEvents.forEach((ev) => {
        dotsHtml += `<span class="cal-dot ${ev.type}"></span>`;
      });
      dotsHtml += `</div>`;
    }

    html += `
      <div class="cal-cell ${isToday ? "today" : ""}" onclick="showCalendarDateEvents('${dateStr}')">
        <span>${d}</span>
        ${dotsHtml}
      </div>
    `;
  }

  gridEl.innerHTML = html;
}

function showCalendarDateEvents(dateStr) {
  const matched = studentCalendarEvents.filter((ev) => ev.date === dateStr);
  const detailBox = document.getElementById("calendarSelectedDayEvents");
  if (!detailBox) return;

  if (matched.length === 0) {
    detailBox.innerHTML = `
      <div style="font-size:0.8rem; color:var(--text-muted); text-align:center; padding: 0.5rem 0;">
        No academic events due on ${formatDate(dateStr)}.
      </div>
    `;
    return;
  }

  detailBox.innerHTML = `
    <div style="font-size:0.8rem; font-weight:600; color:var(--text-main); margin-bottom: 0.5rem;">
      Due on ${formatDate(dateStr)}:
    </div>
    ${matched
      .map(
        (m) => `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:0.4rem 0; border-top:1px solid var(--border-subtle); font-size:0.8rem;">
        <div>
          <span style="font-weight:600; color:var(--text-main);">${escapeHtml(m.title)}</span>
          <span style="color:var(--text-muted); font-size:0.75rem;">(${escapeHtml(m.course_code)})</span>
        </div>
        <a href="${m.url}" class="btn btn-sm btn-secondary" style="padding: 2px 8px; font-size:0.75rem;">View</a>
      </div>
    `
      )
      .join("")}
  `;
}

// Student Profile Management
async function loadStudentProfile() {
  try {
    const res = await fetch("/api/auth/me");
    if (!res.ok) return;
    const user = await res.json();

    document.getElementById("profileFullName").value = user.full_name || "";
    document.getElementById("profileEmail").value = user.email || "";
    document.getElementById("profileDept").value = user.department_or_major || "";
    document.getElementById("profileRoll").value = user.roll_or_employee_id || "";
    document.getElementById("profileBio").value = user.bio || "";

    const form = document.getElementById("studentProfileForm");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const saveBtn = document.getElementById("saveProfileBtn");
      saveBtn.disabled = true;

      const payload = {
        full_name: document.getElementById("profileFullName").value,
        department_or_major: document.getElementById("profileDept").value,
        roll_or_employee_id: document.getElementById("profileRoll").value,
        bio: document.getElementById("profileBio").value,
      };

      const newPassword = document.getElementById("profileNewPassword").value.trim();
      if (newPassword) {
        if (newPassword.length < 6) {
          showToast("Password must be at least 6 characters.", "error");
          saveBtn.disabled = false;
          return;
        }
        payload.password = newPassword;
      }

      try {
        const updateRes = await fetch("/api/auth/profile", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (updateRes.ok) {
          showToast("Profile details updated successfully!", "success");
          document.getElementById("profileNewPassword").value = "";
        } else {
          const err = await updateRes.json();
          showToast(err.detail || "Failed to update profile", "error");
        }
      } catch (err) {
        showToast("Error updating profile.", "error");
      } finally {
        saveBtn.disabled = false;
      }
    });
  } catch (err) {
    console.error("Profile load error", err);
  }
}

