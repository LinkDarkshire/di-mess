// ui.js - User Interface Manager

class UIManager {
    constructor() {
        this.currentTab = 'pending';
        this.loadingStates = new Set();
        this.connectionStatus = false;
        this.toastCounter = 0;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupTabNavigation();
        console.log('UI Manager initialized');
    }

    setupEventListeners() {
        // Settings button
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.openSettingsWindow());
        }

        // Refresh buttons
        const refreshButtons = [
            { id: 'refreshBtn', action: () => this.refreshCurrentTab() },
            { id: 'refreshProcessingBtn', action: () => this.refreshCurrentTab() },
            { id: 'refreshCompletedBtn', action: () => this.refreshCurrentTab() },
            { id: 'refreshCleanupBtn', action: () => this.refreshCurrentTab() }
        ];

        refreshButtons.forEach(({ id, action }) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', action);
            }
        });

        // Action buttons
        const actionButtons = [
            { id: 'approveAllBtn', action: () => this.approveAllItems() },
            { id: 'clearCompletedBtn', action: () => this.clearCompleted() },
            { id: 'deleteAllArchivesBtn', action: () => this.deleteAllArchives() },
            { id: 'extractAllArchivesBtn', action: () => this.extractAllArchives() }
        ];

        actionButtons.forEach(({ id, action }) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', action);
            }
        });
    }

    setupTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabName = btn.getAttribute('data-tab');
                this.switchTab(tabName);
            });
        });
    }

    // Tab Management
    switchTab(tabName) {
        // Update active tab button
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update active tab pane
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`).classList.add('active');

        this.currentTab = tabName;
        this.loadTabData(tabName);
    }

    async loadTabData(tabName) {
        switch (tabName) {
            case 'pending':
                await window.fileHandlers.loadPendingItems();
                break;
            case 'processing':
                await window.fileHandlers.loadProcessingItems();
                break;
            case 'completed':
                await window.fileHandlers.loadCompletedItems();
                break;
            case 'cleanup':
                await window.fileHandlers.loadCleanupCandidates();
                break;
        }
    }

    refreshCurrentTab() {
        window.api.clearCache();
        this.loadTabData(this.currentTab);
    }

    // Connection Status
    updateConnectionStatus(connected, statusData = null) {
        this.connectionStatus = connected;
        const statusElement = document.getElementById('connectionStatus');
        const statusDot = statusElement?.querySelector('.status-dot');
        const statusText = statusElement?.querySelector('.status-text');

        if (statusDot) {
            statusDot.classList.toggle('connected', connected);
        }

        if (statusText) {
            if (connected) {
                statusText.textContent = 'Connected';
            } else {
                statusText.textContent = 'Disconnected';
            }
        }
    }

    // Loading States
    showLoading(containerId) {
        this.loadingStates.add(containerId);
        const container = document.getElementById(containerId);
        const loading = document.getElementById(`${containerId.replace('List', 'Loading')}`);
        const empty = document.getElementById(`${containerId.replace('List', 'Empty')}`);

        if (container) container.style.display = 'none';
        if (loading) loading.style.display = 'flex';
        if (empty) empty.style.display = 'none';
    }

    hideLoading(containerId, hasData = true) {
        this.loadingStates.delete(containerId);
        const container = document.getElementById(containerId);
        const loading = document.getElementById(`${containerId.replace('List', 'Loading')}`);
        const empty = document.getElementById(`${containerId.replace('List', 'Empty')}`);

        if (loading) loading.style.display = 'none';
        
        if (hasData) {
            if (container) container.style.display = 'flex';
            if (empty) empty.style.display = 'none';
        } else {
            if (container) container.style.display = 'none';
            if (empty) empty.style.display = 'flex';
        }
    }

    // Badge Updates
    updateBadges(counts) {
        const badges = {
            pending: document.getElementById('pendingBadge'),
            processing: document.getElementById('processingBadge'),
            completed: document.getElementById('completedBadge'),
            cleanup: document.getElementById('cleanupBadge')
        };

        Object.entries(counts).forEach(([key, count]) => {
            const badge = badges[key];
            if (badge) {
                badge.textContent = count || 0;
                badge.style.display = count > 0 ? 'inline-flex' : 'none';
            }
        });
    }

    // Toast Notifications
    showToast(title, message, type = 'info', duration = 5000) {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) return;

        const toastId = `toast-${++this.toastCounter}`;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.id = toastId;
        
        toast.innerHTML = `
            <div class="toast-title">${this.escapeHtml(title)}</div>
            <div class="toast-message">${this.escapeHtml(message)}</div>
        `;

        toastContainer.appendChild(toast);

        // Auto remove
        setTimeout(() => {
            this.removeToast(toastId);
        }, duration);

        // Click to dismiss
        toast.addEventListener('click', () => {
            this.removeToast(toastId);
        });
    }

    removeToast(toastId) {
        const toast = document.getElementById(toastId);
        if (toast) {
            toast.style.animation = 'toastSlideOut 0.3s ease';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }
    }

    // Modal Management
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    openSettingsWindow() {
        this.openModal('settingsModal');
        window.fileHandlers.loadSettings();
    }

    // Item Rendering
    renderVideoItem(video) {
        const isProcessing = video.status === 'processing';
        const isCompleted = video.status === 'completed';
        const isPending = video.status === 'pending';

        return `
            <div class="item-card video-item" data-filepath="${this.escapeHtml(video.filepath)}">
                <div class="item-header">
                    <div class="item-info">
                        <h3 class="item-title">🎬 ${this.escapeHtml(video.series_name)}</h3>
                        <div class="item-details">
                            <span class="detail-item">📁 ${this.escapeHtml(video.filename)}</span>
                            ${video.episode_number ? `<span class="detail-item">📺 S${video.season_number || 1}E${video.episode_number}</span>` : ''}
                            <span class="detail-item">💾 ${video.file_size_mb}MB</span>
                            <span class="detail-item">🕒 ${new Date(video.detected_at * 1000).toLocaleString()}</span>
                        </div>
                    </div>
                    <div class="item-status">
                        <span class="status-badge status-${video.status}">${this.formatStatus(video.status)}</span>
                        ${video.confidence ? `<span class="confidence-badge">${Math.round(video.confidence * 100)}%</span>` : ''}
                    </div>
                </div>
                
                ${isPending ? this.renderVideoActions(video) : ''}
                ${isCompleted && video.processing_result ? this.renderProcessingResult(video.processing_result) : ''}
                ${video.target_suggestions && video.target_suggestions.length > 0 ? this.renderTargetSuggestions(video.target_suggestions) : ''}
            </div>
        `;
    }

    renderVideoActions(video) {
        return `
            <div class="item-actions">
                <button class="btn btn-success" onclick="fileHandlers.approveVideo('${this.escapeAttr(video.filepath)}')">
                    <span class="icon">✅</span>
                    Approve
                </button>
                <button class="btn btn-secondary" onclick="fileHandlers.editVideo('${this.escapeAttr(video.filepath)}')">
                    <span class="icon">✏️</span>
                    Edit
                </button>
                <button class="btn btn-danger" onclick="fileHandlers.rejectVideo('${this.escapeAttr(video.filepath)}')">
                    <span class="icon">❌</span>
                    Reject
                </button>
            </div>
        `;
    }

    renderArchiveItem(archive) {
        const isProcessing = archive.status === 'processing';
        const isCompleted = archive.status === 'completed';
        const isPending = archive.status === 'pending';

        return `
            <div class="item-card archive-item" data-filepath="${this.escapeHtml(archive.filepath)}">
                <div class="item-header">
                    <div class="item-info">
                        <h3 class="item-title">📦 ${this.escapeHtml(archive.filename)}</h3>
                        <div class="item-details">
                            <span class="detail-item">💾 ${archive.file_size_mb}MB</span>
                            <span class="detail-item">🕒 ${new Date(archive.detected_at * 1000).toLocaleString()}</span>
                        </div>
                    </div>
                    <div class="item-status">
                        <span class="status-badge status-${archive.status}">${this.formatStatus(archive.status)}</span>
                    </div>
                </div>
                
                ${isPending ? this.renderArchiveActions(archive) : ''}
                ${isCompleted && archive.processing_result ? this.renderProcessingResult(archive.processing_result) : ''}
            </div>
        `;
    }

    renderArchiveActions(archive) {
        return `
            <div class="item-actions">
                <button class="btn btn-success" onclick="fileHandlers.approveArchive('${this.escapeAttr(archive.filepath)}')">
                    <span class="icon">✅</span>
                    Extract
                </button>
                <button class="btn btn-danger" onclick="fileHandlers.rejectArchive('${this.escapeAttr(archive.filepath)}')">
                    <span class="icon">❌</span>
                    Reject
                </button>
            </div>
        `;
    }

    renderCleanupItem(candidate) {
        return `
            <div class="item-card cleanup-item" data-filepath="${this.escapeHtml(candidate.archive_path)}">
                <div class="item-header">
                    <div class="item-info">
                        <h3 class="item-title">🧹 ${this.escapeHtml(candidate.archive_name)}</h3>
                        <div class="item-details">
                            <span class="detail-item">📦 Archive: ${candidate.archive_size_mb}MB</span>
                            ${candidate.extracted_folder_path ? `<span class="detail-item">📁 Extracted: ${candidate.extracted_folder_size_mb}MB</span>` : ''}
                            ${candidate.file_count_in_extracted ? `<span class="detail-item">📄 ${candidate.file_count_in_extracted} files</span>` : ''}
                        </div>
                    </div>
                    <div class="item-status">
                        <span class="status-badge status-warning">Needs Cleanup</span>
                    </div>
                </div>
                
                <div class="item-actions">
                    <button class="btn btn-danger" onclick="fileHandlers.cleanupArchive('${this.escapeAttr(candidate.archive_path)}', 'delete')">
                        <span class="icon">🗑️</span>
                        Delete Archive
                    </button>
                    <button class="btn btn-primary" onclick="fileHandlers.cleanupArchive('${this.escapeAttr(candidate.archive_path)}', 'extract')">
                        <span class="icon">📦</span>
                        Re-extract
                    </button>
                </div>
            </div>
        `;
    }

    renderProcessingResult(result) {
        const isSuccess = result.success;
        const statusClass = isSuccess ? 'success' : 'error';
        
        return `
            <div class="processing-result ${statusClass}">
                <div class="result-header">
                    <span class="icon">${isSuccess ? '✅' : '❌'}</span>
                    <span class="result-title">${isSuccess ? 'Success' : 'Error'}</span>
                </div>
                <div class="result-message">${this.escapeHtml(result.message || result.error || 'No details available')}</div>
                ${result.target_path ? `<div class="result-detail">📁 ${this.escapeHtml(result.target_path)}</div>` : ''}
                ${result.file_count ? `<div class="result-detail">📄 ${result.file_count} files</div>` : ''}
            </div>
        `;
    }

    renderTargetSuggestions(suggestions) {
        if (!suggestions || suggestions.length === 0) return '';
        
        const suggestionItems = suggestions.slice(0, 3).map(suggestion => `
            <div class="suggestion-item">
                <div class="suggestion-info">
                    <span class="suggestion-name">${this.escapeHtml(suggestion.name)}</span>
                    <span class="suggestion-path">${this.escapeHtml(suggestion.path)}</span>
                </div>
                <div class="suggestion-meta">
                    ${suggestion.has_existing_series ? '<span class="meta-badge">📺 Has Series</span>' : ''}
                    <span class="meta-badge">💾 ${suggestion.free_space_gb.toFixed(1)}GB free</span>
                </div>
            </div>
        `).join('');

        return `
            <div class="target-suggestions">
                <h4>🎯 Target Suggestions</h4>
                <div class="suggestions-list">
                    ${suggestionItems}
                </div>
            </div>
        `;
    }

    // Action Methods
    async approveAllItems() {
        try {
            let response;
            if (this.currentTab === 'pending') {
                response = await window.api.approveAllVideos();
            } else {
                this.showToast('Error', 'Approve all is only available for pending items', 'error');
                return;
            }

            if (response.success) {
                this.showToast('Success', response.message, 'success');
                this.refreshCurrentTab();
            } else {
                this.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            this.showToast('Error', 'Failed to approve all items', 'error');
        }
    }

    async clearCompleted() {
        try {
            const response = await window.api.cleanupOldEntries(1); // 1 hour
            if (response.success) {
                this.showToast('Success', response.message, 'success');
                this.refreshCurrentTab();
            } else {
                this.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            this.showToast('Error', 'Failed to clear completed items', 'error');
        }
    }

    async deleteAllArchives() {
        if (!confirm('Are you sure you want to delete all cleanup candidates?')) return;

        try {
            const response = await window.api.approveAllCleanupCandidates('delete');
            if (response.success) {
                this.showToast('Success', `${response.data.successful} archives deleted`, 'success');
                this.refreshCurrentTab();
            } else {
                this.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            this.showToast('Error', 'Failed to delete archives', 'error');
        }
    }

    async extractAllArchives() {
        if (!confirm('Are you sure you want to extract all cleanup candidates?')) return;

        try {
            const response = await window.api.approveAllCleanupCandidates('extract');
            if (response.success) {
                this.showToast('Success', `${response.data.successful} archives processed`, 'success');
                this.refreshCurrentTab();
            } else {
                this.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            this.showToast('Error', 'Failed to extract archives', 'error');
        }
    }

    // Utility Methods
    formatStatus(status) {
        const statusMap = {
            'pending': 'Pending',
            'approved': 'Approved',
            'processing': 'Processing',
            'completed': 'Completed',
            'error': 'Error',
            'rejected': 'Rejected'
        };
        return statusMap[status] || status;
    }

    escapeHtml(text) {
        if (typeof text !== 'string') return text;
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    escapeAttr(text) {
        if (typeof text !== 'string') return text;
        return text.replace(/'/g, '&#39;').replace(/"/g, '&quot;');
    }

    // Populate lists
    populateList(containerId, items, renderFunction) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!items || items.length === 0) {
            this.hideLoading(containerId, false);
            return;
        }

        const html = items.map(renderFunction.bind(this)).join('');
        container.innerHTML = html;
        this.hideLoading(containerId, true);
    }
}

// Add CSS for new elements
const additionalCSS = `
.item-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-md);
}

