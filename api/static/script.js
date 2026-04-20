document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const generateBtn = document.getElementById('generate-btn');
    const sendBtn = document.getElementById('send-btn');
    const promptInput = document.getElementById('prompt');

    const subjectInput = document.getElementById('email-subject');
    const bodyArea = document.getElementById('email-body');
    const loader = document.getElementById('loader');
    const btnText = document.getElementById('btn-text');
    const recipientInput = document.getElementById('recipient-input');
    const addRecipientBtn = document.getElementById('add-recipient');
    const recipientChips = document.getElementById('recipient-chips');
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const fileListDisplay = document.getElementById('file-list');
    const excelBtn = document.getElementById('excel-btn');
    const excelInput = document.getElementById('excel-input');
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toast-msg');
    const toastIcon = document.getElementById('toast-icon');
    const copyBtn = document.getElementById('copy-btn');

    let recipients = [];
    let attachedFiles = [];
    let toastTimeout = null;

    // --- Notifications ---
    function showToast(message, type = 'success') {
        if (toastTimeout) {
            clearTimeout(toastTimeout);
        }

        toastMsg.textContent = message;
        toastIcon.className = 'toast-icon ' + (type === 'success' ? 'toast-success' : 'toast-error');
        toastIcon.innerHTML = type === 'success'
            ? '<i class="fas fa-check" style="color:white;font-size:0.8rem;"></i>'
            : '<i class="fas fa-times" style="color:white;font-size:0.8rem;"></i>';

        toast.classList.add('show');
        toastTimeout = setTimeout(() => toast.classList.remove('show'), 3500);
    }

    // --- File Handling ---
    dropZone.addEventListener('click', (e) => {
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFiles(e.target.files);
        }
        fileInput.value = ''; 
    });

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, e => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    ['dragenter', 'dragover'].forEach(evt => {
        dropZone.addEventListener(evt, () => dropZone.classList.add('drag-active'));
    });
    ['dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, () => dropZone.classList.remove('drag-active'));
    });

    dropZone.addEventListener('drop', e => handleFiles(e.dataTransfer.files));

    function handleFiles(files) {
        const MAX_TOTAL_SIZE = 20 * 1024 * 1024; 
        let currentTotalSize = attachedFiles.reduce((sum, f) => sum + f.size, 0);
        let addedCount = 0;

        for (let file of files) {
            if (currentTotalSize + file.size > MAX_TOTAL_SIZE) {
                showToast(`Cannot add "${file.name}". Size limit exceeded.`, 'error');
                continue;
            }
            if (!attachedFiles.find(f => f.name === file.name && f.size === file.size)) {
                attachedFiles.push(file);
                currentTotalSize += file.size;
                addedCount++;
            }
        }

        renderFileList();
        if (addedCount > 0) {
            showToast(`${addedCount} file(s) attached`);
        }
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }

    function renderFileList() {
        fileListDisplay.innerHTML = attachedFiles.map((file, index) => `
            <div class="file-pill">
                <span class="file-pill-name">
                    <i class="fas fa-file" style="margin-right:8px;color:var(--primary);"></i>
                    ${escapeHtml(file.name)}
                    <small style="color:var(--text-muted);margin-left:4px;">(${formatFileSize(file.size)})</small>
                </span>
                <i class="fas fa-times file-remove-btn" data-index="${index}"></i>
            </div>
        `).join('');

        fileListDisplay.querySelectorAll('.file-remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                attachedFiles.splice(index, 1);
                renderFileList();
            });
        });
    }

    // --- Recipient Management ---
    function addRecipient(email) {
        email = email.trim().toLowerCase();
        if (!email) return;

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            showToast('Invalid email address format', 'error');
            return;
        }

        if (recipients.includes(email)) {
            showToast('Email already in list', 'error');
            return;
        }

        recipients.push(email);
        renderChips();
        recipientInput.value = '';
        validateSendStatus();
    }

    addRecipientBtn.addEventListener('click', () => addRecipient(recipientInput.value));

    recipientInput.addEventListener('keypress', e => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addRecipient(recipientInput.value);
        }
    });

    function renderChips() {
        recipientChips.innerHTML = recipients.map((email, index) => `
            <div class="mail-chip">
                <span>${escapeHtml(email)}</span>
                <i class="fas fa-close chip-remove-btn" data-index="${index}"></i>
            </div>
        `).join('');

        recipientChips.querySelectorAll('.chip-remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                recipients.splice(index, 1);
                renderChips();
                validateSendStatus();
            });
        });
    }

    // --- Excel Extraction ---
    excelBtn.addEventListener('click', () => excelInput.click());

    excelInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        showToast('Processing document...');
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/extract-emails', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (response.ok) {
                const newEmails = data.emails.filter(email => !recipients.includes(email.toLowerCase()));
                if (newEmails.length > 0) {
                    recipients.push(...newEmails.map(e => e.toLowerCase()));
                    renderChips();
                    validateSendStatus();
                    showToast(`Found ${newEmails.length} new recipient(s)`);
                } else {
                    showToast('No new emails found', 'warning');
                }
            } else {
                showToast(data.detail || 'Extraction failed', 'error');
            }
        } catch (err) {
            showToast('Connection failed during extraction', 'error');
        } finally {
            excelInput.value = ''; 
        }
    });

    function validateSendStatus() {
        const hasBody = bodyArea.innerText.trim().length > 0;
        const hasSubject = subjectInput.value.trim().length > 0;
        const hasRecipients = recipients.length > 0;
        sendBtn.disabled = !(hasBody && hasSubject && hasRecipients);
    }

    // --- AI Generation ---
    generateBtn.addEventListener('click', async () => {
        const prompt = promptInput.value.trim();
        if (!prompt) return showToast('Please enter campaign intent', 'error');

        generateBtn.disabled = true;
        loader.classList.remove('hidden');
        btnText.textContent = 'Launching AI...';

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });

            const data = await response.json();
            
            if (response.ok) {
                subjectInput.value = data.subject || '';
                bodyArea.innerText = data.body || '';
                showToast('Campaign drafted successfully');
                validateSendStatus();
                
                // Smooth scroll to editor on mobile
                if (window.innerWidth < 1200) {
                    document.querySelector('.editor-container').scrollIntoView({ behavior: 'smooth' });
                }
            } else {
                showToast(data.detail || 'AI Generation failed', 'error');
            }
        } catch (err) {
            showToast('System offline. Check connection.', 'error');
        } finally {
            generateBtn.disabled = false;
            loader.classList.add('hidden');
            btnText.textContent = 'Craft Content';
        }
    });

    // --- Sending ---
    sendBtn.addEventListener('click', async () => {
        const subject = subjectInput.value.trim();
        const body = bodyArea.innerText.trim();

        sendBtn.disabled = true;
        const originalHTML = sendBtn.innerHTML;
        sendBtn.innerHTML = '<div class="loader" style="width:18px;height:18px;border-width:2px;"></div> <span>Launching...</span>';

        const formData = new FormData();
        formData.append('subject', subject);
        formData.append('body', body);
        formData.append('recipients', JSON.stringify(recipients));
        attachedFiles.forEach(f => formData.append('attachments', f));

        try {
            const response = await fetch('/api/send', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (response.ok) {
                showToast(data.message || 'Mission successful. Emails sent.');
            } else {
                showToast(data.detail || 'Transmission failed', 'error');
            }
        } catch (error) {
            showToast('Connection lost during transmission', 'error');
        } finally {
            sendBtn.disabled = false;
            sendBtn.innerHTML = originalHTML;
            validateSendStatus();
        }
    });

    subjectInput.addEventListener('input', validateSendStatus);
    bodyArea.addEventListener('input', validateSendStatus);
    bodyArea.addEventListener('keyup', validateSendStatus);
    bodyArea.addEventListener('paste', () => setTimeout(validateSendStatus, 50));

    // --- Clipboard ---
    copyBtn.addEventListener('click', () => {
        const text = bodyArea.innerText;
        if (!text.trim()) return showToast('Nothing to copy', 'error');

        navigator.clipboard.writeText(text).then(() => {
            showToast('Copied to clipboard');
        });
    });



    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    validateSendStatus();
});
