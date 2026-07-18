// ── Clickable rows ─────────────────────────────────────────────
document.querySelectorAll("tr.clickable-row").forEach((row) => {
    row.addEventListener("click", (e) => {
        // Don't navigate if the click was on a button, link, or interactive element
        if (e.target.closest("button") || e.target.closest("a") || e.target.closest(".copy-btn")) {
            return;
        }
        const href = row.dataset.href;
        if (href) {
            window.location.href = href;
        }
    });
});

// ── Copy to clipboard ──────────────────────────────────────────
document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async (e) => {
        e.stopPropagation();
        const value = button.dataset.copy;
        try {
            await navigator.clipboard.writeText(value);
            const original = button.innerHTML;
            button.innerHTML = "Copied";
            setTimeout(() => {
                button.innerHTML = original;
            }, 1200);
        } catch {
            button.textContent = value;
        }
    });
});