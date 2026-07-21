(function () {
    "use strict";

    var card = document.getElementById("examCard");
    if (!card) return;

    var examCode = card.dataset.examCode;
    var timeLimitSeconds = parseInt(card.dataset.timeLimit, 10) || 0;

    var form = document.getElementById("examAnswerForm");
    var slides = Array.prototype.slice.call(document.querySelectorAll(".question-slide"));
    var progressLabel = document.getElementById("questionProgress");
    var prevBtn = document.getElementById("prevQuestionBtn");
    var nextBtn = document.getElementById("nextQuestionBtn");
    var submitBtn = document.getElementById("submitExamBtn");
    var autoSubmittedField = document.getElementById("autoSubmittedField");
    var warningCountEl = document.getElementById("warningCount");
    var maxWarningsEl = document.querySelector("[data-max-warnings]");
    var maxWarnings = maxWarningsEl ? parseInt(maxWarningsEl.dataset.maxWarnings, 10) || 2 : 2;
    var timerEl = document.getElementById("examTimer");
    var gate = document.getElementById("fullscreenGate");
    var enterFullscreenBtn = document.getElementById("enterFullscreenBtn");

    var currentIndex = 0;
    var hasEnteredFullscreenOnce = false;
    var warningCount = warningCountEl ? parseInt(warningCountEl.textContent, 10) || 0 : 0;
    var submitted = false;
    var warningInFlight = false;
    var blurTimeout = null;

    // ------------------------------------------------------------------
    // One-question-per-view navigation
    // ------------------------------------------------------------------

    function showSlide(index) {
        slides.forEach(function (slide, i) {
            slide.style.display = i === index ? "" : "none";
        });
        if (progressLabel) {
            progressLabel.textContent = "Question " + (index + 1) + " of " + slides.length;
        }
        if (prevBtn) prevBtn.disabled = index === 0;
        var isLast = index === slides.length - 1;
        if (nextBtn) nextBtn.style.display = isLast ? "none" : "";
        if (submitBtn) submitBtn.style.display = isLast ? "" : "none";
        currentIndex = index;
    }

    if (nextBtn) {
        nextBtn.addEventListener("click", function () {
            if (currentIndex < slides.length - 1) showSlide(currentIndex + 1);
        });
    }
    if (prevBtn) {
        prevBtn.addEventListener("click", function () {
            if (currentIndex > 0) showSlide(currentIndex - 1);
        });
    }

    if (slides.length > 0) showSlide(0);

    // ------------------------------------------------------------------
    // Countdown timer
    // ------------------------------------------------------------------

    var remainingSeconds = timeLimitSeconds;

    function formatTime(totalSeconds) {
        var m = Math.max(0, Math.floor(totalSeconds / 60));
        var s = Math.max(0, Math.floor(totalSeconds % 60));
        return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
    }

    var timerHandle = null;
    if (timeLimitSeconds > 0 && timerEl) {
        timerEl.textContent = formatTime(remainingSeconds);
        timerHandle = setInterval(function () {
            remainingSeconds -= 1;
            timerEl.textContent = formatTime(remainingSeconds);
            if (remainingSeconds <= 0) {
                clearInterval(timerHandle);
                forceSubmit();
            }
        }, 1000);
    }

    // ------------------------------------------------------------------
    // Fullscreen gate
    // ------------------------------------------------------------------

    function isFullscreen() {
        return !!(document.fullscreenElement || document.webkitFullscreenElement);
    }

    function requestFullscreen() {
        var el = document.documentElement;
        var request = el.requestFullscreen || el.webkitRequestFullscreen;
        if (request) {
            request.call(el).catch(function () {
                /* user dismissed the browser's own permission prompt; gate stays visible */
            });
        }
    }

    function showGate() {
        if (gate) gate.style.display = "flex";
    }

    function hideGate() {
        if (gate) gate.style.display = "none";
    }

    if (enterFullscreenBtn) {
        enterFullscreenBtn.addEventListener("click", function () {
            requestFullscreen();
        });
    }

    document.addEventListener("fullscreenchange", function () {
        if (isFullscreen()) {
            hasEnteredFullscreenOnce = true;
            hideGate();
        } else {
            showGate();
            if (hasEnteredFullscreenOnce && !submitted) {
                flagWarning();
            }
        }
    });
    document.addEventListener("webkitfullscreenchange", function () {
        document.dispatchEvent(new Event("fullscreenchange"));
    });

    // ------------------------------------------------------------------
    // Tab-switch / window-blur detection
    // ------------------------------------------------------------------

    document.addEventListener("visibilitychange", function () {
        if (document.hidden && hasEnteredFullscreenOnce && !submitted) {
            flagWarning();
        }
    });

    window.addEventListener("blur", function () {
        if (!hasEnteredFullscreenOnce || submitted) return;
        if (blurTimeout) clearTimeout(blurTimeout);
        blurTimeout = setTimeout(function () {
            if (!document.hasFocus() && !submitted) flagWarning();
        }, 250);
    });

    // Block the right-click context menu (copy/inspect shortcuts).
    document.addEventListener("contextmenu", function (event) {
        event.preventDefault();
    });

    // ------------------------------------------------------------------
    // Warnings + auto-submit
    // ------------------------------------------------------------------

    function flagWarning() {
        if (submitted || !examCode || warningInFlight) return;
        warningInFlight = true;
        fetch("/exams/" + encodeURIComponent(examCode) + "/warning", {
            method: "POST",
        })
            .then(function (response) {
                return response.ok ? response.json() : null;
            })
            .then(function (data) {
                if (data && typeof data.security_warnings === "number") {
                    warningCount = data.security_warnings;
                } else {
                    warningCount += 1;
                }
                if (warningCountEl) warningCountEl.textContent = String(warningCount);
                if (warningCount >= maxWarnings) {
                    forceSubmit();
                }
            })
            .catch(function () {
                /* network hiccup — don't block the student on a failed warning ping */
            })
            .finally(function () {
                warningInFlight = false;
            });
    }

    function forceSubmit() {
        if (submitted || !form) return;
        submitted = true;
        if (timerHandle) clearInterval(timerHandle);
        if (autoSubmittedField) autoSubmittedField.value = "1";
        if (typeof form.requestSubmit === "function") {
            form.requestSubmit();
        } else {
            form.submit();
        }
    }

    // Confirm before the browser's own back/refresh/close, since that
    // would otherwise silently drop the in-progress attempt.
    window.addEventListener("beforeunload", function (event) {
        if (!submitted) {
            event.preventDefault();
            event.returnValue = "";
        }
    });
})();