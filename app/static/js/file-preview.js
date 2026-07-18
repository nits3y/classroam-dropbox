// ── File Preview Modal Manager ────────────────────────────────────

function openPreviewModal(previewUrl, filename, lastName, firstName, downloadUrl, fileClass) {
    const modal = document.getElementById('previewModal');
    const contentArea = document.getElementById('previewContentArea');
    
    // Set header info
    document.getElementById('previewFilename').textContent = filename;
    document.getElementById('previewStudent').textContent = `${lastName}, ${firstName}`;
    document.getElementById('previewDownloadBtn').href = downloadUrl;
    
    // Show loading state (distinct for office conversions)
    const loadingText = fileClass === 'office' ? 'Converting document...' : 'Loading preview...';
    contentArea.innerHTML = `
        <div class="preview-loading">
            <div class="spinner"></div>
            <p>${loadingText}</p>
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
            if (data && data.type === 'error') {
                showPreviewError(contentArea, data.message || 'Preview unavailable.');
            } else {
                renderTextPreview(data, contentArea);
            }
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
    // Create the outer wrapper (non-scrolling) and an inner scrollable area
    const wrapper = document.createElement('div');
    wrapper.className = 'preview-code-wrapper';

    // Toolbar area (copy button)
    const toolbar = document.createElement('div');
    toolbar.className = 'preview-code-toolbar';
    const copyBtn = document.createElement('button');
    copyBtn.className = 'btn-copy';
    copyBtn.type = 'button';
    copyBtn.textContent = 'Copy Code';
    toolbar.appendChild(copyBtn);
    wrapper.appendChild(toolbar);

    // Scrollable code container
    const scrollArea = document.createElement('div');
    scrollArea.className = 'preview-code-scroll';

    const codeBlock = document.createElement('pre');
    codeBlock.className = 'preview-code-block';

    const codeElement = document.createElement('code');
    codeElement.textContent = content;
    codeElement.className = `language-${language}`;
    codeBlock.appendChild(codeElement);
    scrollArea.appendChild(codeBlock);
    wrapper.appendChild(scrollArea);

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

    // Copy button behavior: copy raw code text and show feedback
    copyBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        try {
            await navigator.clipboard.writeText(codeElement.textContent || '');
            // visual feedback
            copyBtn.classList.add('copied');
            const original = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            setTimeout(() => {
                copyBtn.classList.remove('copied');
                copyBtn.textContent = original;
            }, 2000);
        } catch (err) {
            console.error('Copy failed', err);
            // fallback: select text
            const range = document.createRange();
            range.selectNodeContents(codeElement);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        }
    });
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