.item-info {
    flex: 1;
}

.item-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0 0 var(--spacing-sm) 0;
    color: var(--text-primary);
}

.item-details {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
}

.detail-item {
    font-size: 0.875rem;
    color: var(--text-secondary);
    background: var(--bg-tertiary);
    padding: 2px 8px;
    border-radius: var(--radius-sm);
}

.item-status {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    align-items: flex-end;
}

.status-badge {
    padding: 4px 12px;
    border-radius: var(--radius-md);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
}

.status-pending { background: var(--accent-warning); color: var(--text-inverse); }
.status-processing { background: var(--accent-info); color: white; }
.status-completed { background: var(--accent-success); color: white; }
.status-error { background: var(--accent-danger); color: white; }
.status-rejected { background: var(--bg-quaternary); color: var(--text-secondary); }

.confidence-badge {
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-size: 0.7rem;
    background: var(--bg-quaternary);
    color: var(--text-secondary);
}

.item-actions {
    display: flex;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-md);
    flex-wrap: wrap;
}

.processing-result {
    margin-top: var(--spacing-md);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    border-left: 4px solid;
}

.processing-result.success {
    background: rgba(16, 185, 129, 0.1);
    border-color: var(--accent-success);
}

.processing-result.error {
    background: rgba(239, 68, 68, 0.1);
    border-color: var(--accent-danger);
}

