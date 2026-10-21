// ContextGuard Dashboard Client Scripts

document.addEventListener("DOMContentLoaded", function () {
  // PR Submission Form
  const prForm = document.getElementById("pr-submit-form");
  if (prForm) {
    prForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const input = document.getElementById("pr-url-input");
      const btn = document.getElementById("pr-submit-btn");
      const statusDiv = document.getElementById("submit-status");

      if (!input || !input.value.trim()) return;

      btn.disabled = true;
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
        btn.innerText = "Verify PR";
        if (data.status === "COMPLETED" || data.status === "CACHED") {
          window.location.href = `/developer?pr_id=${encodeURIComponent(data.pr_id)}`;
        } else if (data.status === "FAIL_OPEN") {
          alert(`Fail-Open Triggered: ${data.decision_reason}`);
          window.location.href = `/developer?pr_id=${encodeURIComponent(data.pr_id)}`;
        } else {
          alert(`Error: ${data.error || "Verification failed."}`);
          if (statusDiv) statusDiv.innerText = "";
        }
      })
      .catch(err => {
        btn.disabled = false;
        btn.innerText = "Verify PR";
        alert(`Request failed: ${err.message}`);
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
