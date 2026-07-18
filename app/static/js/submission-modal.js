// ── Submission Modal Manager ──────────────────────────────────────
let currentSubmissionId = null;

// Open submission modal and load data
async function openSubmissionModal(submissionId) {
    currentSubmissionId = submissionId;
    try {
        const response = await fetch(`/admin/submissions/${submissionId}/api`);
        if (!response.ok) throw new Error('Failed to fetch submission details');
        
        const data = await response.json();
        populateSubmissionModal(data);
        document.getElementById('submissionModal').classList.add('modal-open');
    } catch (error) {
        console.error('Error loading submission:', error);
        alert('Failed to load submission details');
    }
}

function closeSubmissionModal() {
    document.getElementById('submissionModal').classList.remove('modal-open');
    currentSubmissionId = null;
}

function populateSubmissionModal(data) {
    // Set header information
    document.getElementById('modalClassname').textContent = data.class_name;
    document.getElementById('modalTitle').textContent = data.title;
    document.getElementById('modalDeadline').textContent = formatDeadline(data.deadline);
    document.getElementById('modalCode').textContent = data.code;
    document.getElementById('modalStatus').textContent = data.status.replace('-', ' ');
    document.getElementById('modalStatus').className = `badge ${data.status}`;
    
    // Set description (show only if not empty)
    const descEl = document.getElementById('modalDescription');
    if (data.description) {
        descEl.textContent = data.description;
        descEl.style.display = 'block';
    } else {
        descEl.style.display = 'none';
    }
    
    // Set action button URLs
    document.getElementById('downloadAllBtn').href = data.download_all_url;
    document.getElementById('exportCsvBtn').href = data.export_csv_url;
    
    // Update copy button
    const copyBtn = document.getElementById('modalCopyBtn');
    copyBtn.dataset.copy = data.code;
    
    // Populate student rows
    const tbody = document.getElementById('modalStudentRows');
    if (data.students.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="6" class="empty-state" style="padding: 2rem;">No files submitted yet. Waiting for students…</td></tr>';
    } else {
        tbody.innerHTML = data.students.map(student => `
            <tr>
                <td class="col-last"><strong>${escapeHtml(student.last_name)}</strong></td>
                <td class="col-first">${escapeHtml(student.first_name)}</td>
                <td class="file-col">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 8px; color: #64748b;">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    <span class="file-name" title="${escapeHtml(student.filename)}">${escapeHtml(student.filename)}</span>
                </td>
                <td class="col-submitted">
                    ${escapeHtml(formatDeadline(student.submitted_at))}
                    ${student.is_late ? '<span class="late-tag">Late</span>' : ''}
                </td>
                <td class="actions-col">
                    ${student.can_preview ? `<button class="btn-primary" onclick="openPreviewModal('${student.preview_url}', '${escapeHtml(student.filename)}', '${escapeHtml(student.last_name)}', '${escapeHtml(student.first_name)}', '${student.download_url}', '${student.file_class}');">View</button>` : ''}
                    <a href="${student.download_url}" class="btn-secondary-outline">Download</a>
                </td>
            </tr>
        `).join('');
    }
}

// Open edit modal
function openEditModal() {
    if (!currentSubmissionId) return;
    
    // Get current data from the modal
    const title = document.getElementById('modalTitle').textContent;
    const deadline = document.getElementById('modalDeadline').textContent;
    const description = document.getElementById('modalDescription').textContent;
    
    // Populate form with current values
    document.getElementById('editTitle').value = title;
    document.getElementById('editDescription').value = description;
    
    // Convert deadline string to datetime-local format
    // The deadline is displayed as formatted text, we need to convert it back
    // For now, we'll fetch the raw value from the API
    const isoDeadline = getIsoDeadlineFromModal();
    document.getElementById('editDeadline').value = isoDeadline;
    
    document.getElementById('editModal').classList.add('modal-open');
}

function closeEditModal() {
    document.getElementById('editModal').classList.remove('modal-open');
}

function getIsoDeadlineFromModal() {
    // Since we don't have the ISO format readily available, we'll make a small request
    // Or better, we can store it in a data attribute in the openSubmissionModal function
    // For now, return a placeholder - we'll improve this
    const input = document.getElementById('editDeadline');
    return input.value || '';
}

