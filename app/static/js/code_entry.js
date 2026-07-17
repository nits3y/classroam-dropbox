const codeInput = document.getElementById("code");
const continueBtn = document.getElementById("continue-btn");
const errorMsg = document.getElementById("error-msg");
const form = document.getElementById("code-form");

codeInput.addEventListener("input", () => {
    continueBtn.disabled = codeInput.value.trim() === "";
});

form.addEventListener("submit", (e) => {
    e.preventDefault();
    const code = codeInput.value.trim();
    // Placeholder for now — this is where we'll check the code
    // against the database once that part is built.
    console.log("Code entered:", code);
});