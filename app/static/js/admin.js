document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
        const value = button.dataset.copy;
        try {
            await navigator.clipboard.writeText(value);
            button.textContent = "Copied";
            setTimeout(() => {
                button.textContent = "Copy";
            }, 1200);
        } catch {
            button.textContent = value;
        }
    });
});
