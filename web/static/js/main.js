// ContextGuard Dashboard Client Scripts

document.addEventListener("DOMContentLoaded", function () {
  // PR & Repository Submission Form
  const prForm = document.getElementById("pr-submit-form");
  const alertBanner = document.getElementById("pr-alert-banner");

  function showAlert(msg, type = "error") {
    if (!alertBanner) {
      alert(msg);
      return;
    }
    alertBanner.style.display = "block";
    if (type === "error") {
      alertBanner.style.background = "#450a0a";
      alertBanner.style.border = "1px solid #dc2626";
      alertBanner.style.color = "#fca5a5";
    } else if (type === "warning") {
      alertBanner.style.background = "#451a03";
      alertBanner.style.border = "1px solid #d97706";
      alertBanner.style.color = "#fcd34d";
    } else {
      alertBanner.style.background = "#052e16";
      alertBanner.style.border = "1px solid #16a34a";
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
      const originalText = "Verify Codebase / PR";
      btn.innerText = "Verifying...";
      if (statusDiv) statusDiv.innerHTML = "<span style='color: #38bdf8;'>Running ContextGuard verification pipeline...</span>";

      fetch("/api/submit_pr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pr_url: input.value.trim() })
      })
      .then(res => res.json())
      .then(data => {
        btn.disabled = false;
        btn.innerText = originalText;
        if (data.status === "COMPLETED" || data.status === "CACHED") {
          if (statusDiv) statusDiv.innerHTML = "<span style='color: #4ade80;'>Verified! Redirecting...</span>";
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
        btn.innerText = originalText;
        showAlert(`<strong>Request Failed:</strong> ${err.message}`, "error");
        if (statusDiv) statusDiv.innerText = "";
      });
    });
  }

  // Quick PR Selection Helper
  window.loadQuickPr = function (num) {
    const input = document.getElementById("pr-url-input");
    if (input) {
      input.value = `https://github.com/shopkit/shopkit/pull/${num}`;
      const form = document.getElementById("pr-submit-form");
      if (form) form.requestSubmit();
    }
  };

  // Reviewer Override Function
  window.overrideVerdict = function (prId, currentVerdict) {
    const newVerdict = currentVerdict === "COMPLIANT" ? "NON_COMPLIANT" : "COMPLIANT";
    const reason = prompt(`Enter justification for overriding ${prId} to ${newVerdict}:`, "Manual inspection by reviewer.");
    if (!reason) return;

    fetch("/api/override_verdict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pr_id: prId,
        new_verdict: newVerdict,
        reviewer_name: "Lead Reviewer",
        reason: reason
      })
    })
    .then(res => res.json())
    .then(data => {
      if (data.status === "success") {
        alert(`Verdict successfully updated to ${newVerdict}.`);
        window.location.reload();
      } else {
        alert("Failed to override verdict.");
      }
    })
    .catch(err => alert("Error overriding verdict: " + err.message));
  };

  // Admin Scope Update
  const scopeForm = document.getElementById("scope-form");
  if (scopeForm) {
    scopeForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const repoId = document.getElementById("scope-repo-id").value;
      const allowPaths = document.getElementById("scope-allow-paths").value;
      const denyPaths = document.getElementById("scope-deny-paths").value;

      fetch("/api/update_scope", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_id: repoId, allow_paths: allowPaths, deny_paths: denyPaths })
      })
      .then(res => res.json())
      .then(data => {
        alert("Scope rules updated successfully.");
        window.location.reload();
      })
      .catch(err => alert("Failed to update scope: " + err.message));
    });
  }

  // Admin Reset PRs
  const resetBtn = document.getElementById("reset-prs-btn");
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      if (!confirm("Reset all PR verification history and database tables?")) return;
      fetch("/api/reset_prs", { method: "POST" })
      .then(res => res.json())
      .then(data => {
        alert("Database successfully reset.");
        window.location.reload();
      });
    });
  }
});
