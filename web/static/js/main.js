// ContextGuard — Professional Dashboard Client Script

document.addEventListener("DOMContentLoaded", function () {
  const prForm = document.getElementById("pr-submit-form");
  const alertBanner = document.getElementById("pr-alert-banner");

  function showAlert(msg, type = "error") {
    if (!alertBanner) {
      alert(msg);
      return;
    }
    alertBanner.style.display = "block";
    if (type === "error") {
      alertBanner.style.background = "rgba(127, 29, 29, 0.5)";
      alertBanner.style.border = "1px solid #ef4444";
      alertBanner.style.color = "#fca5a5";
    } else if (type === "warning") {
      alertBanner.style.background = "rgba(120, 53, 15, 0.5)";
      alertBanner.style.border = "1px solid #f59e0b";
      alertBanner.style.color = "#fcd34d";
    } else {
      alertBanner.style.background = "rgba(6, 78, 59, 0.5)";
      alertBanner.style.border = "1px solid #10b981";
      alertBanner.style.color = "#86efac";
    }
    alertBanner.innerHTML = msg;
  }

  function clearAlert() {
    if (alertBanner) {
      alertBanner.style.display = "none";
      alertBanner.innerHTML = "";
    }
  }

  if (prForm) {
    prForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const input = document.getElementById("pr-url-input");
      const btn = document.getElementById("pr-submit-btn");
      const statusDiv = document.getElementById("submit-status");

      if (!input || !input.value.trim()) return;

      clearAlert();
      btn.disabled = true;
      const originalText = "<span>🔍</span><span>Fact-Check This Code</span>";
      btn.innerHTML = "<span>⏳</span><span>Verifying in Sandbox...</span>";
      if (statusDiv) {
        statusDiv.innerHTML = "<span style='color: #60a5fa;'>Executing ContextGuard verification pipeline...</span>";
      }

      fetch("/api/submit_pr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pr_url: input.value.trim() })
      })
      .then(res => res.json())
      .then(data => {
        btn.disabled = false;
        btn.innerHTML = originalText;
        if (data.status === "COMPLETED" || data.status === "CACHED") {
          if (statusDiv) statusDiv.innerHTML = "<span style='color: #34d399;'>Verified! Redirecting...</span>";
          window.location.href = `/developer?pr_id=${encodeURIComponent(data.pr_id)}`;
        } else if (data.status === "FAIL_OPEN") {
          showAlert(`<strong>Fail-Open Fallback:</strong> ${data.decision_reason}`, "warning");
          setTimeout(() => {
            window.location.href = `/developer?pr_id=${encodeURIComponent(data.pr_id)}`;
          }, 1200);
        } else {
          showAlert(`<strong>Verification Error:</strong> ${data.error || "Verification failed."}`, "error");
          if (statusDiv) statusDiv.innerText = "";
        }
      })
      .catch(err => {
        btn.disabled = false;
        btn.innerHTML = originalText;
        showAlert(`<strong>Request Failed:</strong> ${err.message}`, "error");
        if (statusDiv) statusDiv.innerText = "";
      });
    });
  }

  // Quick Benchmark Scenario Helper
  window.loadQuickPr = function (num) {
    const input = document.getElementById("pr-url-input");
    if (input) {
      input.value = `https://github.com/shopkit/shopkit/pull/${num}`;
      const form = document.getElementById("pr-submit-form");
      if (form) form.requestSubmit();
    }
  };
});
