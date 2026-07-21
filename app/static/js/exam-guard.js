/**
 * exam-guard.js
 *
 * Anti-cheat guard for the student exam-taking page (ported from Fucursa's
 * src/app/exam/[id]/page.tsx fullscreen/visibility handling, rewritten as
 * plain JS against the Flask routes in app/exams.py).
 *
 * Public API (used by take_exam.html):
 *   ExamGuard.init({
 *     warningUrl:   '/exams/<code>/warning',
 *     maxWarnings:   3,
 *     onWarning:    function(count, reason) {},  // called after each violation
 *     onAutoSubmit: function() {},                // called once max is exceeded
 *   });
 *   ExamGuard.enterFullscreen();   // call from a user-gesture (Start button)
 *   ExamGuard.markStarted();       // begin monitoring
 *   ExamGuard.markSubmitting();    // call right before a normal submit
 *   ExamGuard.exitFullscreen();
 */
(function (window, document) {
  "use strict";

  const ExamGuard = {
    _opts: null,
    _warnings: 0,
    _started: false,
    _reenteringFullscreen: false,
    _submitting: false,

    init(opts) {
      this._opts = Object.assign(
        {
          warningUrl: null,
          maxWarnings: 3,
          onWarning: function () {},
          onAutoSubmit: function () {},
        },
        opts || {}
      );

      document.addEventListener("visibilitychange", this._handleVisibilityChange.bind(this));
      document.addEventListener("fullscreenchange", this._handleFullscreenChange.bind(this));
      document.addEventListener("webkitfullscreenchange", this._handleFullscreenChange.bind(this));
      document.addEventListener("keydown", this._handleKeyDown.bind(this), true);
      document.addEventListener("contextmenu", this._handleRightClick.bind(this));
      window.addEventListener("blur", this._handleWindowBlur.bind(this));
    },

    markStarted() {
      this._started = true;
    },

    markSubmitting() {
      this._submitting = true;
    },

    async enterFullscreen() {
      try {
        if (document.fullscreenElement) return true;
        const el = document.documentElement;
        if (el.requestFullscreen) {
          await el.requestFullscreen();
        } else if (el.webkitRequestFullscreen) {
          await el.webkitRequestFullscreen();
        } else if (el.msRequestFullscreen) {
          await el.msRequestFullscreen();
        } else {
          console.warn("Fullscreen API not supported in this browser.");
          return false;
        }
        return true;
      } catch (err) {
        console.error("Failed to enter fullscreen:", err);
        return false;
      }
    },

    async exitFullscreen() {
      try {
        if (document.fullscreenElement && document.exitFullscreen) {
          await document.exitFullscreen();
        } else if (document.webkitFullscreenElement && document.webkitExitFullscreen) {
          await document.webkitExitFullscreen();
        }
      } catch (err) {
        console.error("Failed to exit fullscreen:", err);
      }
    },

    async _reenterFullscreen() {
      this._reenteringFullscreen = true;
      const ok = await this.enterFullscreen();
      window.setTimeout(() => {
        this._reenteringFullscreen = false;
      }, 400);
      return ok;
    },

    _handleVisibilityChange() {
      if (!this._started || this._submitting) return;
      if (document.hidden) {
        this._recordViolation("Switched tabs or minimized the window");
      }
    },

    _handleWindowBlur() {
      if (!this._started || this._submitting) return;
      if (document.fullscreenElement || document.webkitFullscreenElement) {
        this._recordViolation("Window lost focus");
      }
    },

    _handleFullscreenChange() {
      const isFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement);
      if (isFullscreen) return;
      if (!this._started || this._reenteringFullscreen || this._submitting) return;
      this._recordViolation("Exited fullscreen mode");
      this._reenterFullscreen();
    },

    _handleKeyDown(event) {
      if (!this._started || this._submitting) return;
      const key = event.key;
      const blockedCombos =
        (event.altKey && key === "Tab") ||
        (event.metaKey && key === "Tab") ||
        (event.ctrlKey && ["t", "n", "w"].includes((key || "").toLowerCase())) ||
        key === "F11" ||
        key === "Escape" ||
        (event.ctrlKey && event.shiftKey && (key === "I" || key === "J" || key === "C")) ||
        key === "F12";

      if (blockedCombos) {
        event.preventDefault();
        event.stopPropagation();
        this._recordViolation("Attempted a blocked keyboard shortcut");
      }
    },

    _handleRightClick(event) {
      if (!this._started || this._submitting) return;
      event.preventDefault();
    },

    _recordViolation(reason) {
      this._warnings += 1;
      console.warn("Exam security warning:", reason, "(" + this._warnings + ")");

      if (this._opts.warningUrl) {
        fetch(this._opts.warningUrl, {
          method: "POST",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        })
          .then((res) => (res.ok ? res.json() : null))
          .then((data) => {
            if (data && typeof data.security_warnings === "number") {
              this._warnings = data.security_warnings;
            }
            this._opts.onWarning(this._warnings, reason);
            if (this._warnings >= this._opts.maxWarnings) {
              this._submitting = true;
              this._opts.onAutoSubmit();
            }
          })
          .catch((err) => console.error("Failed to report exam warning:", err));
      } else {
        this._opts.onWarning(this._warnings, reason);
        if (this._warnings >= this._opts.maxWarnings) {
          this._submitting = true;
          this._opts.onAutoSubmit();
        }
      }
    },
  };

  window.ExamGuard = ExamGuard;
})(window, document);