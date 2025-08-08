// ui.js - UI Components and Helpers
const { ipcRenderer } = require('electron');

class UIManager {
    constructor() {
        this.currentTab = 'pending';
        this.loadingStates = new Set();
        this.toastCounter = 0;
        
        this.init();
    }

    init() {
        this.setupTabNavigation();
        this.setupModals();
        this.setupToasts();
        this.setupElectronHandlers();
        
        console.log('UI Manager initialized');
    }

    // ===== TAB NAVIGATION =====

    setupTabNavigation() {
        const tabButtons = document.querySelectorAll('.nav-tab');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabId = button.dataset.tab;
                this.switchTab(tabId);
            });
        });
    }

    switchTab(tabId) {
        // Remove active class from all tabs and contents
        document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

        // Add active class to selected tab and content
        document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
        document.getElementById(`${tabId}Tab`).classList.add('active');

        this.currentTab = tabId;
        
        // Trigger tab-specific updates
        this.onTabChanged(tabId);
    }

    onTabChanged(tabId) {
        // Clear any existing intervals/timeouts for previous tab
        
        // Load data for the new tab
        switch(tabId) {
            case 'pending':
                fileHandlers.loadPendingItems();
                break;
            case 'processing':
                fileHandlers.loadProcessingItems();
                break;
            case 'completed':
                fileHandlers.loadCompletedItems();
                break;
            case 'cleanup':
                fileHandlers.loadCleanupCandidates();
                break;
        }
    }

    // ===== LOADING STATES =====

    showLoading(context = 'global') {
        this.loadingStates.add(context);
        
        if (context === 'global') {
            document.getElementById('loadingOverlay').classList.remove('hidden');
        } else {
            // Show loading in specific areas
            const element = document.getElementById(`${context}FileList`);
            if (element) {
                element.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-spinner fa-spin"></i>
                        <h3>Loading...</h3>
                        <p>Please wait while we fetch the data.</p>
                    </div>
                `;
            }
        }
    }

    hideLoading(context = 'global') {
        this.loadingStates.delete(context);
        
        if (context === 'global') {
            document.getElementById('loadingOverlay').classList.add('hidden');
        }
    }

    isLoading(context = 'global') {
        return this.loadingStates.has(context);
    }

    // ===== MODAL MANAGEMENT =====

    setupModals() {
        // Close modal when clicking outside
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target.id);
            }
        });

        // Close button handlers
        document.querySelectorAll('.modal-close').forEach(button => {
            button.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    this.closeModal(modal.id);
                }
            });
        });

        // Escape key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const activeModal = document.querySelector('.modal.active');
                if (activeModal) {
                    this.closeModal(activeModal.id);
                }
            }
        });
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            
            // Focus first input
            const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 100);
            }
        }
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            
            // Reset form if exists
            const form = modal.querySelector('form');
            if (form) {
                form.reset();
            }
        }
    }

    // ===== TOAST NOTIFICATIONS =====

    setupToasts() {
        // Auto-remove toasts after 5 seconds
        setInterval(() => {
            const oldToasts = document.querySelectorAll('.toast:not(.removing)');
            oldToasts.forEach(toast => {
                const created = parseInt(toast.dataset.created || 0);
                if (Date.now() - created > 5000) {
                    this.removeToast(toast);
                }
            });
        }, 1000);
    }

    showToast(title, message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toastId = `toast-${++this.toastCounter}`;
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.id = toastId;
        toast.dataset.created = Date.now();
        
        toast.innerHTML = `
            <div class="toast-header">
                <span class="toast-title">${title}</span>
                <button class="toast-close" onclick="ui.removeToast('${toastId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="toast-body">${message}</div>
        `;

        container.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            this.removeToast(toastId);
        }, 5000);

        return toastId;
    }

    removeToast(toastIdOrElement) {
        let toast;
        
        if (typeof toastIdOrElement === 'string') {
            toast = document.getElementById(toastIdOrElement);
        } else {
            toast = toastIdOrElement;
        }
        
        if (toast && !toast.classList.contains('removing')) {
            toast.classList.add('removing');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    }

    // ===== CONFIRMATION DIALOGS =====

    showConfirmation(title, message, onConfirm, onCancel = null) {
        const modal = document.getElementById('confirmationModal');
        const titleEl = document.getElementById('confirmTitle');
        const messageEl = document.getElementById('confirmMessage');
        const okBtn = document.getElementById('confirmOk');
        const cancelBtn = document.getElementById('confirmCancel');

        titleEl.textContent = title;
        messageEl.textContent = message;

        // Remove existing handlers
        const newOkBtn = okBtn.cloneNode(true);
        const newCancelBtn = cancelBtn.cloneNode(true);
        okBtn.parentNode.replaceChild(newOkBtn, okBtn);
        cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);

        // Add new handlers
        newOkBtn.addEventListener('click', () => {
            this.closeModal('confirmationModal');
            if (onConfirm) onConfirm();
        });

        newCancelBtn.addEventListener('click', () => {
            this.closeModal('confirmationModal');
            if (onCancel) onCancel();
        });

        this.openModal('confirmationModal');
    }

    // ===== BADGE UPDATES =====

    updateBadges(counts) {
        const badges = {
            pending: document.getElementById('pendingBadge'),
            processing: document.getElementById('processingBadge'),
            completed: document.getElementById('completedBadge'),
            cleanup: document.getElementById('cleanupBadge')
        };

        Object.keys(badges).forEach(key => {
            const badge = badges[key];
            const count = counts[key] || 0;
            
            if (badge) {
                badge.textContent = count > 0 ? count : '';
                badge.style.display = count > 0 ? 'inline-flex' : 'none';
            }
        });
    }

    // ===== CONNECTION STATUS =====

    updateConnectionStatus(connected, data = null) {
        const statusEl = document.getElementById('connectionStatus');
        const icon = statusEl.querySelector('i');
        const text = statusEl.querySelector('span');

        if (connected) {
            statusEl.className = 'connection-status connected';
            text.textContent = 'Connected';
            icon.className = 'fas fa-circle';
        } else {
            statusEl.className = 'connection-status disconnected';
            text.textContent = 'Disconnected';
            icon.className = 'fas fa-circle';
        }
    }

    // ===== FILE LIST RENDERING =====

    renderFileList(container, files, type = 'video') {
        if (!container) return;

        if (!files || files.length === 0) {
            container.innerHTML = this.getEmptyState(type);
            return;
        }

        const html = files.map(file => this.renderFileItem(file, type)).join('');
        container.innerHTML = html;
        
        // Setup event listeners for file items
        this.setupFileItemHandlers(container);
    }

    renderFileItem(file, type = 'video') {
        const confidence = api.formatConfidence(file.confidence);
        const fileSize = api.formatFileSize(file.file_size);
        const icon = api.getFileTypeIcon(file.filename, type);
        const statusClass = api.getStatusClass(file.status);
        
        // Determine if this needs manual review
        const needsReview = type === 'video' && (!file.episode_number || file.confidence < 0.5);
        
        let actions = '';
        if (file.status === 'pending') {
            if (type === 'video') {
                actions = `
                    <button class="btn btn-sm btn-secondary" onclick="fileHandlers.editVideo('${file.filepath}')">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="fileHandlers.customMove('${file.filepath}')">
                        <i class="fas fa-folder-open"></i> Custom
                    </button>
                    <button class="btn btn-sm btn-success" onclick="fileHandlers.approveVideo('${file.filepath}')">
                        <i class="fas fa-check"></i> Approve
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="fileHandlers.rejectVideo('${file.filepath}')">
                        <i class="fas fa-times"></i> Reject
                    </button>
                `;
            } else if (type === 'archive') {
                actions = `
                    <button class="btn btn-sm btn-success" onclick="fileHandlers.approveArchive('${file.filepath}')">
                        <i class="fas fa-check"></i> Approve
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="fileHandlers.rejectArchive('${file.filepath}')">
                        <i class="fas fa-times"></i> Reject
                    </button>
                `;
            }
        }

        return `
            <div class="file-item ${file.status}" data-filepath="${file.filepath}" data-type="${type}">
                <div class="file-icon ${type}">
                    <i class="${icon}"></i>
                </div>
                <div class="file-info">
                    <div class="file-title">${file.series_name || file.filename}</div>
                    <div class="file-details">
                        ${file.episode_number ? 
                            `<span class="file-meta"><i class="fas fa-tv"></i> Episode ${file.episode_number}</span>` : 
                            ''
                        }
                        ${file.season_number ? 
                            `<span class="file-meta"><i class="fas fa-layer-group"></i> Season ${file.season_number}</span>` : 
                            ''
                        }
                        <span class="file-meta"><i class="fas fa-hdd"></i> ${fileSize}</span>
                        ${confidence.text !== 'Unknown' ? 
                            `<span class="confidence-score confidence-${confidence.level}">${confidence.text}</span>` : 
                            ''
                        }
                        ${needsReview ? '<span class="confidence-score confidence-low">Needs Review</span>' : ''}
                        <span class="file-meta"><i class="fas fa-file"></i> ${file.filename}</span>
                    </div>
                </div>
                <div class="file-actions">
                    ${actions}
                </div>
            </div>
        `;
    }

    renderCleanupItem(candidate) {
        const archiveSize = api.formatFileSize(candidate.archive_size_mb * 1024 * 1024);
        const folderSize = api.formatFileSize(candidate.extracted_folder_size_mb * 1024 * 1024);
        
        return `
            <div class="file-item" data-filepath="${candidate.archive_path}" data-type="cleanup">
                <div class="file-icon archive">
                    <i class="fas fa-file-archive"></i>
                </div>
                <div class="file-info">
                    <div class="file-title">${candidate.archive_name}</div>
                    <div class="file-details">
                        <span class="file-meta"><i class="fas fa-archive"></i> Archive: ${archiveSize}</span>
                        <span class="file-meta"><i class="fas fa-folder"></i> Extracted: ${folderSize} (${candidate.file_count_in_extracted} files)</span>
                        <span class="file-meta"><i class="fas fa-info-circle"></i> Recommended: ${candidate.recommended_action}</span>
                        <span class="file-meta"><i class="fas fa-folder-open"></i> ${candidate.extracted_folder_path}</span>
                    </div>
                </div>
                <div class="file-actions">
                    <button class="btn btn-sm btn-danger" onclick="fileHandlers.cleanupArchive('${candidate.archive_path}', 'delete')">
                        <i class="fas fa-trash"></i> Delete Archive
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="fileHandlers.cleanupArchive('${candidate.archive_path}', 'extract')">
                        <i class="fas fa-redo"></i> Re-extract
                    </button>
                </div>
            </div>
        `;
    }

    setupFileItemHandlers(container) {
        // Setup context menu for file items
        const fileItems = container.querySelectorAll('.file-item');
        
        fileItems.forEach(item => {
            item.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                this.showFileContextMenu(e, item);
            });

            // Double-click to edit videos
            item.addEventListener('dblclick', () => {
                const filepath = item.dataset.filepath;
                const type = item.dataset.type;
                
                if (type === 'video') {
                    fileHandlers.editVideo(filepath);
                }
            });
        });
    }

    showFileContextMenu(event, fileItem) {
        const filepath = fileItem.dataset.filepath;
        const type = fileItem.dataset.type;
        
        // Create context menu (simplified - in a real app you might want a proper context menu library)
        const actions = [
            { label: 'Show in Folder', action: () => this.showInFolder(filepath) },
        ];

        if (type === 'video') {
            actions.unshift(
                { label: 'Edit Details', action: () => fileHandlers.editVideo(filepath) },
                { label: 'Custom Move', action: () => fileHandlers.customMove(filepath) }
            );
        }

        // For now, just show in folder on right-click
        this.showInFolder(filepath);
    }

    async showInFolder(filepath) {
        if (typeof ipcRenderer !== 'undefined') {
            await ipcRenderer.invoke('show-item-in-folder', filepath);
        }
    }

    getEmptyState(type) {
        const states = {
            video: {
                icon: 'fas fa-video',
                title: 'No pending videos',
                description: 'New videos will appear here when detected'
            },
            archive: {
                icon: 'fas fa-file-archive', 
                title: 'No pending archives',
                description: 'Archives will appear here for extraction'
            },
            processing: {
                icon: 'fas fa-cogs',
                title: 'No files processing',
                description: 'Files being processed will appear here'
            },
            completed: {
                icon: 'fas fa-check-circle',
                title: 'No completed files',
                description: 'Successfully processed files will appear here'
            },
            cleanup: {
                icon: 'fas fa-broom',
                title: 'No cleanup needed',
                description: 'Already extracted archives will appear here'
            }
        };

        const state = states[type] || states.video;
        
        return `
            <div class="empty-state">
                <i class="${state.icon}"></i>
                <h3>${state.title}</h3>
                <p>${state.description}</p>
            </div>
        `;
    }

    // ===== ELECTRON HANDLERS =====

    setupElectronHandlers() {
        if (typeof ipcRenderer === 'undefined') return;

        // Handle backend connection updates
        ipcRenderer.on('backend-connected', (event, data) => {
            this.updateConnectionStatus(true, data);
            this.showToast('Connected', 'Successfully connected to backend', 'success');
        });

        ipcRenderer.on('backend-disconnected', (event, error) => {
            this.updateConnectionStatus(false);
            this.showToast('Disconnected', 'Lost connection to backend', 'error');
        });

        // Handle pending updates from main process
        ipcRenderer.on('pending-updates', (event, counts) => {
            this.updateBadges(counts);
        });

        // Window controls
        document.getElementById('minimizeBtn')?.addEventListener('click', () => {
            ipcRenderer.send('minimize-to-tray');
        });

        document.getElementById('settingsBtn')?.addEventListener('click', () => {
            // Settings will be handled in a separate window
            this.openSettingsWindow();
        });

        document.getElementById('refreshBtn')?.addEventListener('click', () => {
            this.refreshCurrentTab();
        });
    }

    async openSettingsWindow() {
        // This will be handled by the main process
        if (typeof ipcRenderer !== 'undefined') {
            // The main process will handle opening the settings window
            // For now, we'll show a toast
            this.showToast('Settings', 'Settings window will open in a separate window', 'info');
        }
    }

    refreshCurrentTab() {
        api.clearCache();
        this.onTabChanged(this.currentTab);
        this.showToast('Refreshed', 'Data refreshed successfully', 'success');
    }

    // ===== UTILITY METHODS =====

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatPath(path) {
        if (!path) return '';
        
        // Truncate long paths
        if (path.length > 60) {
            const parts = path.split(/[/\\]/);
            if (parts.length > 2) {
                return parts[0] + '/.../' + parts[parts.length - 1];
            }
        }
        
        return path;
    }

    copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                this.showToast('Copied', 'Text copied to clipboard', 'success');
            });
        }
    }
}

// Create global UI instance
const ui = new UIManager();