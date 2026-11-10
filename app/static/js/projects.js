/**
 * EDVANCE Project & Team Management
 */

let projectsCache = [];
let availableStudents = [];

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("projectsContainer")) {
    loadProjects();
    setupProjectSearchAndFilters();
  }

  const projDocFile = document.getElementById("projDocFileInput");
  if (projDocFile) {
    projDocFile.addEventListener("change", (e) => {
      const file = e.target.files[0];
      const preview = document.getElementById("projDocChosenName");
      if (preview && file) {
        preview.innerHTML = `<span>Selected: <strong>${escapeHtml(file.name)}</strong> (${formatBytes(file.size)})</span>`;
      }
    });
  }
});

async function loadProjects() {
  try {
    const res = await fetch("/api/projects");
    if (!res.ok) return;
    projectsCache = await res.json();
    renderProjectsList(projectsCache);
  } catch (err) {
    console.error("Failed to load projects", err);
  }
}

function setupProjectSearchAndFilters() {
  const searchInput = document.getElementById("projectSearchInput");
  const filterSelect = document.getElementById("projectStatusFilter");

  function applyFilters() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
    const filter = filterSelect ? filterSelect.value : "all";

    const filtered = projectsCache.filter((p) => {
      const matchQuery =
        p.title.toLowerCase().includes(query) ||
        p.course_code.toLowerCase().includes(query) ||
        p.description.toLowerCase().includes(query);

      if (!matchQuery) return false;
      if (filter !== "all" && p.status !== filter) return false;
      return true;
    });

    renderProjectsList(filtered);
  }

  if (searchInput) searchInput.addEventListener("input", applyFilters);
  if (filterSelect) filterSelect.addEventListener("change", applyFilters);
}

function renderProjectsList(items) {
  const container = document.getElementById("projectsContainer");
  if (!container) return;

  const isFaculty = document.body.dataset.role === "faculty";

  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <i data-lucide="layers" class="empty-state-icon"></i>
        <h4>No projects found</h4>
        <p>${isFaculty ? "Click 'Create Project' to set up collaborative team projects." : "You are not assigned to any projects matching these criteria."}</p>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();
    return;
  }

  container.innerHTML = items
    .map(
      (p) => `
    <div class="project-card">
      <div>
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.4rem;">
          <span class="project-code">${escapeHtml(p.course_code)}</span>
          <span class="status-pill ${p.status.toLowerCase().replace(' ', '_')}">${p.status}</span>
        </div>
        <h3 class="project-title">${escapeHtml(p.title)}</h3>
        <p class="project-desc">${escapeHtml(p.description)}</p>

        <!-- Team Roster -->
        <div style="margin-top:1rem;">
          <div style="font-size:0.775rem; font-weight:600; color:var(--text-muted); text-transform:uppercase;">
            Team Members (${p.members.length})
          </div>
          <div class="team-roster">
            ${
              p.members.length > 0
                ? p.members
                    .map(
                      (m) => `
                  <div class="team-chip" title="${escapeHtml(m.student_email)}">
                    <span class="team-chip-avatar">${escapeHtml(m.student_name.charAt(0))}</span>
                    <span>${escapeHtml(m.student_name)}</span>
                    <span style="font-size:0.7rem; color:var(--text-muted);">(${escapeHtml(m.project_role)})</span>
                  </div>
                `
                    )
                    .join("")
                : '<span style="font-size:0.8rem; color:var(--text-muted);">No members assigned yet</span>'
            }
          </div>
        </div>

        <!-- Uploaded Documents Preview -->
        ${
          p.submissions.length > 0
            ? `
          <div style="margin-top:1rem; padding-top:0.75rem; border-top:1px solid var(--border-subtle);">
            <div style="font-size:0.775rem; font-weight:600; color:var(--text-muted); text-transform:uppercase; margin-bottom:0.4rem;">
              Milestone Documents (${p.submissions.length})
            </div>
            ${p.submissions
              .map(
                (s) => `
              <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; padding: 0.3rem 0;">
                <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:200px;" title="${escapeHtml(s.file_name)}">
                  📄 ${escapeHtml(s.title || s.file_name)}
                </span>
                <a href="/api/submissions/${s.id}/download" style="color:var(--accent-600); font-weight:600;">Download</a>
              </div>
            `
              )
              .join("")}
          </div>
        `
            : ""
        }
      </div>

      <!-- Action Footer -->
      <div style="margin-top:1.5rem; padding-top:1rem; border-top:1px solid var(--border-light); display:flex; justify-content:space-between; align-items:center;">
        <div style="font-size:0.775rem; color:var(--text-muted);">
          Due: ${formatDate(p.deadline)}
        </div>
        <div style="display:flex; gap:0.4rem;">
          ${
            isFaculty
              ? `
              <button class="btn btn-sm btn-secondary" onclick="openEditProjectModal(${p.id})">Edit</button>
              <button class="btn btn-sm btn-danger" onclick="confirmDeleteProject(${p.id})">Delete</button>
            `
              : `
              <button class="btn btn-sm btn-primary" onclick="openSubmitProjectDocModal(${p.id}, '${escapeHtml(p.title)}')">
                <i data-lucide="upload" style="width:14px; height:14px;"></i> Upload Milestone
              </button>
            `
          }
        </div>
      </div>
    </div>
  `
    )
    .join("");

  if (window.lucide) window.lucide.createIcons();
}

