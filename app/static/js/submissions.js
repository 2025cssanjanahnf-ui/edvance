/**
 * EDVANCE Submissions & Faculty Evaluation
 */

let submissionsCache = [];

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("submissionsContainer")) {
    loadSubmissions();
    setupSubmissionFilters();
  }

  // Check if evaluation page with URL parameter ?submission_id=123
  if (window.location.pathname.includes("/faculty/evaluation")) {
    initEvaluationPage();
  }
});

async function loadSubmissions() {
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const assignId = urlParams.get("assignment_id");
    const projId = urlParams.get("project_id");

    let fetchUrl = "/api/submissions?";
    if (assignId) fetchUrl += `assignment_id=${assignId}&`;
    if (projId) fetchUrl += `project_id=${projId}&`;

    const res = await fetch(fetchUrl);
    if (!res.ok) return;
    submissionsCache = await res.json();
    renderSubmissionsTable(submissionsCache);
  } catch (err) {
    console.error("Failed to load submissions", err);
  }
}

function setupSubmissionFilters() {
  const searchInput = document.getElementById("subSearchInput");
  const typeFilter = document.getElementById("subTypeFilter");
  const statusFilter = document.getElementById("subStatusFilter");

  function applyFilters() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
    const typeVal = typeFilter ? typeFilter.value : "all";
    const statusVal = statusFilter ? statusFilter.value : "all";

    const filtered = submissionsCache.filter((s) => {
      const matchQuery =
        s.title.toLowerCase().includes(query) ||
        s.file_name.toLowerCase().includes(query) ||
        (s.student_name && s.student_name.toLowerCase().includes(query)) ||
        (s.assignment_title && s.assignment_title.toLowerCase().includes(query)) ||
        (s.project_title && s.project_title.toLowerCase().includes(query));

      if (!matchQuery) return false;
      if (typeVal !== "all" && s.submission_type !== typeVal) return false;
      if (statusVal !== "all" && s.status !== statusVal) return false;
      return true;
    });

    renderSubmissionsTable(filtered);
  }

  if (searchInput) searchInput.addEventListener("input", applyFilters);
  if (typeFilter) typeFilter.addEventListener("change", applyFilters);
  if (statusFilter) statusFilter.addEventListener("change", applyFilters);
}

function renderSubmissionsTable(items) {
  const container = document.getElementById("submissionsContainer");
  if (!container) return;

  const isFaculty = document.body.dataset.role === "faculty";

  if (!items || items.length === 0) {
    container.innerHTML = `
      <tr>
        <td colspan="${isFaculty ? 6 : 5}" class="empty-state">
          <i data-lucide="inbox" class="empty-state-icon"></i>
          <h4>No submissions found</h4>
          <p>No submission records match your search criteria.</p>
        </td>
      </tr>
    `;
    if (window.lucide) window.lucide.createIcons();
    return;
  }

  if (isFaculty) {
    container.innerHTML = items
      .map(
        (s) => `
      <tr>
        <td>
          <div class="table-title">${escapeHtml(s.title)}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">
            ${escapeHtml(s.assignment_title || s.project_title || "General")}
          </div>
        </td>
        <td>
          <div style="font-weight:600; color:var(--text-main);">${escapeHtml(s.student_name)}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(s.student_roll || "")}</div>
        </td>
        <td>
          <span class="status-pill ${s.submission_type}">${s.submission_type}</span>
        </td>
        <td>
          <span class="status-pill ${s.status.toLowerCase().replace(' ', '_')}">${s.status}</span>
        </td>
        <td>${formatDateTime(s.submitted_at)}</td>
        <td style="text-align:right;">
          <div style="display:inline-flex; gap:0.4rem;">
            <a href="/api/submissions/${s.id}/download" class="btn btn-sm btn-secondary" title="Download ${escapeHtml(s.file_name)}">
              <i data-lucide="download" style="width:14px; height:14px;"></i> Download
            </a>
            <button class="btn btn-sm btn-primary" onclick="openEvaluateModal(${s.id})">
              ${s.feedback ? "Edit Grade" : "Evaluate"}
            </button>
          </div>
        </td>
      </tr>
    `
      )
      .join("");
  } else {
    // Student Table
    container.innerHTML = items
      .map(
        (s) => `
      <tr>
        <td>
          <div class="table-title">${escapeHtml(s.title)}</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">
            ${escapeHtml(s.assignment_title || s.project_title || "General")} • ${escapeHtml(s.file_name)}
          </div>
        </td>
        <td>
          <span class="status-pill ${s.submission_type}">${s.submission_type}</span>
        </td>
        <td>${formatDateTime(s.submitted_at)}</td>
        <td>
          <span class="status-pill ${s.status.toLowerCase().replace(' ', '_')}">${s.status}</span>
        </td>
        <td style="text-align:right;">
          <div style="display:inline-flex; gap:0.4rem;">
            <a href="/api/submissions/${s.id}/download" class="btn btn-sm btn-secondary" title="Download File">
              <i data-lucide="download" style="width:14px; height:14px;"></i>
            </a>
            ${
              s.feedback
                ? `<button class="btn btn-sm btn-primary" onclick="viewFeedbackDetailModal(${s.id})">
                     View Feedback (${s.feedback.score} pts)
                   </button>`
                : `<span style="font-size:0.8rem; color:var(--text-muted); padding: 4px 8px;">Pending Review</span>`
            }
          </div>
        </td>
      </tr>
    `
      )
      .join("");
  }

  if (window.lucide) window.lucide.createIcons();
}

