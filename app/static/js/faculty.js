/**
 * EDVANCE Faculty Portal Logic & Dashboard
 */

let facultyCalendarMonth = new Date().getMonth();
let facultyCalendarYear = new Date().getFullYear();
let facultyCalendarEvents = [];

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("facultyDashboardStats")) {
    loadFacultyDashboard();
    initFacultyCalendar();
  }

  if (document.getElementById("facultyProfileForm")) {
    loadFacultyProfile();
  }
});

async function loadFacultyDashboard() {
  try {
    const res = await fetch("/api/faculty/dashboard-stats");
    if (!res.ok) return;
    const data = await res.json();

    const greetingEl = document.getElementById("facultyGreetingName");
    if (greetingEl) greetingEl.textContent = data.faculty_name;
    const deptEl = document.getElementById("facultyDeptText");
    if (deptEl) deptEl.textContent = data.department;

    document.getElementById("metricFacultyAssignments").textContent = data.active_assignments_count;
    document.getElementById("metricFacultyProjects").textContent = data.active_projects_count;
    document.getElementById("metricFacultyPending").textContent = data.pending_reviews_count;
    document.getElementById("metricFacultyTotalSubmissions").textContent = data.total_submissions_count;

    renderFacultyRecentSubmissions(data.recent_submissions);
    renderFacultyUpcomingDeadlines(data.upcoming_deadlines);
  } catch (err) {
    console.error("Failed to load faculty dashboard stats", err);
  }
}

function renderFacultyRecentSubmissions(submissions) {
  const container = document.getElementById("facultyRecentSubmissionsList");
  if (!container) return;

  if (!submissions || submissions.length === 0) {
    container.innerHTML = `
      <tr>
        <td colspan="5" class="empty-state">
          <p>No recent student submissions yet.</p>
        </td>
      </tr>
    `;
    return;
  }

  container.innerHTML = submissions
    .map(
      (s) => `
      <tr>
        <td>
          <div class="table-title">${escapeHtml(s.title)}</div>
          <div style="font-size:0.775rem; color:var(--text-muted);">${escapeHtml(s.target)}</div>
        </td>
        <td>
          <div style="font-weight:600; color:var(--text-main);">${escapeHtml(s.student_name)}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(s.student_roll)}</div>
        </td>
        <td>
          <span class="status-pill ${s.status.toLowerCase().replace(' ', '_')}">${s.status}</span>
        </td>
        <td>${s.date}</td>
        <td>
          <div style="display:flex; gap:0.4rem;">
            <a href="/api/submissions/${s.id}/download" class="btn btn-sm btn-secondary" title="Download File">Download</a>
            <a href="/faculty/evaluation?submission_id=${s.id}" class="btn btn-sm btn-primary">Evaluate</a>
          </div>
        </td>
      </tr>
    `
    )
    .join("");
}

function renderFacultyUpcomingDeadlines(deadlines) {
  const container = document.getElementById("facultyDeadlinesList");
  if (!container) return;

  if (!deadlines || deadlines.length === 0) {
    container.innerHTML = `
      <tr>
        <td colspan="3" class="empty-state">
          <p>No active deadlines scheduled.</p>
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
          <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(d.course)}</div>
        </td>
        <td>
          <span class="status-pill ${d.type.toLowerCase()}">${d.type}</span>
        </td>
        <td>${formatDateTime(d.deadline)}</td>
      </tr>
    `
    )
    .join("");
}

// ==========================================
// Faculty Calendar
// ==========================================

async function initFacultyCalendar() {
  try {
    const res = await fetch("/api/faculty/calendar-events");
    if (res.ok) {
      facultyCalendarEvents = await res.json();
    }
  } catch (e) {
    console.error("Faculty calendar error", e);
  }

  renderFacultyCalendarGrid(facultyCalendarMonth, facultyCalendarYear);

  const prevBtn = document.getElementById("facultyCalPrevBtn");
  const nextBtn = document.getElementById("facultyCalNextBtn");

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      facultyCalendarMonth--;
      if (facultyCalendarMonth < 0) {
        facultyCalendarMonth = 11;
        facultyCalendarYear--;
      }
      renderFacultyCalendarGrid(facultyCalendarMonth, facultyCalendarYear);
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      facultyCalendarMonth++;
      if (facultyCalendarMonth > 11) {
        facultyCalendarMonth = 0;
        facultyCalendarYear++;
      }
      renderFacultyCalendarGrid(facultyCalendarMonth, facultyCalendarYear);
    });
  }
}

function renderFacultyCalendarGrid(month, year) {
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  const titleEl = document.getElementById("facultyCalendarTitle");
  if (titleEl) {
    titleEl.textContent = `${monthNames[month]} ${year}`;
  }

  const gridEl = document.getElementById("facultyCalendarGrid");
  if (!gridEl) return;

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();

  let html = "";
  const dayHeaders = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  dayHeaders.forEach((dh) => {
    html += `<div class="cal-day-header">${dh}</div>`;
  });

  for (let i = 0; i < firstDay; i++) {
    html += `<div class="cal-cell empty"></div>`;
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const isToday =
      today.getDate() === d &&
      today.getMonth() === month &&
      today.getFullYear() === year;

    const dayEvents = facultyCalendarEvents.filter((ev) => ev.date === dateStr);
    let dotsHtml = "";
    if (dayEvents.length > 0) {
      dotsHtml = `<div style="display:flex; gap:2px; justify-content:center;">`;
      dayEvents.forEach((ev) => {
        dotsHtml += `<span class="cal-dot ${ev.type}"></span>`;
      });
      dotsHtml += `</div>`;
    }

    html += `
      <div class="cal-cell ${isToday ? "today" : ""}">
        <span>${d}</span>
        ${dotsHtml}
      </div>
    `;
  }

  gridEl.innerHTML = html;
}

// Faculty Profile Management
async function loadFacultyProfile() {
  try {
    const res = await fetch("/api/auth/me");
    if (!res.ok) return;
    const user = await res.json();

    document.getElementById("facultyProfileName").value = user.full_name || "";
    document.getElementById("facultyProfileEmail").value = user.email || "";
    document.getElementById("facultyProfileDept").value = user.department_or_major || "";
    document.getElementById("facultyProfileEmpId").value = user.roll_or_employee_id || "";
    document.getElementById("facultyProfileBio").value = user.bio || "";

    const form = document.getElementById("facultyProfileForm");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const saveBtn = document.getElementById("saveFacultyProfileBtn");
      saveBtn.disabled = true;

      const payload = {
        full_name: document.getElementById("facultyProfileName").value,
        department_or_major: document.getElementById("facultyProfileDept").value,
        roll_or_employee_id: document.getElementById("facultyProfileEmpId").value,
        bio: document.getElementById("facultyProfileBio").value,
      };

      const newPassword = document.getElementById("facultyProfileNewPass").value.trim();
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
          showToast("Faculty profile updated successfully!", "success");
          document.getElementById("facultyProfileNewPass").value = "";
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
    console.error("Faculty profile load error", err);
  }
}

