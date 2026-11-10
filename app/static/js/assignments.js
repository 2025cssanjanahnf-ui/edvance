/**
 * EDVANCE Assignment Management (Student & Faculty)
 */

let assignmentsCache = [];

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("assignmentsContainer")) {
    loadAssignments();
    setupAssignmentSearchAndFilters();
  }

  // Setup File Upload Dropzone previews
  const fileInput = document.getElementById("submissionFileInput");
  if (fileInput) {
    fileInput.addEventListener("change", handleFileChosenPreview);
  }
  const refInput = document.getElementById("assignRefFileInput");
  if (refInput) {
    refInput.addEventListener("change", handleRefFileChosenPreview);
  }
});

function handleFileChosenPreview(e) {
  const file = e.target.files[0];
  const preview = document.getElementById("fileChosenName");
  if (preview && file) {
    preview.innerHTML = `<span>Selected: <strong>${escapeHtml(file.name)}</strong> (${formatBytes(file.size)})</span>`;
  }
}

function handleRefFileChosenPreview(e) {
  const file = e.target.files[0];
  const preview = document.getElementById("refFileChosenName");
  if (preview && file) {
    preview.innerHTML = `<span>Attached: <strong>${escapeHtml(file.name)}</strong> (${formatBytes(file.size)})</span>`;
  }
}

async function loadAssignments() {
  try {
    const res = await fetch("/api/assignments");
    if (!res.ok) return;
    assignmentsCache = await res.json();
    renderAssignmentsList(assignmentsCache);
  } catch (err) {
    console.error("Failed to load assignments", err);
  }
}

function setupAssignmentSearchAndFilters() {
  const searchInput = document.getElementById("assignmentSearchInput");
  const filterSelect = document.getElementById("assignmentFilterSelect");

  function applyFilters() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
    const filter = filterSelect ? filterSelect.value : "all";

    const filtered = assignmentsCache.filter((a) => {
      const matchQuery =
        a.title.toLowerCase().includes(query) ||
        a.course_code.toLowerCase().includes(query) ||
        a.description.toLowerCase().includes(query);

      if (!matchQuery) return false;

      const isStudent = document.body.dataset.role === "student";
      if (isStudent) {
        if (filter === "submitted") return a.has_submitted;
        if (filter === "pending") return !a.has_submitted;
      }
      return true;
    });

    renderAssignmentsList(filtered);
  }

  if (searchInput) searchInput.addEventListener("input", applyFilters);
  if (filterSelect) filterSelect.addEventListener("change", applyFilters);
}

function renderAssignmentsList(items) {
  const container = document.getElementById("assignmentsContainer");
  if (!container) return;

  const isFaculty = document.body.dataset.role === "faculty";

  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <i data-lucide="file-text" class="empty-state-icon"></i>
        <h4>No assignments found</h4>
        <p>${isFaculty ? "Click 'Create Assignment' to publish your first academic task." : "No assignments match your current filters."}</p>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();
    return;
  }

  if (isFaculty) {
    renderFacultyAssignments(items, container);
  } else {
    renderStudentAssignments(items, container);
  }

  if (window.lucide) window.lucide.createIcons();
}

function renderStudentAssignments(items, container) {
  container.innerHTML = items
    .map(
      (a) => `
    <div class="card" style="margin-bottom: 1.25rem;">
      <div class="card-body">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem; flex-wrap:wrap; gap:0.5rem;">
          <div>
            <div style="font-size:0.75rem; font-weight:600; color:var(--accent-600); text-transform:uppercase;">${escapeHtml(a.course_code)}</div>
            <h3 style="margin-top:2px;">${escapeHtml(a.title)}</h3>
            <div style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">Instructor: ${escapeHtml(a.faculty_name)}</div>
          </div>
          <div>
            ${
              a.has_submitted
                ? `<span class="status-pill ${a.student_submission?.status?.toLowerCase() || 'submitted'}">${a.student_submission?.status || 'Submitted'}</span>`
                : `<span class="status-pill late">Pending Submission</span>`
            }
          </div>
        </div>

        <p style="font-size:0.875rem; color:var(--text-secondary); line-height:1.6; margin-bottom:1.25rem;">
          ${escapeHtml(a.description)}
        </p>

        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-subtle); padding-top:1rem; flex-wrap:wrap; gap:0.75rem;">
          <div style="font-size:0.8rem; color:var(--text-muted);">
            <strong>Deadline:</strong> ${formatDateTime(a.deadline)} • <strong>Max Score:</strong> ${a.max_score} pts
          </div>
          <div style="display:flex; gap:0.5rem; align-items:center;">
            ${
              a.reference_file_path
                ? `<a href="/api/assignments/${a.id}/reference" class="btn btn-sm btn-secondary" title="Download Reference Guide">
                     <i data-lucide="download" style="width:14px; height:14px;"></i> Reference File
                   </a>`
                : ""
            }
            ${
              a.has_submitted
                ? `<button class="btn btn-sm btn-secondary" onclick="openStudentSubmissionDetail(${a.id})">
                     View My Work
                   </button>`
                : `<button class="btn btn-sm btn-primary" onclick="openSubmitAssignmentModal(${a.id}, '${escapeHtml(a.title)}')">
                     <i data-lucide="upload" style="width:14px; height:14px;"></i> Submit Assignment
                   </button>`
            }
          </div>
        </div>
      </div>
    </div>
  `
    )
    .join("");
}