// Student: View Feedback Detail Modal
function viewFeedbackDetailModal(subId) {
  const item = submissionsCache.find((s) => s.id === subId);
  if (!item || !item.feedback) return;

  const content = document.getElementById("studentFeedbackDetailContent");
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom:1rem;">
      <div style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Submission</div>
      <h3 style="margin-top:2px;">${escapeHtml(item.title)}</h3>
      <div style="font-size:0.825rem; color:var(--text-secondary);">${escapeHtml(item.assignment_title || item.project_title || "")}</div>
    </div>

    <div style="background:var(--success-soft); padding:1rem 1.25rem; border-radius:var(--radius-md); display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem;">
      <div>
        <div style="font-size:0.775rem; color:var(--success-text); font-weight:600; text-transform:uppercase;">Score Awarded</div>
        <div style="font-size:1.75rem; font-weight:700; color:var(--success); line-height:1.1;">
          ${item.feedback.score !== null ? item.feedback.score : "N/A"}<span style="font-size:1rem; font-weight:500;"> / 100</span>
        </div>
      </div>
      <div style="text-align:right; font-size:0.775rem; color:var(--text-muted);">
        Evaluated by ${escapeHtml(item.feedback.faculty_name)}<br/>
        ${formatDate(item.feedback.created_at)}
      </div>
    </div>

    <div>
      <div style="font-size:0.85rem; font-weight:600; color:var(--text-main); margin-bottom:0.4rem;">Instructor Comments:</div>
      <div class="feedback-comment">${escapeHtml(item.feedback.comments)}</div>
    </div>
  `;

  openModal("studentFeedbackModal");
}

// Faculty: Evaluation Modal & Page
function openEvaluateModal(submissionId) {
  const item = submissionsCache.find((s) => s.id === submissionId);
  if (!item) return;

  document.getElementById("evalSubmissionId").value = item.id;
  document.getElementById("evalMetaTitle").textContent = item.title;
  document.getElementById("evalMetaTarget").textContent = item.assignment_title || item.project_title || "General";
  document.getElementById("evalMetaStudent").textContent = `${item.student_name} (${item.student_roll || "N/A"})`;
  document.getElementById("evalMetaFile").innerHTML = `
    <a href="/api/submissions/${item.id}/download" style="color:var(--accent-600); font-weight:600;">
      📄 ${escapeHtml(item.file_name)} (${formatBytes(item.file_size)})
    </a>
  `;

  document.getElementById("evalScoreInput").value = item.feedback?.score ?? 90;
  document.getElementById("evalStatusSelect").value = item.status === "Needs Revision" ? "Needs Revision" : "Evaluated";
  document.getElementById("evalCommentsInput").value = item.feedback?.comments || "";

  openModal("facultyEvaluateModal");
}

const facultyEvalForm = document.getElementById("facultyEvaluationForm");
if (facultyEvalForm) {
  facultyEvalForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const subId = parseInt(document.getElementById("evalSubmissionId").value);
    const scoreVal = parseFloat(document.getElementById("evalScoreInput").value);
    const statusVal = document.getElementById("evalStatusSelect").value;
    const commentsVal = document.getElementById("evalCommentsInput").value.trim();
    const saveBtn = document.getElementById("btnSaveEvaluation");

    if (!commentsVal) {
      showToast("Please provide constructive evaluation comments.", "error");
      return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = "Saving Evaluation...";

    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          submission_id: subId,
          score: isNaN(scoreVal) ? null : scoreVal,
          comments: commentsVal,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save evaluation.");
      }

      showToast("Evaluation and feedback successfully saved!", "success");
      closeModal("facultyEvaluateModal");
      loadSubmissions();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save Evaluation";
    }
  });
}

// Standalone Evaluation Page Loader (if on /faculty/evaluation)
async function initEvaluationPage() {
  const urlParams = new URLSearchParams(window.location.search);
  const subId = urlParams.get("submission_id");

  if (!subId) {
    // If no specific submission selected, load submissions to select from
    loadSubmissions();
    return;
  }

  try {
    const res = await fetch(`/api/submissions/${subId}`);
    if (!res.ok) return;
    const item = await res.json();

    const panel = document.getElementById("standaloneEvalPanel");
    if (!panel) return;

    panel.style.display = "block";
    document.getElementById("evalSubmissionId").value = item.id;
    document.getElementById("evalMetaTitle").textContent = item.title;
    document.getElementById("evalMetaTarget").textContent = item.assignment_title || item.project_title || "General";
    document.getElementById("evalMetaStudent").textContent = `${item.student_name} (${item.student_roll || "N/A"})`;
    document.getElementById("evalMetaFile").innerHTML = `
      <a href="/api/submissions/${item.id}/download" class="btn btn-sm btn-secondary" style="margin-top:4px;">
        <i data-lucide="download" style="width:14px; height:14px;"></i> Download ${escapeHtml(item.file_name)}
      </a>
    `;

    document.getElementById("evalScoreInput").value = item.feedback?.score ?? 90;
    document.getElementById("evalStatusSelect").value = item.status === "Needs Revision" ? "Needs Revision" : "Evaluated";
    document.getElementById("evalCommentsInput").value = item.feedback?.comments || "";

    if (window.lucide) window.lucide.createIcons();
  } catch (err) {
    console.error("Evaluation init error", err);
  }
}

