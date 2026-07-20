const fileInputsContainer = document.getElementById('fileInputsContainer');
const addFileBtn = document.getElementById('addFileBtn');
const snippetContainer = document.getElementById('snippetContainer');
const addSnippetBtn = document.getElementById('addSnippetBtn');
const submitAssignmentBtn = document.getElementById('submitAssignmentBtn');
const studentSubmissionForm = document.getElementById('studentSubmissionForm');
const submissionConfirmModal = document.getElementById('submissionConfirmModal');
const submissionConfirmText = document.getElementById('submissionConfirmText');
const cancelSubmitBtn = document.getElementById('cancelSubmitBtn');
const confirmSubmitBtn = document.getElementById('confirmSubmitBtn');
const snippetError = document.getElementById('snippetError');
let fileInputIndex = 1;

function createFileInputRow() {
    fileInputIndex += 1;
    const wrapper = document.createElement('div');
    wrapper.className = 'file-input-row';
    wrapper.innerHTML = `
        <input type="file" name="files" id="file-${fileInputIndex}" ${acceptAttribute()}>
        <button type="button" class="button secondary small remove-file-btn">Remove</button>
    `;
    wrapper.querySelector('.remove-file-btn').addEventListener('click', () => wrapper.remove());
    return wrapper;
}

function acceptAttribute() {
    const firstFileInput = fileInputsContainer.querySelector('input[type="file"]');
    return firstFileInput?.getAttribute('accept') ? `accept="${firstFileInput.getAttribute('accept')}"` : '';
}

function createSnippetBlock() {
    const wrapper = document.createElement('div');
    wrapper.className = 'snippet-block';
    wrapper.innerHTML = `
        <textarea name="snippets" rows="8" placeholder="Paste a code snippet..." required style="font-family: monospace; white-space: pre; overflow:auto;"></textarea>
        <button type="button" class="button secondary small remove-snippet-btn">Remove</button>
    `;
    wrapper.querySelector('.remove-snippet-btn').addEventListener('click', () => wrapper.remove());
    return wrapper;
}

function validateSnippets() {
    if (!snippetContainer) return true;
    const textareas = Array.from(snippetContainer.querySelectorAll('textarea[name="snippets"]'));
    const invalid = textareas.some((textarea) => !textarea.value.trim());
    snippetError.style.display = invalid ? 'block' : 'none';
    snippetError.textContent = invalid ? 'Every code snippet must contain text before submission.' : '';
    return !invalid;
}

function countFileInputs() {
    return Array.from(fileInputsContainer.querySelectorAll('input[type="file"]')).filter((input) => input.files.length > 0).length;
}

function countTextSnippets() {
    if (!snippetContainer) return 0;
    return Array.from(snippetContainer.querySelectorAll('textarea[name="snippets"]')).filter((textarea) => textarea.value.trim()).length;
}

function openSubmissionConfirmModal(event) {
    event.preventDefault();

    if (!validateSnippets()) {
        return;
    }

    const filesCount = Array.from(fileInputsContainer.querySelectorAll('input[type="file"]')).filter((input) => input.files.length > 0).length;
    const snippetsCount = countTextSnippets();
    if (filesCount === 0 && snippetsCount === 0) {
        alert('Please add at least one file or plain text snippet before submitting.');
        return;
    }

    submissionConfirmText.textContent = `Are you sure you want to submit? You are submitting ${filesCount} file(s) and ${snippetsCount} text snippet(s).`;
    submissionConfirmModal.classList.add('modal-open');
    document.body.classList.add('modal-open');
}

function closeSubmissionConfirmModal() {
    submissionConfirmModal.classList.remove('modal-open');
    document.body.classList.remove('modal-open');
}

function submitForm() {
    studentSubmissionForm.submit();
}

function attachSnippetValidation() {
    if (!snippetContainer) return;
    snippetContainer.addEventListener('input', validateSnippets);
}

if (addFileBtn) {
    addFileBtn.addEventListener('click', () => {
        fileInputsContainer.appendChild(createFileInputRow());
    });
}

if (addSnippetBtn) {
    addSnippetBtn.addEventListener('click', () => {
        snippetContainer.appendChild(createSnippetBlock());
    });
}

if (submitAssignmentBtn) {
    submitAssignmentBtn.addEventListener('click', openSubmissionConfirmModal);
}

if (studentSubmissionForm) {
    studentSubmissionForm.addEventListener('submit', openSubmissionConfirmModal);
}

if (cancelSubmitBtn) {
    cancelSubmitBtn.addEventListener('click', closeSubmissionConfirmModal);
}

if (confirmSubmitBtn) {
    confirmSubmitBtn.addEventListener('click', submitForm);
}

attachSnippetValidation();

document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && submissionConfirmModal.classList.contains('modal-open')) {
        closeSubmissionConfirmModal();
    }
});