async function handleEditSubmissionSubmit(e) {
    e.preventDefault();
    
    if (!currentSubmissionId) return;
    
    const formData = new FormData(document.getElementById('editSubmissionForm'));
    
    try {
        const response = await fetch(`/admin/submissions/${currentSubmissionId}/update`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to update submission');
        }
        
        const result = await response.json();
        
        // Close edit modal
        closeEditModal();
        
        // Reload the submission modal with updated data
        await openSubmissionModal(currentSubmissionId);
        
        // Show success message
        showSuccessMessage('Submission updated successfully');
    } catch (error) {
        console.error('Error updating submission:', error);
        alert('Failed to update submission: ' + error.message);
    }
}

function showSuccessMessage(message) {
    // You can enhance this with a proper notification system
    const notification = document.createElement('div');
    notification.className = 'success-notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #10b981;
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Delete submission
let deleteSubmissionId = null;

function openDeleteConfirm() {
    if (!currentSubmissionId) return;
    deleteSubmissionId = currentSubmissionId;
    const title = document.getElementById('modalTitle').textContent;
    document.getElementById('deleteConfirmTitle').textContent = `Delete "${title}"?`;
    document.getElementById('deleteConfirmModal').classList.add('modal-open');
}

function closeDeleteConfirm() {
    document.getElementById('deleteConfirmModal').classList.remove('modal-open');
    deleteSubmissionId = null;
}

document.getElementById('deleteSubmissionBtn')?.addEventListener('click', openDeleteConfirm);
document.getElementById('confirmDeleteBtn')?.addEventListener('click', async function() {
    if (!deleteSubmissionId) return;
    
    try {
        const response = await fetch(`/admin/submissions/${deleteSubmissionId}/delete`, {
            method: 'POST'
        });
        
        if (response.ok) {
            closeDeleteConfirm();
            closeSubmissionModal();
            // Reload the page to refresh the submissions list
            window.location.reload();
        } else {
            throw new Error('Failed to delete submission');
        }
    } catch (error) {
        console.error('Error deleting submission:', error);
        alert('Failed to delete submission');
    }
});

// ── Event Listeners ──────────────────────────────────────────────
document.querySelectorAll('.submission-row').forEach(row => {
    row.addEventListener('click', (e) => {
        // Don't open modal if clicking on action buttons
        if (e.target.closest('button') || e.target.closest('a')) {
            return;
        }
        const submissionId = row.dataset.submissionId;
        if (submissionId) {
            openSubmissionModal(parseInt(submissionId));
        }
    });
});

// Copy to clipboard for modal code
document.getElementById('modalCopyBtn')?.addEventListener('click', async function(e) {
    e.stopPropagation();
    const value = this.dataset.copy;
    try {
        await navigator.clipboard.writeText(value);
        const original = this.innerHTML;
        this.innerHTML = 'Copied';
        setTimeout(() => {
            this.innerHTML = original;
        }, 1200);
    } catch {
        this.textContent = value;
    }
});

// Utility function to escape HTML
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Utility function to format deadline for display
function formatDeadline(isoString) {
    try {
        const date = new Date(isoString);
        const datePart = date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
        const timePart = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        return `${datePart} · ${timePart}`;
    } catch {
        return isoString;
    }
}

// Store ISO deadline in modal for later use
const originalOpenSubmissionModal = openSubmissionModal;
openSubmissionModal = async function(submissionId) {
    currentSubmissionId = submissionId;
    try {
        const response = await fetch(`/admin/submissions/${submissionId}/api`);
        if (!response.ok) throw new Error('Failed to fetch submission details');
        
        const data = await response.json();
        
        // Store ISO deadline for the edit form
        document.getElementById('editDeadline').dataset.isoDeadline = data.deadline;
        
        populateSubmissionModal(data);
        document.getElementById('submissionModal').classList.add('modal-open');
    } catch (error) {
        console.error('Error loading submission:', error);
        alert('Failed to load submission details');
    }
};

// Update the getIsoDeadlineFromModal function
function getIsoDeadlineFromModal() {
    const isoDeadline = document.getElementById('editDeadline').dataset.isoDeadline || '';
    // Convert ISO format to datetime-local format (remove seconds and timezone)
    if (isoDeadline) {
        return isoDeadline.substring(0, 16); // YYYY-MM-DDTHH:MM
    }
    return '';
}

// Add CSS animations if not already present
if (!document.getElementById('modal-animations')) {
    const style = document.createElement('style');
    style.id = 'modal-animations';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}
