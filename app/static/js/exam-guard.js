(function () {
    "use strict";

    var card = document.getElementById("examCard");
    if (!card) return;

    var examCode = card.dataset.examCode;

    var form = document.getElementById("examAnswerForm");
    var questionSlides = document.getElementById("questionSlides");
    var slides = Array.prototype.slice.call(document.querySelectorAll(".question-slide"));
    var progressLabel = document.getElementById("questionProgress");
    var prevBtn = document.getElementById("prevQuestionBtn");
    var nextBtn = document.getElementById("nextQuestionBtn");
    var submitBtn = document.getElementById("submitExamBtn");
    var autoSubmittedField = document.getElementById("autoSubmittedField");
    var warningCountEl = document.getElementById("warningCount");
    var maxWarningsEl = document.querySelector("[data-max-warnings]");
    var maxWarnings = maxWarningsEl ? parseInt(maxWarningsEl.dataset.maxWarnings, 10) || 3 : 3;
    var questionTimerRow = document.getElementById("questionTimerRow");
    var questionTimerEl = document.getElementById("questionTimer");
    var nextQuestionBtnLabel = document.getElementById("nextQuestionBtnLabel");
    var gate = document.getElementById("fullscreenGate");
    var enterFullscreenBtn = document.getElementById("enterFullscreenBtn");
    var lockedOverlay = document.getElementById("examLockedOverlay");

    [gate, document.getElementById("warningModal"), lockedOverlay].forEach(function (overlay) {
        if (overlay && overlay.parentElement !== document.body) {
            document.body.appendChild(overlay);
        }
    });

    var currentIndex = 0;
    var hasEnteredFullscreenOnce = false;
    var warningCount = warningCountEl ? parseInt(warningCountEl.textContent, 10) || 0 : 0;
    var submitted = false;
    var warningInFlight = false;
    var blurTimeout = null;
    var lastWarningMs = 0;
    var warningCooldownMs = 2000;
    var examStarted = false; // true only once the student has confirmed fullscreen at least once
    var fullscreenStartRequested = false;

    // ------------------------------------------------------------------
    // One-question-per-view navigation
    // ------------------------------------------------------------------

    function isSlideAnswered(slideEl) {
        if (!slideEl) return false;
        var checked = slideEl.querySelector('input[type="radio"]:checked, input[type="checkbox"]:checked');
        if (checked) return true;
        return Array.prototype.some.call(slideEl.querySelectorAll("input[type='text'], input[type='number'], textarea"), function (field) {
            return field.value.trim() !== "";
        });
    }

    function showSlide(index) {
        if (submitted) return;
        slides.forEach(function (slide, i) {
            slide.style.display = i === index ? "" : "none";
        });
        if (progressLabel) {
            progressLabel.textContent = "Question " + (index + 1) + " of " + slides.length;
        }
        if (prevBtn) prevBtn.disabled = index === 0;
        var isLast = index === slides.length - 1;
        if (nextBtn) nextBtn.style.display = isLast ? "none" : "";
        if (nextQuestionBtnLabel) nextQuestionBtnLabel.textContent = isSlideAnswered(slides[index]) ? "Next" : "Skip";
        if (submitBtn) submitBtn.style.display = isLast ? "" : "none";
        currentIndex = index;
        // Only run the per-question countdown once the student is actually
        // in the exam (past the fullscreen gate) — otherwise a question timer
        // could burn down while the student is still staring at the gate.
        if (examStarted) startQuestionTimer(slides[index]);
    }

    // ------------------------------------------------------------------
    // Per-question countdown (app/exams.py exam_questions.time_limit_seconds).
    // Advances to the next question automatically on expiry; this is a
    // normal pacing event, not a security violation, so it never calls
    // flagWarning().
    // ------------------------------------------------------------------

    var questionTimerHandle = null;
    var questionDeadlineMs = null;

    function stopQuestionTimer() {
        if (questionTimerHandle) {
            clearTimeout(questionTimerHandle);
            questionTimerHandle = null;
        }
        questionDeadlineMs = null;
    }

    function startQuestionTimer(slideEl) {
        stopQuestionTimer();
        if (!slideEl) return;
        var limit = parseInt(slideEl.dataset.timeLimit, 10);
        if (!limit || limit <= 0) {
            if (questionTimerRow) questionTimerRow.style.display = "none";
            return;
        }
        if (questionTimerRow) questionTimerRow.style.display = "";
        if (questionTimerRow) questionTimerRow.className = "question-timer question-timer-normal";
        questionDeadlineMs = Date.now() + limit * 1000;

        function tickQuestionTimer() {
            var remaining = Math.ceil((questionDeadlineMs - Date.now()) / 1000);
            if (questionTimerEl) questionTimerEl.textContent = formatTime(remaining);
            if (questionTimerRow) {
                var urgency = remaining <= 10 || remaining <= limit * 0.25 ? "question-timer-urgent" : remaining <= limit * 0.5 ? "question-timer-warning" : "question-timer-normal";
                questionTimerRow.className = "question-timer " + urgency;
            }
            if (remaining <= 0) {
                stopQuestionTimer();
                if (submitted) return;
                var isLast = currentIndex === slides.length - 1;
                if (isLast) {
                    if (questionTimerEl) questionTimerEl.textContent = "Time's up";
                } else {
                    showSlide(currentIndex + 1);
                }
                return;
            }
            questionTimerHandle = setTimeout(tickQuestionTimer, Math.min(1000, Math.max(100, questionDeadlineMs - Date.now())));
        }

        tickQuestionTimer();
    }

    if (nextBtn) {
        nextBtn.addEventListener("click", function () {
            if (submitted || currentIndex >= slides.length - 1) return;
            showSlide(currentIndex + 1);
        });
    }
    if (questionSlides) {
        questionSlides.addEventListener("input", function (event) {
            if (event.target.matches("input[type='text'], input[type='number'], textarea")) {
                if (nextQuestionBtnLabel) nextQuestionBtnLabel.textContent = isSlideAnswered(slides[currentIndex]) ? "Next" : "Skip";
            }
        });
        questionSlides.addEventListener("change", function (event) {
            if (event.target.matches("input[type='radio'], input[type='checkbox']")) {
                if (nextQuestionBtnLabel) nextQuestionBtnLabel.textContent = isSlideAnswered(slides[currentIndex]) ? "Next" : "Skip";
            }
        });
    }
    if (prevBtn) {
        prevBtn.addEventListener("click", function () {
            if (submitted || currentIndex <= 0) return;
            showSlide(currentIndex - 1);
        });
    }

    if (slides.length > 0) showSlide(0);
    if (!isFullscreen()) showGate();

    function formatTime(totalSeconds) {
        var m = Math.max(0, Math.floor(totalSeconds / 60));
        var s = Math.max(0, Math.floor(totalSeconds % 60));
        return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
    }

    // ------------------------------------------------------------------
    // Fullscreen gate
    //
    // IMPORTANT: browsers only allow requestFullscreen() to succeed when
    // it's called synchronously inside a real user-gesture event handler
    // (a click, a keypress, etc). Calling it from page-load script, from
    // inside a setTimeout callback, or from a fetch/promise callback will
    // silently fail in every modern browser. That's why fullscreen must
    // always be triggered from the "Enter Fullscreen" button's click
    // handler and never attempted automatically on page load.
    // ------------------------------------------------------------------

    function isFullscreen() {
        return !!(document.fullscreenElement || document.webkitFullscreenElement);
    }

    function requestFullscreen() {
        var el = document.documentElement;
        var request = el.requestFullscreen || el.webkitRequestFullscreen;
        if (request) {
            var result = request.call(el);
            if (result && typeof result.catch === "function") {
                result.catch(function () {
                    /* user dismissed the browser's own permission prompt; gate stays visible */
                });
            }
        }
    }

    function showGate() {
        if (gate) {
            gate.style.display = "flex";
            gate.classList.add("modal-open");
            document.body.classList.add("modal-open");
        }
    }

    function hideGate() {
        if (gate) {
            gate.style.display = "none";
            gate.classList.remove("modal-open");
        }
        if (
            (!warningModal || !warningModal.classList.contains("modal-open")) &&
            (!lockedOverlay || !lockedOverlay.classList.contains("modal-open"))
        ) {
            document.body.classList.remove("modal-open");
        }
    }

    function exitFullscreenIfNeeded() {
        if (!isFullscreen()) return;
        var exit = document.exitFullscreen || document.webkitExitFullscreen;
        if (exit) {
            exit.call(document).catch(function () {
                /* already exiting/exited — nothing to do */
            });
        }
    }

    // Gate is shown immediately on load. There is no auto-fullscreen
    // attempt here on purpose — see note above. The student must click
    // the button, which is a genuine user gesture and will succeed.
    if (!isFullscreen() && gate) {
        showGate();
    }

    if (enterFullscreenBtn) {
        enterFullscreenBtn.addEventListener("click", function () {
            fullscreenStartRequested = true;
            requestFullscreen();
        });
    }

    function startExamIfFocusedFullscreen() {
        if (submitted || examStarted || !fullscreenStartRequested || !isFullscreen() || !document.hasFocus()) return;
        hasEnteredFullscreenOnce = true;
        examStarted = true;
        hideGate();
        startQuestionTimer(slides[currentIndex]);
    }

    window.addEventListener("focus", function () {
        startExamIfFocusedFullscreen();
    });

    document.addEventListener("fullscreenerror", function () {
        showGate();
    });

    document.addEventListener("fullscreenchange", function () {
        if (isFullscreen()) {
            hasEnteredFullscreenOnce = true;
            window.focus();
            startExamIfFocusedFullscreen();
            if (examStarted) {
                hideGate();
            } else {
                showGate();
            }
        } else if (!submitted) {
            // Only trap/gate exits while the exam is actually in progress.
            // Once submitted is true (normal submit or forced auto-submit),
            // exiting fullscreen is expected and should be silent.
            showGate();
            if (hasEnteredFullscreenOnce) {
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
        if (document.hidden && examStarted && hasEnteredFullscreenOnce && !submitted) {
            flagWarning();
        }
    });

    window.addEventListener("blur", function () {
        if (!examStarted || !hasEnteredFullscreenOnce || submitted) return;
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
    // Warning modal
    // ------------------------------------------------------------------

    var warningModal = document.getElementById("warningModal");
    var warningMessage = document.getElementById("warningMessage");
    var warningModalClose = document.getElementById("warningModalClose");

    function showWarningModal(warningsLeft) {
        if (!warningModal || !warningMessage) return;
        warningMessage.textContent =
            warningsLeft > 0
                ? "Warning: you left fullscreen or switched away. " + warningsLeft + " warning" + (warningsLeft === 1 ? "" : "s") + " remaining."
                : "Warning: you have reached the maximum number of warnings.";
        warningModal.classList.add("modal-open");
        document.body.classList.add("modal-open");
    }

    function hideWarningModal() {
        if (!warningModal) return;
        warningModal.classList.remove("modal-open");
        document.body.classList.remove("modal-open");
    }

    if (warningModalClose) {
        warningModalClose.addEventListener("click", function () {
            hideWarningModal();
            if (!isFullscreen()) {
                showGate();
            }
        });
    }

    // ------------------------------------------------------------------
    // Warnings + auto-submit
    // ------------------------------------------------------------------

    function flagWarning() {
        var now = Date.now();
        if (submitted || !examCode || warningInFlight || now - lastWarningMs < warningCooldownMs) return;
        lastWarningMs = now;
        warningInFlight = true;
        fetch("/exams/" + encodeURIComponent(examCode) + "/warning", {
            method: "POST",
            credentials: "same-origin",
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

                if (data && data.locked) {
                    forceSubmit();
                    return;
                }

                var warningsLeft = data && typeof data.warnings_left === "number" ? data.warnings_left : maxWarnings - warningCount;
                if (warningsLeft <= 0) {
                    forceSubmit();
                } else {
                    showWarningModal(warningsLeft);
                }
            })
            .catch(function () {
                /* network hiccup — don't block the student on a failed warning ping */
            })
            .finally(function () {
                warningInFlight = false;
            });
    }

    function disableExamInteraction() {
        if (questionSlides) {
            questionSlides.style.display = "none";
        }
        if (nextBtn) {
            nextBtn.disabled = true;
        }
        if (prevBtn) {
            prevBtn.disabled = true;
        }
        if (submitBtn) {
            submitBtn.disabled = true;
        }
        if (form) {
            form.style.pointerEvents = "none";
            form.style.opacity = "0.7";
        }
    }

    function forceSubmit() {
        if (submitted || !form) return;
        submitted = true;
        if (lockedOverlay) {
            lockedOverlay.classList.add("modal-open");
            document.body.classList.add("modal-open");
        }
        stopQuestionTimer();
        exitFullscreenIfNeeded();
        hideGate();
        disableExamInteraction();
        if (autoSubmittedField) autoSubmittedField.value = "1";
        if (typeof form.requestSubmit === "function") {
            form.requestSubmit();
        } else {
            form.submit();
        }
    }

    // Normal path: student clicks "Submit exam" on the last question.
    if (form) {
        form.addEventListener("submit", function () {
            if (submitted) return; // already handled by forceSubmit
            submitted = true;
            stopQuestionTimer();
            exitFullscreenIfNeeded();
            hideGate();
        });
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
