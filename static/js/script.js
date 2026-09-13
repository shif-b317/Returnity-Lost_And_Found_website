/**
 * RETURNITY - Lost and Found Management System
 * Vanilla JavaScript Utilities
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Mobile Navigation Toggle
  const mobileToggle = document.getElementById("mobileNavToggle");
  const navLinks = document.getElementById("mainNavLinks");

  if (mobileToggle && navLinks) {
    mobileToggle.addEventListener("click", function () {
      navLinks.classList.toggle("show");
      const isExpanded = navLinks.classList.contains("show");
      mobileToggle.setAttribute("aria-expanded", isExpanded);
    });
  }

  // 2. Prevent Future Dates for Lost and Found Date Pickers
  const today = new Date().toISOString().split("T")[0];
  const dateInputs = document.querySelectorAll("input[type='date'][data-max-today]");
  dateInputs.forEach(function (input) {
    input.setAttribute("max", today);
  });

  // 3. Image Upload Preview
  const imageInputs = document.querySelectorAll("input[type='file'][data-preview-target]");
  imageInputs.forEach(function (input) {
    input.addEventListener("change", function () {
      const targetId = input.getAttribute("data-preview-target");
      const previewContainer = document.getElementById(targetId);
      if (!previewContainer) return;

      const file = input.files[0];
      if (file) {
        // Validate file size (5MB max)
        if (file.size > 5 * 1024 * 1024) {
          alert("Selected file exceeds the maximum allowed limit of 5 MB.");
          input.value = "";
          previewContainer.innerHTML = "";
          return;
        }

        if (file.type.startsWith("image/")) {
          const reader = new FileReader();
          reader.onload = function (e) {
            previewContainer.innerHTML = `
              <div style="margin-top: 0.75rem; max-width: 260px;">
                <p style="font-size: 0.8rem; color: #7B694E; margin-bottom: 0.25rem;">Selected Image Preview:</p>
                <img src="${e.target.result}" alt="Preview" style="width: 100%; height: 160px; object-fit: cover; border-radius: 6px; border: 1px solid #7B694E;" />
              </div>
            `;
          };
          reader.readAsDataURL(file);
        } else if (file.type === "application/pdf") {
          previewContainer.innerHTML = `
            <div style="margin-top: 0.5rem; font-size: 0.88rem; color: #280B0F; background: #F3EFEA; padding: 0.5rem 0.75rem; border-radius: 4px;">
              PDF Document Selected: <strong>${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)
            </div>
          `;
        }
      }
    });
  });

  // 4. Action Confirmations
  const confirmActions = document.querySelectorAll("[data-confirm]");
  confirmActions.forEach(function (elem) {
    elem.addEventListener("click", function (e) {
      const message = elem.getAttribute("data-confirm") || "Are you sure you want to perform this action?";
      if (!window.confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // 5. Password Confirmation Check on Registration
  const regForm = document.getElementById("registrationForm");
  if (regForm) {
    regForm.addEventListener("submit", function (e) {
      const password = document.getElementById("regPassword");
      const confirmPassword = document.getElementById("regConfirmPassword");

      if (password && confirmPassword && password.value !== confirmPassword.value) {
        e.preventDefault();
        alert("Password and Confirmation Password do not match. Please verify.");
        confirmPassword.focus();
      }
    });
  }

  // 6. Flash Alert Auto-Dismiss or Close
  const alertCloseButtons = document.querySelectorAll(".alert-close-btn");
  alertCloseButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const alertBox = btn.closest(".alert");
      if (alertBox) {
        alertBox.style.display = "none";
      }
    });
  });
});
