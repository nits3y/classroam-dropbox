/**
 * code_entry.js
 *
 * Auto-routing code entry page. Calls POST /api/access-code/verify
 * to determine whether the code is for a submission or an exam,
 * then redirects automatically. Shows loading spinner and inline
 * error messages — no page reload required.
 */
(function () {
  "use strict";

  var codeInput = document.getElementById("code");
  var continueBtn = document.getElementById("continue-btn");
  var errorMsg = document.getElementById("error-msg");
  var btnText = document.getElementById("btn-text");
  var btnSpinner = document.getElementById("btn-spinner");
  var loading = false;

  /** Enable/disable the button based on input content and loading state. */
  function updateButtonState() {
    continueBtn.disabled = loading || codeInput.value.trim() === "";
  }

  /** Show an inline error message below the input. */
  function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.style.display = "block";
  }

  /** Hide the inline error message. */
  function hideError() {
    errorMsg.textContent = "";
    errorMsg.style.display = "none";
  }

  /** Set loading state: disable button, show spinner, hide label. */
  function setLoading(state) {
    loading = state;
    if (state) {
      btnText.style.display = "none";
      btnSpinner.style.display = "inline";
    } else {
      btnText.style.display = "inline";
      btnSpinner.style.display = "none";
    }
    updateButtonState();
  }

  /** Make the API call and handle the response. */
  function verifyCode(code) {
    hideError();
    setLoading(true);

    fetch("/api/access-code/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code }),
    })
      .then(function (res) {
        if (!res.ok) throw new Error("Server error (" + res.status + ")");
        return res.json();
      })
      .then(function (data) {
        setLoading(false);

        if (data.found && data.redirect) {
          // Successful verification — redirect to the appropriate page
          window.location.href = data.redirect;
        } else {
          // Show the error returned by the API
          showError(data.error || "Invalid or expired code. Please check and try again.");
          codeInput.focus();
        }
      })
      .catch(function (err) {
        setLoading(false);
        showError("Connection error. Please try again.");
        console.error("Code verification failed:", err);
      });
  }

  // ── Event listeners ──────────────────────────────────────────────

  codeInput.addEventListener("input", function () {
    updateButtonState();
    hideError();
  });

  // Handle Enter key in the input field
  codeInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !continueBtn.disabled) {
      event.preventDefault();
      var code = codeInput.value.trim();
      if (code) verifyCode(code);
    }
  });

  continueBtn.addEventListener("click", function () {
    var code = codeInput.value.trim();
    if (code && !loading) verifyCode(code);
  });

  // Initial state
  updateButtonState();
})();