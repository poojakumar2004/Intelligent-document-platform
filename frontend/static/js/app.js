document.addEventListener("DOMContentLoaded", () => {
  const uploadForm = document.getElementById("uploadForm");
  const submitBtn = document.getElementById("submitBtn");
  const spinner = document.getElementById("spinner");
  const btnText = document.getElementById("btnText");
  const alertContainer = document.getElementById("alertContainer");

  if (uploadForm) {
    uploadForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      
      const fileInput = document.getElementById("documentFile");
      const typeSelect = document.getElementById("documentType");

      if (!fileInput.files.length) {
        showAlert("Please select a document file to upload.", "danger");
        return;
      }

      const file = fileInput.files[0];
      const validExtensions = ["pdf", "jpg", "jpeg", "png"];
      const ext = file.name.split(".").pop().toLowerCase();
      if (!validExtensions.includes(ext)) {
        showAlert("Only PDF, JPG, and PNG documents are supported.", "danger");
        return;
      }

      // Prepare form data
      const formData = new FormData();
      formData.append("file", file);
      formData.append("document_type", typeSelect.value);

      // Loading UI
      submitBtn.disabled = true;
      spinner.style.display = "inline-block";
      btnText.textContent = "Processing Document...";
      if (alertContainer) alertContainer.innerHTML = "";

      try {
        const response = await fetch("/api/v1/documents/process", {
          method: "POST",
          body: formData
        });

        const result = await response.json();

        if (!response.ok) {
          const errMsg = result.error ? `${result.error.code}: ${result.error.message}` : "Failed to process document.";
          showAlert(errMsg, "danger");
          resetButton();
          return;
        }

        // Success - navigate to document view
        window.location.href = `/view/${encodeURIComponent(result.document_name)}`;
      } catch (err) {
        showAlert(`Network error: ${err.message}`, "danger");
        resetButton();
      }
    });
  }

  function showAlert(message, type) {
    if (!alertContainer) return;
    alertContainer.innerHTML = `
      <div class="alert alert-${type}">
        <span>${message}</span>
      </div>
    `;
  }

  function resetButton() {
    submitBtn.disabled = false;
    spinner.style.display = "none";
    btnText.textContent = "Extract & Validate";
  }
});

// Copy JSON helper
function copyJson() {
  const jsonPre = document.getElementById("rawJsonText");
  if (!jsonPre) return;
  navigator.clipboard.writeText(jsonPre.innerText).then(() => {
    const copyBtn = document.getElementById("copyBtn");
    if (copyBtn) {
      const originalText = copyBtn.innerText;
      copyBtn.innerText = "✓ Copied!";
      setTimeout(() => copyBtn.innerText = originalText, 2000);
    }
  });
}