function renderFacultyAssignments(items, container) {
  container.innerHTML = `
    <div class="card">
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Assignment Title & Course</th>
              <th>Deadline</th>
              <th>Submissions</th>
              <th>Reference</th>
              <th style="text-align:right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${items
              .map(
                (a) => `
              <tr>
                <td>
                  <div class="table-title">${escapeHtml(a.title)}</div>
                  <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(a.course_code)} • Max ${a.max_score} pts</div>
                </td>
                <td>${formatDateTime(a.deadline)}</td>
                <td>
                  <a href="/faculty/submissions?assignment_id=${a.id}" class="btn btn-sm btn-secondary">
                    ${a.submission_count} Submissions
                  </a>
                </td>
                <td>
                  ${
                    a.reference_file_name
                      ? `<a href="/api/assignments/${a.id}/reference" style="font-size:0.8rem; color:var(--accent-600); display:flex; align-items:center; gap:4px;">
                           <i data-lucide="file" style="width:14px; height:14px;"></i> ${escapeHtml(a.reference_file_name)}
                         </a>`
                      : '<span style="color:var(--text-muted); font-size:0.8rem;">None</span>'
                  }
                </td>
                <td style="text-align:right;">
                  <div style="display:inline-flex; gap:0.4rem;">
                    <button class="btn btn-sm btn-secondary" onclick="openEditAssignmentModal(${a.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="confirmDeleteAssignment(${a.id})">Delete</button>
                  </div>
                </td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// Student: Open Submit Assignment Modal
function openSubmitAssignmentModal(assignmentId, title) {
  document.getElementById("submitAssignmentId").value = assignmentId;
  document.getElementById("modalSubmitAssignmentTitle").textContent = title;
  document.getElementById("submissionDocTitle").value = `Submission - ${title}`;
  document.getElementById("submissionFileInput").value = "";
  document.getElementById("fileChosenName").innerHTML = "";
  openModal("submitAssignmentModal");
}

// Handle Student Assignment Submit Form
const submitForm = document.getElementById("submitAssignmentForm");
if (submitForm) {
  submitForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const assignmentId = document.getElementById("submitAssignmentId").value;
    const title = document.getElementById("submissionDocTitle").value.trim();
    const file = document.getElementById("submissionFileInput").files[0];
    const submitBtn = document.getElementById("btnConfirmSubmitAssignment");

    if (!file) {
      showToast("Please select a document to upload.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("title", title);
    formData.append("file", file);

    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading...";

    try {
      const res = await fetch(`/api/submissions/assignment/${assignmentId}`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Submission failed.");
      }

      showToast("Assignment submitted successfully!", "success");
      closeModal("submitAssignmentModal");
      loadAssignments();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Work";
    }
  });
}

