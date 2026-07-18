// ── File Preview Modal Manager ────────────────────────────────────

function openPreviewModal(previewUrl, filename, lastName, firstName, downloadUrl) {
    const modal = document.getElementById('previewModal');
    const contentArea = document.getElementById('previewContentArea');
    
    // Set header info
    document.getElementById('previewFilename').textContent = filename;
    document.getElementById('previewStudent').textContent = `${lastName}, ${firstName}`;
    document.getElementById('previewDownloadBtn').href = downloadUrl;
    
    // Show loading state
    contentArea.innerHTML = `
        <div class="preview-loading">
            <div class="spinner"></div>
            <p>Loading preview...</p>
        </div>
    `;
    modal.classList.add('modal-open');
    
    // Fetch preview content
    fetchPreviewContent(previewUrl, contentArea);
}

function closePreviewModal() {
    document.getElementById('previewModal').classList.remove('modal-open');
}

async function fetchPreviewContent(previewUrl, contentArea) {
    try {
        const response = await fetch(previewUrl);
        
        if (!response.ok) {
            if (response.status === 415) {
                showPreviewError(contentArea, 'This file type cannot be previewed.');
            } else {
                showPreviewError(contentArea, 'Failed to load preview.');
            }
            return;
        }
        
        // Check content type
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
            // Text/code file - JSON response with content
            const data = await response.json();
            renderTextPreview(data, contentArea);
        } else if (contentType && (contentType.includes('image/') || contentType.includes('application/pdf'))) {
            // Image or PDF - render directly
            const blob = await response.blob();
            renderDirectPreview(blob, contentType, contentArea);
        } else {
            showPreviewError(contentArea, 'Unsupported file format.');
        }
    } catch (error) {
        console.error('Error loading preview:', error);
        showPreviewError(contentArea, 'Failed to load preview. Please try downloading instead.');
    }
}

function renderTextPreview(data, contentArea) {
    const { content, language } = data;
    
    // Create a padded wrapper and code block with syntax highlighting
    const wrapper = document.createElement('div');
    wrapper.className = 'preview-code-wrapper';

    const codeBlock = document.createElement('pre');
    codeBlock.className = 'preview-code-block';

    const codeElement = document.createElement('code');
    codeElement.textContent = content;
    codeElement.className = `language-${language}`;
    codeBlock.appendChild(codeElement);

    // allow vertical scrolling within the wrapper for long files
    wrapper.appendChild(codeBlock);

    contentArea.innerHTML = '';
    contentArea.appendChild(wrapper);

    // Apply syntax highlighting if highlight.js is available
    if (typeof hljs !== 'undefined') {
        try {
            hljs.highlightElement(codeElement);
        } catch (e) {
            console.warn('Highlight failed', e);
        }
    }
}

function renderDirectPreview(blob, contentType, contentArea) {
    const url = URL.createObjectURL(blob);
    contentArea.innerHTML = '';
    
    if (contentType.includes('application/pdf')) {
        // Embed PDF
        const embed = document.createElement('embed');
        embed.src = url;
        embed.type = 'application/pdf';
        embed.className = 'preview-embed';
        contentArea.appendChild(embed);
    } else if (contentType.includes('image/')) {
        // Display image
        const img = document.createElement('img');
        img.src = url;
        img.className = 'preview-image';
        img.alt = 'Preview';
        contentArea.appendChild(img);
    }
}

function showPreviewError(contentArea, message) {
    contentArea.innerHTML = `
        <div class="preview-error">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}