.result-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-xs);
}

.result-title {
    font-weight: 600;
    color: var(--text-primary);
}

.result-message, .result-detail {
    font-size: 0.875rem;
    color: var(--text-secondary);
}

.target-suggestions {
    margin-top: var(--spacing-md);
    padding: var(--spacing-md);
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);
}

.target-suggestions h4 {
    margin: 0 0 var(--spacing-sm) 0;
    font-size: 0.875rem;
    color: var(--text-primary);
}

.suggestions-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
}

.suggestion-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm);
    background: var(--bg-secondary);
    border-radius: var(--radius-sm);
}

.suggestion-info {
    display: flex;
    flex-direction: column;
}

.suggestion-name {
    font-weight: 500;
    color: var(--text-primary);
    font-size: 0.875rem;
}

.suggestion-path {
    font-size: 0.75rem;
    color: var(--text-muted);
}

.suggestion-meta {
    display: flex;
    gap: var(--spacing-xs);
}

.meta-badge {
    font-size: 0.7rem;
    padding: 2px 6px;
    background: var(--bg-quaternary);
    color: var(--text-secondary);
    border-radius: var(--radius-sm);
}

@keyframes toastSlideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
}
`;

// Inject additional CSS
const style = document.createElement('style');
style.textContent = additionalCSS;
document.head.appendChild(style);

// Create global UI instance
window.ui = new UIManager();

console.log('UI Manager initialized');