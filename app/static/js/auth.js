/**
 * EDVANCE Authentication Script
 */

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("loginForm");
  const roleInputs = document.querySelectorAll('input[name="authRole"]');
  const togglePasswordBtn = document.getElementById("togglePasswordBtn");
  const passwordInput = document.getElementById("passwordInput");
  const errorAlert = document.getElementById("authErrorAlert");

  // Show/Hide Password Toggle
  if (togglePasswordBtn && passwordInput) {
    togglePasswordBtn.addEventListener("click", () => {
      const isPassword = passwordInput.type === "password";
      passwordInput.type = isPassword ? "text" : "password";
      togglePasswordBtn.innerHTML = isPassword
        ? '<i data-lucide="eye-off" style="width:18px; height:18px;"></i>'
        : '<i data-lucide="eye" style="width:18px; height:18px;"></i>';
      if (window.lucide) window.lucide.createIcons();
    });
  }

  // Handle Form Submit
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (errorAlert) errorAlert.style.display = "none";

      const email = document.getElementById("emailInput").value.trim();
      const password = passwordInput.value;
      const selectedRole = document.querySelector('input[name="authRole"]:checked')?.value || "student";
      const submitBtn = document.getElementById("loginSubmitBtn");

      if (!email || !password) {
        showAuthError("Please provide both email and password.");
        return;
      }

      submitBtn.disabled = true;
      const origText = submitBtn.innerHTML;
      submitBtn.innerHTML = '<span>Signing in...</span>';

      try {
        const response = await fetch("/api/auth/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: email,
            password: password,
            role: selectedRole,
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Authentication failed.");
        }

        // Store user role and token in localStorage as secondary store
        localStorage.setItem("edvance_role", data.role);
        localStorage.setItem("edvance_user", data.full_name);

        // Redirect based on role
        if (data.role === "faculty") {
          window.location.href = "/faculty/dashboard";
        } else {
          window.location.href = "/student/dashboard";
        }
      } catch (err) {
        showAuthError(err.message);
        submitBtn.disabled = false;
        submitBtn.innerHTML = origText;
      }
    });
  }
});

function showAuthError(msg) {
  const errorAlert = document.getElementById("authErrorAlert");
  if (errorAlert) {
    errorAlert.textContent = msg;
    errorAlert.style.display = "block";
  }
}

// Quick Demo Credential Fillers
function fillDemoStudent() {
  document.getElementById("emailInput").value = "student@edvance.edu";
  document.getElementById("passwordInput").value = "Student@123";
  const studentRadio = document.getElementById("roleStudent");
  if (studentRadio) studentRadio.checked = true;
}

function fillDemoFaculty() {
  document.getElementById("emailInput").value = "faculty@edvance.edu";
  document.getElementById("passwordInput").value = "Faculty@123";
  const facultyRadio = document.getElementById("roleFaculty");
  if (facultyRadio) facultyRadio.checked = true;
}

