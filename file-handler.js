// file-handler.js - File Operation Handlers (Fixed)

class FileHandlers {
    constructor() {
        this.autoRefreshInterval = null;
        this.autoRefreshDelay = 30000; // 30 seconds

        this.currentData = {
            pendingVideos: [],
            pendingArchives: [],
            processingItems: [],
            completedItems: [],
            cleanupCandidates: [],
            targetFolders: [],
            config: null
        };

        // Folder selection state
        this.pendingFolderAction = null;

        console.log('File Handlers initialized');
    }

    // Auto-refresh functionality
    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }

        this.autoRefreshInterval = setInterval(() => {
            this.refreshCurrentTabData();
        }, this.autoRefreshDelay);

        console.log('Auto-refresh started');
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
        console.log('Auto-refresh stopped');
    }

    async refreshCurrentTabData() {
        try {
            const currentTab = window.ui.currentTab;
            await this.loadTabData(currentTab);
        } catch (error) {
            console.error('Auto-refresh failed:', error);
        }
    }

    async loadTabData(tabName) {
        switch (tabName) {
            case 'pending':
                await this.loadPendingItems();
                break;
            case 'processing':
                await this.loadProcessingItems();
                break;
            case 'completed':
                await this.loadCompletedItems();
                break;
            case 'cleanup':
                await this.loadCleanupCandidates();
                break;
        }
    }

    // Load pending items (videos and archives)
    async loadPendingItems() {
        window.ui.showLoading('pendingList');

        try {
            const [videosResponse, archivesResponse] = await Promise.all([
                window.api.getPendingVideos(),
                window.api.getPendingArchives()
            ]);

            const videos = videosResponse.success ? videosResponse.data : [];
            const archives = archivesResponse.success ? archivesResponse.data : [];

            this.currentData.pendingVideos = videos;
            this.currentData.pendingArchives = archives;

            // Combine and sort by detected_at
            const allItems = [
                ...videos.map(v => ({ ...v, type: 'video' })),
                ...archives.map(a => ({ ...a, type: 'archive' }))
            ].sort((a, b) => b.detected_at - a.detected_at);

            // Render items
            this.renderPendingItems(allItems);

            // Update badges
            window.ui.updateBadges({
                pending: videos.length + archives.length
            });

        } catch (error) {
            console.error('Failed to load pending items:', error);
            window.ui.hideLoading('pendingList', false);
            window.ui.showToast('Error', 'Failed to load pending items', 'error');
        }
    }

    renderPendingItems(items) {
        const html = items.map(item => {
            if (item.type === 'video') {
                return window.ui.renderVideoItem(item);
            } else {
                return window.ui.renderArchiveItem(item);
            }
        }).join('');

        const container = document.getElementById('pendingList');
        if (container) {
            container.innerHTML = html;
        }

        window.ui.hideLoading('pendingList', items.length > 0);
    }

    // Load processing items
    async loadProcessingItems() {
        window.ui.showLoading('processingList');

        try {
            const [videosResponse, archivesResponse] = await Promise.all([
                window.api.getProcessingVideos(),
                window.api.getProcessingArchives()
            ]);

            const videos = videosResponse.success ? videosResponse.data : [];
            const archives = archivesResponse.success ? archivesResponse.data : [];

            // Combine and sort
            const allItems = [
                ...videos.map(v => ({ ...v, type: 'video' })),
                ...archives.map(a => ({ ...a, type: 'archive' }))
            ].sort((a, b) => b.detected_at - a.detected_at);

            this.currentData.processingItems = allItems;

            // Render items
            this.renderProcessingItems(allItems);

            // Update badges
            window.ui.updateBadges({
                processing: videos.length + archives.length
            });

        } catch (error) {
            console.error('Failed to load processing items:', error);
            window.ui.hideLoading('processingList', false);
            window.ui.showToast('Error', 'Failed to load processing items', 'error');
        }
    }

    renderProcessingItems(items) {
        const html = items.map(item => {
            if (item.type === 'video') {
                return window.ui.renderVideoItem(item);
            } else {
                return window.ui.renderArchiveItem(item);
            }
        }).join('');

        const container = document.getElementById('processingList');
        if (container) {
            container.innerHTML = html;
        }

        window.ui.hideLoading('processingList', items.length > 0);
    }

    // Load completed items
    async loadCompletedItems() {
        window.ui.showLoading('completedList');

        try {
            const [videosResponse, archivesResponse] = await Promise.all([
                window.api.getCompletedVideos(),
                window.api.getCompletedArchives()
            ]);

            const videos = videosResponse.success ? videosResponse.data : [];
            const archives = archivesResponse.success ? archivesResponse.data : [];

            // Combine and sort
            const allItems = [
                ...videos.map(v => ({ ...v, type: 'video' })),
                ...archives.map(a => ({ ...a, type: 'archive' }))
            ].sort((a, b) => b.detected_at - a.detected_at);

            this.currentData.completedItems = allItems;

            // Render items
            this.renderCompletedItems(allItems);

            // Update badges
            window.ui.updateBadges({
                completed: videos.length + archives.length
            });

        } catch (error) {
            console.error('Failed to load completed items:', error);
            window.ui.hideLoading('completedList', false);
            window.ui.showToast('Error', 'Failed to load completed items', 'error');
        }
    }

    renderCompletedItems(items) {
        const html = items.map(item => {
            if (item.type === 'video') {
                return window.ui.renderVideoItem(item);
            } else {
                return window.ui.renderArchiveItem(item);
            }
        }).join('');

        const container = document.getElementById('completedList');
        if (container) {
            container.innerHTML = html;
        }

        window.ui.hideLoading('completedList', items.length > 0);
    }

    // Load cleanup candidates
    async loadCleanupCandidates() {
        window.ui.showLoading('cleanupList');

        try {
            const response = await window.api.getStartupCleanupCandidates();
            const candidates = response.success ? response.data : [];

            this.currentData.cleanupCandidates = candidates;

            // Render items
            this.renderCleanupCandidates(candidates);

            // Update badges
            window.ui.updateBadges({
                cleanup: candidates.length
            });

        } catch (error) {
            console.error('Failed to load cleanup candidates:', error);
            window.ui.hideLoading('cleanupList', false);
            window.ui.showToast('Error', 'Failed to load cleanup candidates', 'error');
        }
    }

    renderCleanupCandidates(candidates) {
        const html = candidates.map(candidate =>
            window.ui.renderCleanupItem(candidate)
        ).join('');

        const container = document.getElementById('cleanupList');
        if (container) {
            container.innerHTML = html;
        }

        window.ui.hideLoading('cleanupList', candidates.length > 0);
    }

    // Load target folders for dropdowns
    async loadTargetFolders() {
        try {
            const response = await window.api.getConfig();
            if (response.success) {
                this.currentData.targetFolders = response.data.target_folders || [];
                this.currentData.config = response.data;
                this.updateTargetFolderSelects();
            }
        } catch (error) {
            console.error('Failed to load target folders:', error);
        }
    }

    updateTargetFolderSelects() {
        const selects = document.querySelectorAll('select[id*="TargetFolder"], select[id*="targetFolder"]');
        selects.forEach(select => {
            // Keep current value
            const currentValue = select.value;

            // Clear and repopulate
            select.innerHTML = '<option value="">Select target folder...</option>';

            this.currentData.targetFolders.forEach(folder => {
                if (folder.enabled) {
                    const option = document.createElement('option');
                    option.value = folder.path;
                    option.textContent = `${folder.name} (${folder.path})`;
                    select.appendChild(option);
                }
            });

            // Restore value if still valid
            if (currentValue) {
                select.value = currentValue;
            }
        });
    }

    // Video Actions
    async approveVideo(filepath) {
        try {
            const response = await window.api.approveVideo(filepath);
            if (response.success) {
                window.ui.showToast('Success', 'Video approved for processing', 'success');
                await this.loadPendingItems();
            } else {
                window.ui.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            window.ui.showToast('Error', 'Failed to approve video', 'error');
        }
    }

    async rejectVideo(filepath) {
        if (!confirm('Are you sure you want to reject this video?')) return;

        try {
            const response = await window.api.rejectVideo(filepath);
            if (response.success) {
                window.ui.showToast('Success', 'Video rejected', 'success');
                await this.loadPendingItems();
            } else {
                window.ui.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            window.ui.showToast('Error', 'Failed to reject video', 'error');
        }
    }

    editVideo(filepath) {
        // Find video in current data
        const video = this.currentData.pendingVideos.find(v => v.filepath === filepath);
        if (!video) {
            window.ui.showToast('Error', 'Video not found', 'error');
            return;
        }

        // Populate edit form
        document.getElementById('editVideoPath').value = filepath;
        document.getElementById('editSeriesName').value = video.series_name || '';
        document.getElementById('editSeasonNumber').value = video.season_number || '';
        document.getElementById('editEpisodeNumber').value = video.episode_number || '';

        // Set target folder if available
        const targetSelect = document.getElementById('editTargetFolder');
        if (video.target_folder) {
            targetSelect.value = video.target_folder;
        }

        // Open modal
        window.ui.openModal('editVideoModal');
    }

    async saveVideoEdit() {
        const filepath = document.getElementById('editVideoPath').value;
        const seriesName = document.getElementById('editSeriesName').value.trim();
        const seasonNumber = parseInt(document.getElementById('editSeasonNumber').value) || null;
        const episodeNumber = parseInt(document.getElementById('editEpisodeNumber').value) || null;
        const targetFolder = document.getElementById('editTargetFolder').value;

        if (!seriesName) {
            window.ui.showToast('Error', 'Series name is required', 'error');
            return;
        }

        try {
            const response = await window.api.updateVideoMetadata(filepath, {
                series_name: seriesName,
                season_number: seasonNumber,
                episode_number: episodeNumber
            });

            if (response.success) {
                window.ui.showToast('Success', 'Video metadata updated', 'success');
                window.ui.closeModal('editVideoModal');

                // If target folder is selected, approve with that folder
                if (targetFolder) {
                    await this.approveVideoWithTarget(filepath, targetFolder);
                } else {
                    await this.loadPendingItems();
                }
            } else {
                window.ui.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            window.ui.showToast('Error', 'Failed to update video metadata', 'error');
        }
    }

    async approveVideoWithTarget(filepath, targetFolder) {
        try {
            const response = await window.api.approveVideo(filepath, targetFolder);
            if (response.success) {
                window.ui.showToast('Success', 'Video approved with target folder', 'success');
                await this.loadPendingItems();
            } else {
                window.ui.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            window.ui.showToast('Error', 'Failed to approve video with target', 'error');
        }
    }

    // Archive Actions
    async approveArchive(filepath) {
        try {
            const response = await window.api.approveArchive(filepath);
            if (response.success) {
                window.ui.showToast('Success', 'Archive approved for extraction', 'success');
                await this.loadPendingItems();
            } else {
                window.ui.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            window.ui.showToast('Error', 'Failed to approve archive', 'error');
        }
    }

    async rejectArchive(filepath) {
        if (!confirm('Are you sure you want to reject this archive?')) return;

        try {
            const response = await window.api.rejectArchive(filepath);
            if (response.success) {
                window.ui.showToast('Success', 'Archive rejected', 'success');
                await this.loadPendingItems();
            } else {
                window.ui.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            window.ui.showToast('Error', 'Failed to reject archive', 'error');
        }
    }

    // Cleanup Actions
    async cleanupArchive(archivePath, action) {
        const actionText = action === 'delete' ? 'delete' : 're-extract';
        if (!confirm(`Are you sure you want to ${actionText} this archive?`)) return;

        try {
            const response = await window.api.approveCleanupCandidate(archivePath, action);
            if (response.success) {
                window.ui.showToast('Success', `Archive ${actionText}d successfully`, 'success');
                await this.loadCleanupCandidates();
            } else {
                window.ui.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            window.ui.showToast('Error', `Failed to ${actionText} archive`, 'error');
        }
    }

    // Settings Management
    async loadSettings() {
        try {
            const response = await window.api.getConfig();
            if (response.success) {
                const config = response.data;
                this.currentData.config = config;
                this.populateSettingsForm(config);
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
            window.ui.showToast('Error', 'Failed to load settings', 'error');
        }
    }

    populateSettingsForm(config) {
        // Archive settings
        document.getElementById('autoExtractArchives').checked = config.settings?.auto_extract_archives ?? true;
        document.getElementById('deleteArchivesAfterExtract').checked = config.settings?.delete_archives_after_extract ?? true;
        document.getElementById('autoCleanupExtracted').checked = config.settings?.auto_cleanup_extracted_archives ?? false;

        // System settings
        document.getElementById('minFileSize').value = config.settings?.min_file_size_mb ?? 10;
        document.getElementById('stabilitySeconds').value = config.settings?.download_stability_seconds ?? 30;

        // Populate folder lists
        this.populateWatchFoldersList(config.watch_folders || []);
        this.populateTargetFoldersList(config.target_folders || []);
    }

    populateWatchFoldersList(folders) {
        const container = document.getElementById('watchFoldersList');
        if (!container) return;

        const html = folders.map((folder, index) => `
            <div class="folder-item">
                <div class="folder-info">
                    <strong>${window.ui.escapeHtml(folder.name)}</strong>
                    <span class="folder-path">${window.ui.escapeHtml(folder.path)}</span>
                    <div class="folder-options">
                        <label><input type="checkbox" ${folder.watch_videos ? 'checked' : ''}> Videos</label>
                        <label><input type="checkbox" ${folder.watch_archives ? 'checked' : ''}> Archives</label>
                        <label><input type="checkbox" ${folder.enabled ? 'checked' : ''}> Enabled</label>
                    </div>
                </div>
                <button class="btn btn-danger btn-sm" onclick="fileHandlers.removeWatchFolder(${index})">Remove</button>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    populateTargetFoldersList(folders) {
        const container = document.getElementById('targetFoldersList');
        if (!container) return;

        const html = folders.map((folder, index) => `
            <div class="folder-item">
                <div class="folder-info">
                    <strong>${window.ui.escapeHtml(folder.name)}</strong>
                    <span class="folder-path">${window.ui.escapeHtml(folder.path)}</span>
                    <div class="folder-options">
                        <label>Priority: <input type="number" value="${folder.priority || 0}" min="0" max="10"></label>
                        <label><input type="checkbox" ${folder.enabled ? 'checked' : ''}> Enabled</label>
                    </div>
                </div>
                <button class="btn btn-danger btn-sm" onclick="fileHandlers.removeTargetFolder(${index})">Remove</button>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    async saveSettings() {
        try {
            const settings = {
                settings: {
                    auto_extract_archives: document.getElementById('autoExtractArchives').checked,
                    delete_archives_after_extract: document.getElementById('deleteArchivesAfterExtract').checked,
                    auto_cleanup_extracted_archives: document.getElementById('autoCleanupExtracted').checked,
                    min_file_size_mb: parseInt(document.getElementById('minFileSize').value) || 10,
                    download_stability_seconds: parseInt(document.getElementById('stabilitySeconds').value) || 30
                }
            };

            const response = await window.api.updateConfig(settings);
            if (response.success) {
                window.ui.showToast('Success', 'Settings saved successfully', 'success');
                window.ui.closeModal('settingsModal');
            } else {
                window.ui.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            window.ui.showToast('Error', 'Failed to save settings', 'error');
        }
    }

    // Folder Management - Updated to use proper dialogs
    async addWatchFolder() {
        // Set pending action
        this.pendingFolderAction = 'addWatch';

        // Use Electron dialog if available
        if (window.electronAPI) {
            try {
                const result = await window.electronAPI.showOpenDialog({
                    properties: ['openDirectory'],
                    title: 'Select Watch Folder'
                });

                if (!result.canceled && result.filePaths.length > 0) {
                    const path = result.filePaths[0];
                    await this.showFolderNameDialog(path, 'watch');
                }
            } catch (error) {
                console.error('Electron dialog failed:', error);
                this.showFolderBrowserModal('watch');
            }
        } else {
            // Fallback to custom modal
            this.showFolderBrowserModal('watch');
        }
    }

    async addTargetFolder() {
        // Set pending action
        this.pendingFolderAction = 'addTarget';

        // Use Electron dialog if available
        if (window.electronAPI) {
            try {
                const result = await window.electronAPI.showOpenDialog({
                    properties: ['openDirectory'],
                    title: 'Select Target Folder'
                });

                if (!result.canceled && result.filePaths.length > 0) {
                    const path = result.filePaths[0];
                    await this.showFolderNameDialog(path, 'target');
                }
            } catch (error) {
                console.error('Electron dialog failed:', error);
                this.showFolderBrowserModal('target');
            }
        } else {
            // Fallback to custom modal
            this.showFolderBrowserModal('target');
        }
    }

    showFolderBrowserModal(type) {
        // Store type for later use
        this.folderType = type;

        // Clear path input
        document.getElementById('folderPath').value = '';

        // Update modal title
        const modalTitle = document.querySelector('#folderBrowserModal .modal-header h3');
        if (modalTitle) {
            modalTitle.textContent = type === 'watch' ? 'Select Watch Folder' : 'Select Target Folder';
        }

        // Setup browse button for manual entry (fallback)
        const browseBtn = document.getElementById('browseFolderBtn');
        if (browseBtn) {
            browseBtn.onclick = () => {
                // This is a fallback - user would need to type path manually
                const path = document.getElementById('folderPath').value.trim();
                if (path) {
                    this.showFolderNameDialog(path, type);
                } else {
                    window.ui.showToast('Error', 'Please enter a folder path', 'error');
                }
            };
        }

        // Open modal
        window.ui.openModal('folderBrowserModal');
    }

    async showFolderNameDialog(path, type) {
        // Close folder browser modal
        window.ui.closeModal('folderBrowserModal');

        // Create a simple input dialog using Electron if available
        if (window.electronAPI) {
            try {
                const defaultName = path.split(/[/\\]/).pop();
                const result = await window.electronAPI.showMessageBox({
                    type: 'question',
                    buttons: ['OK', 'Cancel'],
                    defaultId: 0,
                    title: 'Folder Name',
                    message: `Enter a name for this ${type} folder:`,
                    detail: `Path: ${path}\nDefault name: ${defaultName}`
                });

                if (result.response === 0) {
                    // User clicked OK - use default name for now
                    // In a full implementation, you'd want a proper input dialog
                    await this.processFolderAddition(path, defaultName, type);
                }
            } catch (error) {
                console.error('Dialog failed:', error);
                // Fallback to default name
                const defaultName = path.split(/[/\\]/).pop();
                await this.processFolderAddition(path, defaultName, type);
            }
        } else {
            // Browser fallback - use default name
            const defaultName = path.split(/[/\\]/).pop();
            await this.processFolderAddition(path, defaultName, type);
        }
    }

    async processFolderAddition(path, name, type) {
        try {
            let response;
            if (type === 'watch') {
                response = await window.api.addWatchFolder({
                    // Entferne 'path' aus dem Objekt, da es bereits als separater Parameter gesendet wird
                    name: name,
                    watch_videos: true,
                    watch_archives: true,
                    enabled: true,
                    recursive: true,
                    video_search_depth: 1
                });
            } else {
                response = await window.api.addTargetFolder({
                    // Entferne 'path' aus dem Objekt
                    name: name,
                    priority: 1,
                    enabled: true
                });
            }

            if (response.success) {
                window.ui.showToast('Success', `${type === 'watch' ? 'Watch' : 'Target'} folder added`, 'success');
                await this.loadSettings();
                if (type === 'target') {
                    await this.loadTargetFolders();
                }
            } else {
                window.ui.showToast('Error', response.error, 'error');
            }
        } catch (error) {
            window.ui.showToast('Error', `Failed to add ${type} folder`, 'error');
        }
    }

    confirmFolderSelection() {
        const path = document.getElementById('folderPath').value.trim();
        if (!path) {
            window.ui.showToast('Error', 'Please enter a folder path', 'error');
            return;
        }

        const type = this.folderType || 'watch';
        this.showFolderNameDialog(path, type);
    }

    removeWatchFolder(index) {
        if (!confirm('Remove this watch folder?')) return;
        // Implementation would require backend support
        window.ui.showToast('Info', 'Remove functionality not yet implemented', 'info');
    }

    removeTargetFolder(index) {
        if (!confirm('Remove this target folder?')) return;
        // Implementation would require backend support
        window.ui.showToast('Info', 'Remove functionality not yet implemented', 'info');
    }
}

// Add CSS for folder items
const folderCSS = `
.folder-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md);
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-sm);
}

.folder-info {
    flex: 1;
}

.folder-info strong {
    display: block;
    color: var(--text-primary);
    margin-bottom: var(--spacing-xs);
}

.folder-path {
    display: block;
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: var(--spacing-sm);
}

.folder-options {
    display: flex;
    gap: var(--spacing-md);
}

.folder-options label {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: 0.875rem;
    color: var(--text-secondary);
}

.folder-options input[type="checkbox"] {
    width: auto;
    margin: 0;
}

.folder-options input[type="number"] {
    width: 60px;
    padding: 2px 6px;
    margin: 0;
}

.btn-sm {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: 0.75rem;
}

.settings-section {
    margin-bottom: var(--spacing-xl);
}

.settings-section h4 {
    margin-bottom: var(--spacing-md);
    color: var(--text-primary);
    font-size: 1.1rem;
}

.setting-item {
    margin-bottom: var(--spacing-md);
}

.folder-browser {
    display: flex;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
}

.folder-browser input {
    flex: 1;
}

.help-text {
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin: 0;
}
`;

// Inject folder CSS
const folderStyle = document.createElement('style');
folderStyle.textContent = folderCSS;
document.head.appendChild(folderStyle);

// Create global file handlers instance
window.fileHandlers = new FileHandlers();

console.log('File Handlers initialized');