// Student: View My Submission Detail Modal
function openStudentSubmissionDetail(assignmentId) {
  const item = assignmentsCache.find((a) => a.id === assignmentId);
  if (!item || !item.student_submission) return;

  const sub = item.student_submission;
  const body = document.getElementById("studentSubDetailBody");
  if (!body) return;

  body.innerHTML = `
    <div class="meta-row"><span class="meta-label">Submission Title:</span> <span class="meta-value">${escapeHtml(sub.title)}</span></div>
    <div class="meta-row"><span class="meta-label">File Attached:</span> <span class="meta-value">${escapeHtml(sub.file_name)} (${formatBytes(sub.file_size)})</span></div>
    <div class="meta-row"><span class="meta-label">Status:</span> <span class="meta-value"><span class="status-pill ${sub.status.toLowerCase()}">${sub.status}</span></span></div>
    <div class="meta-row"><span class="meta-label">Submitted On:</span> <span class="meta-value">${formatDateTime(sub.submitted_at)}</span></div>
    <div style="margin-top:1.25rem;">
      <a href="/api/submissions/${sub.id}/download" class="btn btn-secondary btn-sm" style="width:100%;">
        <i data-lucide="download" style="width:14px; height:14px;"></i> Download Submitted File
      </a>
    </div>
    ${
      sub.feedback
        ? `
      <div style="margin-top:1.5rem; padding-top:1rem; border-top:1px solid var(--border-light);">
        <h4 style="font-size:0.95rem; margin-bottom:0.5rem; color:var(--text-main);">Faculty Evaluation</h4>
        <div style="font-size:0.85rem; color:var(--success); font-weight:700; margin-bottom:0.4rem;">
          Score: ${sub.feedback.score} / 100
        </div>
        <div class="feedback-comment">${escapeHtml(sub.feedback.comments)}</div>
      </div>
    `
        : `<div style="margin-top:1rem; font-size:0.8rem; color:var(--text-muted); text-align:center;">Evaluation is currently pending from faculty.</div>`
    }
  `;

  if (window.lucide) window.lucide.createIcons();
  openModal("studentSubDetailModal");
}

// Faculty: Create / Edit Assignment Logic
function openCreateAssignmentModal() {
  document.getElementById("assignmentModalTitle").textContent = "Create New Assignment";
  document.getElementById("assignmentEditId").value = "";
  document.getElementById("assignTitleInput").value = "";
  document.getElementById("assignCourseInput").value = "";
  document.getElementById("assignDescInput").value = "";
  document.getElementById("assignDeadlineInput").value = "";
  document.getElementById("assignMaxScoreInput").value = 100;
  document.getElementById("assignRefFileInput").value = "";
  document.getElementById("refFileChosenName").innerHTML = "";
  openModal("createAssignmentModal");
}

function openEditAssignmentModal(assignmentId) {
  const item = assignmentsCache.find((a) => a.id === assignmentId);
  if (!item) return;

  document.getElementById("assignmentModalTitle").textContent = "Edit Assignment";
  document.getElementById("assignmentEditId").value = item.id;
  document.getElementById("assignTitleInput").value = item.title;
  document.getElementById("assignCourseInput").value = item.course_code;
  document.getElementById("assignDescInput").value = item.description;

  // Format date for datetime-local (YYYY-MM-DDTHH:MM)
  if (item.deadline) {
    const d = new Date(item.deadline);
    const localIso = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    document.getElementById("assignDeadlineInput").value = localIso;
  }

  document.getElementById("assignMaxScoreInput").value = item.max_score || 100;
  document.getElementById("refFileChosenName").innerHTML = item.reference_file_name
    ? `<span>Current File: <strong>${escapeHtml(item.reference_file_name)}</strong></span>`
    : "";

  openModal("createAssignmentModal");
}

const facultyAssignForm = document.getElementById("facultyAssignmentForm");
if (facultyAssignForm) {
  facultyAssignForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const editId = document.getElementById("assignmentEditId").value;
    const title = document.getElementById("assignTitleInput").value.trim();
    const course = document.getElementById("assignCourseInput").value.trim();
    const desc = document.getElementById("assignDescInput").value.trim();
    const deadline = document.getElementById("assignDeadlineInput").value;
    const maxScore = document.getElementById("assignMaxScoreInput").value;
    const refFile = document.getElementById("assignRefFileInput").files[0];
    const saveBtn = document.getElementById("btnSaveAssignment");

    if (!title || !course || !desc || !deadline) {
      showToast("Please fill in all required fields.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("title", title);
    formData.append("course_code", course);
    formData.append("description", desc);
    formData.append("deadline", deadline);
    formData.append("max_score", maxScore);
    if (refFile) {
      formData.append("reference_file", refFile);
    }

    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";

    try {
      const url = editId ? `/api/assignments/${editId}` : "/api/assignments";
      const method = editId ? "PUT" : "POST";

      const res = await fetch(url, {
        method: method,
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save assignment.");
      }

      showToast(`Assignment ${editId ? "updated" : "created"} successfully!`, "success");
      closeModal("createAssignmentModal");
      loadAssignments();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save Assignment";
    }
  });
}

async function confirmDeleteAssignment(assignmentId) {
  if (!confirm("Are you sure you want to permanently delete this assignment and all associated student submissions?")) {
    return;
  }

  try {
    const res = await fetch(`/api/assignments/${assignmentId}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Assignment deleted successfully.", "success");
      loadAssignments();
    } else {
      const err = await res.json();
      showToast(err.detail || "Failed to delete assignment", "error");
    }
  } catch (err) {
    showToast("Error deleting assignment.", "error");
  }
}

