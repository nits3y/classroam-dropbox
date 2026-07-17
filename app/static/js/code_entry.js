const codeInput = document.getElementById("code");
const continueBtn = document.getElementById("continue-btn");
const errorMsg = document.getElementById("error-msg");
const form = document.getElementById("code-form");

function updateButtonState() {
    continueBtn.disabled = codeInput.value.trim() === "";
}

codeInput.addEventListener("input", () => {
    updateButtonState();
    errorMsg.style.display = "none";
});

form.addEventListener("submit", (event) => {
    if (codeInput.value.trim() === "") {
        event.preventDefault();
        errorMsg.textContent = "Enter the code your teacher gave you.";
        errorMsg.style.display = "block";
    }
});

updateButtonState();