// Student: Upload Project Milestone
function openSubmitProjectDocModal(projectId, title) {
  document.getElementById("submitProjectId").value = projectId;
  document.getElementById("modalSubmitProjectTitle").textContent = title;
  document.getElementById("projDocTitleInput").value = `Milestone - ${title}`;
  document.getElementById("projDocFileInput").value = "";
  document.getElementById("projDocChosenName").innerHTML = "";
  openModal("submitProjectDocModal");
}

const projDocForm = document.getElementById("submitProjectDocForm");
if (projDocForm) {
  projDocForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const projectId = document.getElementById("submitProjectId").value;
    const title = document.getElementById("projDocTitleInput").value.trim();
    const file = document.getElementById("projDocFileInput").files[0];
    const submitBtn = document.getElementById("btnConfirmSubmitProjDoc");

    if (!file) {
      showToast("Please choose a file to upload.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("title", title);
    formData.append("file", file);

    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading...";

    try {
      const res = await fetch(`/api/submissions/project/${projectId}`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Document upload failed.");
      }

      showToast("Project document uploaded successfully!", "success");
      closeModal("submitProjectDocModal");
      loadProjects();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Upload Document";
    }
  });
}

// Faculty: Open Create Project Modal
async function openCreateProjectModal() {
  document.getElementById("projectModalTitle").textContent = "Create New Project";
  document.getElementById("projectEditId").value = "";
  document.getElementById("projTitleInput").value = "";
  document.getElementById("projCourseInput").value = "";
  document.getElementById("projDescInput").value = "";
  document.getElementById("projDeadlineInput").value = "";
  document.getElementById("projStatusSelect").value = "Planning";

  // Load student list for member assignment
  await loadAvailableStudentsForPicker();
  openModal("facultyProjectModal");
}

async function loadAvailableStudentsForPicker(selectedMemberIds = []) {
  const container = document.getElementById("studentPickerContainer");
  if (!container) return;

  try {
    const res = await fetch("/api/faculty/students-list");
    if (!res.ok) return;
    availableStudents = await res.json();

    container.innerHTML = availableStudents
      .map((s) => {
        const isChecked = selectedMemberIds.includes(s.id);
        return `
          <label class="student-picker-item">
            <input type="checkbox" name="assignedStudents" value="${s.id}" ${isChecked ? "checked" : ""} />
            <div class="student-picker-info">
              <div class="student-picker-name">${escapeHtml(s.full_name)}</div>
              <div class="student-picker-roll">${escapeHtml(s.roll_or_employee_id || "")} • ${escapeHtml(s.department_or_major || "")}</div>
            </div>
          </label>
        `;
      })
      .join("");
  } catch (err) {
    console.error("Error loading students list", err);
  }
}

function openEditProjectModal(projectId) {
  const item = projectsCache.find((p) => p.id === projectId);
  if (!item) return;

  document.getElementById("projectModalTitle").textContent = "Edit Project";
  document.getElementById("projectEditId").value = item.id;
  document.getElementById("projTitleInput").value = item.title;
  document.getElementById("projCourseInput").value = item.course_code;
  document.getElementById("projDescInput").value = item.description;

  if (item.deadline) {
    const d = new Date(item.deadline);
    const localIso = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    document.getElementById("projDeadlineInput").value = localIso;
  }

  document.getElementById("projStatusSelect").value = item.status || "Planning";

  const memberIds = item.members.map((m) => m.student_id);
  loadAvailableStudentsForPicker(memberIds);

  openModal("facultyProjectModal");
}

const facultyProjForm = document.getElementById("facultyProjectForm");
if (facultyProjForm) {
  facultyProjForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const editId = document.getElementById("projectEditId").value;
    const title = document.getElementById("projTitleInput").value.trim();
    const course = document.getElementById("projCourseInput").value.trim();
    const desc = document.getElementById("projDescInput").value.trim();
    const deadline = document.getElementById("projDeadlineInput").value;
    const statusVal = document.getElementById("projStatusSelect").value;
    const saveBtn = document.getElementById("btnSaveProject");

    const checkedBoxes = document.querySelectorAll('input[name="assignedStudents"]:checked');
    const memberIds = Array.from(checkedBoxes).map((cb) => parseInt(cb.value));

    if (!title || !course || !desc || !deadline) {
      showToast("Please complete all required fields.", "error");
      return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";

    try {
      if (editId) {
        // Update project details
        const res = await fetch(`/api/projects/${editId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: title,
            course_code: course,
            description: desc,
            deadline: deadline,
            status: statusVal,
          }),
        });
        if (!res.ok) throw new Error("Failed to update project.");
      } else {
        // Create project
        const res = await fetch("/api/projects", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: title,
            course_code: course,
            description: desc,
            deadline: deadline,
            status: statusVal,
            member_ids: memberIds,
          }),
        });
        if (!res.ok) throw new Error("Failed to create project.");
      }

      showToast(`Project ${editId ? "updated" : "created"} successfully!`, "success");
      closeModal("facultyProjectModal");
      loadProjects();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save Project";
    }
  });
}

async function confirmDeleteProject(projectId) {
  if (!confirm("Are you sure you want to permanently delete this project and its member assignments?")) {
    return;
  }

  try {
    const res = await fetch(`/api/projects/${projectId}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Project deleted successfully.", "success");
      loadProjects();
    } else {
      const err = await res.json();
      showToast(err.detail || "Failed to delete project", "error");
    }
  } catch (err) {
    showToast("Error deleting project.", "error");
  }
}

