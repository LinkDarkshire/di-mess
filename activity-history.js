// settings.js - Settings Window Management - FIXED VERSION

class SettingsManager {
    constructor() {
        this.initialized = false;
        this.currentConfig = null;
        this.folderListUpdateInterval = null;
        
        // Bind methods
        this.loadConfig = this.loadConfig.bind(this);
        this.saveConfig = this.saveConfig.bind(this);
        this.addWatchFolder = this.addWatchFolder.bind(this);
        this.addTargetFolder = this.addTargetFolder.bind(this);
        this.removeWatchFolder = this.removeWatchFolder.bind(this);
        this.removeTargetFolder = this.removeTargetFolder.bind(this);
        
        this.init();
    }

    async init() {
        if (this.initialized) return;

        console.log('Initializing Settings Manager...');

        try {
            // Wait for DOM
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.init());
                return;
            }

            // Setup event listeners
            this.setupEventListeners();

            // Load initial configuration
            await this.loadConfig();

            // Start periodic updates
            this.startPeriodicUpdates();

            this.initialized = true;
            console.log('Settings Manager initialized');

        } catch (error) {
            console.error('Failed to initialize Settings Manager:', error);
            this.showMessage('Failed to initialize settings', 'error');
        }
    }

    setupEventListeners() {
        // Save button
        const saveBtn = document.getElementById('save-settings');
        if (saveBtn) {
            saveBtn.addEventListener('click', this.saveConfig);
        }

        // Add folder buttons
        const addWatchBtn = document.getElementById('add-watch-folder');
        if (addWatchBtn) {
            addWatchBtn.addEventListener('click', this.addWatchFolder);
        }

        const addTargetBtn = document.getElementById('add-target-folder');
        if (addTargetBtn) {
            addTargetBtn.addEventListener('click', this.addTargetFolder);
        }

        // Folder path input with browse button
        this.setupFolderInputs();

        // Form validation
        this.setupFormValidation();

        // Settings tabs
        this.setupTabNavigation();

        console.log('Settings event listeners setup complete');
    }

    setupFolderInputs() {
        // Watch folder path input
        const watchPathInput = document.getElementById('watch-folder-path');
        const watchBrowseBtn = document.getElementById('browse-watch-folder');
        
        if (watchBrowseBtn) {
            watchBrowseBtn.addEventListener('click', async () => {
                if (window.electronAPI) {
                    try {
                        const result = await window.electronAPI.selectFolder();
                        if (result && !result.canceled && result.filePaths.length > 0) {
                            if (watchPathInput) {
                                watchPathInput.value = result.filePaths[0];
                            }
                        }
                    } catch (error) {
                        console.error('Error selecting folder:', error);
                        this.showMessage('Error selecting folder', 'error');
                    }
                } else {
                    this.showMessage('Folder selection is only available in desktop version', 'warning');
                }
            });
        }

        // Target folder path input
        const targetPathInput = document.getElementById('target-folder-path');
        const targetBrowseBtn = document.getElementById('browse-target-folder');
        
        if (targetBrowseBtn) {
            targetBrowseBtn.addEventListener('click', async () => {
                if (window.electronAPI) {
                    try {
                        const result = await window.electronAPI.selectFolder();
                        if (result && !result.canceled && result.filePaths.length > 0) {
                            if (targetPathInput) {
                                targetPathInput.value = result.filePaths[0];
                            }
                        }
                    } catch (error) {
                        console.error('Error selecting folder:', error);
                        this.showMessage('Error selecting folder', 'error');
                    }
                } else {
                    this.showMessage('Folder selection is only available in desktop version', 'warning');
                }
            });
        }
    }

    setupFormValidation() {
        // Real-time validation for folder paths
        const pathInputs = document.querySelectorAll('input[type="text"][id*="path"]');
        pathInputs.forEach(input => {
            input.addEventListener('blur', (e) => {
                this.validatePath(e.target);
            });
        });

        // Validation for numeric inputs
        const numericInputs = document.querySelectorAll('input[type="number"]');
        numericInputs.forEach(input => {
            input.addEventListener('input', (e) => {
                this.validateNumericInput(e.target);
            });
        });
    }

    setupTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const targetTab = e.target.dataset.tab;
                
                // Remove active class from all tabs and contents
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));
                
                // Add active class to clicked tab and corresponding content
                e.target.classList.add('active');
                const targetContent = document.getElementById(`${targetTab}-tab`);
                if (targetContent) {
                    targetContent.classList.add('active');
                }
            });
        });
    }

    async loadConfig() {
        try {
            this.showLoading(true);
            
            // Use global API if available, otherwise create local instance
            const api = window.api || new APIManager();
            const response = await api.getConfig();
            
            if (response.success) {
                this.currentConfig = response.data;
                this.populateForm(this.currentConfig);
                this.updateFolderLists();
                console.log('Configuration loaded:', this.currentConfig);
            } else {
                throw new Error(response.error || 'Failed to load configuration');
            }
            
        } catch (error) {
            console.error('Error loading configuration:', error);
            this.showMessage('Failed to load configuration: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    populateForm(config) {
        // General Settings
        this.setInputValue('min-file-size', config.settings.min_file_size_mb);
        this.setInputValue('download-stability', config.settings.download_stability_seconds);
        this.setCheckboxValue('enable-notifications', config.settings.enable_notifications);

        // Archive Settings
        this.setCheckboxValue('auto-extract-archives', config.settings.auto_extract_archives);
        this.setCheckboxValue('delete-archives-after-extract', config.settings.delete_archives_after_extract);
        this.setCheckboxValue('auto-cleanup-extracted-archives', config.settings.auto_cleanup_extracted_archives);
        this.setCheckboxValue('cleanup-archives-on-startup', config.settings.cleanup_extracted_archives_on_startup);

        // Extensions
        this.populateExtensions('video-extensions', config.video_extensions);
        this.populateExtensions('archive-extensions', config.archive_extensions);

        console.log('Form populated with configuration');
    }

    populateExtensions(containerId, extensions) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = '';

        extensions.forEach(ext => {
            const extensionTag = document.createElement('span');
            extensionTag.className = 'extension-tag';
            extensionTag.innerHTML = `
                ${ext}
                <button type="button" class="remove-extension" data-extension="${ext}">×</button>
            `;

            // Add remove functionality
            const removeBtn = extensionTag.querySelector('.remove-extension');
            removeBtn.addEventListener('click', () => {
                extensionTag.remove();
            });

            container.appendChild(extensionTag);
        });
    }

    // FIX: Verbesserte Ordner-Listen-Anzeige
    updateFolderLists() {
        if (!this.currentConfig) return;

        this.updateWatchFoldersList();
        this.updateTargetFoldersList();
    }

    updateWatchFoldersList() {
        const container = document.getElementById('watch-folders-list');
        if (!container) return;

        container.innerHTML = '';

        if (!this.currentConfig.watch_folders || this.currentConfig.watch_folders.length === 0) {
            container.innerHTML = '<div class="no-folders">No watch folders configured</div>';
            return;
        }

        this.currentConfig.watch_folders.forEach((folder, index) => {
            const folderItem = document.createElement('div');
            folderItem.className = 'folder-item';
            folderItem.innerHTML = `
                <div class="folder-info">
                    <div class="folder-name">${this.escapeHtml(folder.name)}</div>
                    <div class="folder-path">${this.escapeHtml(folder.path)}</div>
                    <div class="folder-settings">
                        <label><input type="checkbox" ${folder.enabled ? 'checked' : ''} data-folder-index="${index}" data-setting="enabled"> Enabled</label>
                        <label><input type="checkbox" ${folder.watch_videos ? 'checked' : ''} data-folder-index="${index}" data-setting="watch_videos"> Videos</label>
                        <label><input type="checkbox" ${folder.watch_archives ? 'checked' : ''} data-folder-index="${index}" data-setting="watch_archives"> Archives</label>
                        <label><input type="checkbox" ${folder.recursive ? 'checked' : ''} data-folder-index="${index}" data-setting="recursive"> Recursive</label>
                    </div>
                </div>
                <div class="folder-actions">
                    <button type="button" class="btn btn-sm btn-secondary edit-folder" data-folder-index="${index}" data-folder-type="watch">
                        Edit
                    </button>
                    <button type="button" class="btn btn-sm btn-danger remove-folder" data-folder-path="${encodeURIComponent(folder.path)}" data-folder-type="watch">
                        Remove
                    </button>
                </div>
            `;

            // Add event listeners for folder settings
            const checkboxes = folderItem.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const folderIndex = parseInt(e.target.dataset.folderIndex);
                    const setting = e.target.dataset.setting;
                    const value = e.target.checked;
                    
                    if (this.currentConfig.watch_folders[folderIndex]) {
                        this.currentConfig.watch_folders[folderIndex][setting] = value;
                        console.log(`Updated watch folder ${folderIndex} setting ${setting} to ${value}`);
                    }
                });
            });

            // Add event listener for remove button
            const removeBtn = folderItem.querySelector('.remove-folder');
            removeBtn.addEventListener('click', () => {
                this.removeWatchFolder(folder.path);
            });

            container.appendChild(folderItem);
        });

        console.log(`Updated watch folders list: ${this.currentConfig.watch_folders.length} folders`);
    }

    updateTargetFoldersList() {
        const container = document.getElementById('target-folders-list');
        if (!container) return;

        container.innerHTML = '';

        if (!this.currentConfig.target_folders || this.currentConfig.target_folders.length === 0) {
            container.innerHTML = '<div class="no-folders">No target folders configured</div>';
            return;
        }

        this.currentConfig.target_folders.forEach((folder, index) => {
            const folderItem = document.createElement('div');
            folderItem.className = 'folder-item';
            folderItem.innerHTML = `
                <div class="folder-info">
                    <div class="folder-name">${this.escapeHtml(folder.name)}</div>
                    <div class="folder-path">${this.escapeHtml(folder.path)}</div>
                    <div class="folder-settings">
                        <label><input type="checkbox" ${folder.enabled ? 'checked' : ''} data-folder-index="${index}" data-setting="enabled"> Enabled</label>
                        <label>Priority: <input type="number" value="${folder.priority || 0}" data-folder-index="${index}" data-setting="priority" min="0" max="100" style="width: 60px;"></label>
                    </div>
                </div>
                <div class="folder-actions">
                    <button type="button" class="btn btn-sm btn-secondary edit-folder" data-folder-index="${index}" data-folder-type="target">
                        Edit
                    </button>
                    <button type="button" class="btn btn-sm btn-danger remove-folder" data-folder-path="${encodeURIComponent(folder.path)}" data-folder-type="target">
                        Remove
                    </button>
                </div>
            `;

            // Add event listeners for folder settings
            const checkbox = folderItem.querySelector('input[type="checkbox"]');
            checkbox.addEventListener('change', (e) => {
                const folderIndex = parseInt(e.target.dataset.folderIndex);
                const setting = e.target.dataset.setting;
                const value = e.target.checked;
                
                if (this.currentConfig.target_folders[folderIndex]) {
                    this.currentConfig.target_folders[folderIndex][setting] = value;
                    console.log(`Updated target folder ${folderIndex} setting ${setting} to ${value}`);
                }
            });

            const priorityInput = folderItem.querySelector('input[type="number"]');
            priorityInput.addEventListener('change', (e) => {
                const folderIndex = parseInt(e.target.dataset.folderIndex);
                const setting = e.target.dataset.setting;
                const value = parseInt(e.target.value);
                
                if (this.currentConfig.target_folders[folderIndex]) {
                    this.currentConfig.target_folders[folderIndex][setting] = value;
                    console.log(`Updated target folder ${folderIndex} setting ${setting} to ${value}`);
                }
            });

            // Add event listener for remove button
            const removeBtn = folderItem.querySelector('.remove-folder');
            removeBtn.addEventListener('click', () => {
                this.removeTargetFolder(folder.path);
            });

            container.appendChild(folderItem);
        });

        console.log(`Updated target folders list: ${this.currentConfig.target_folders.length} folders`);
    }

    async saveConfig() {
        try {
            this.showLoading(true);

            // Collect form data
            const formData = this.collectFormData();
            
            // Merge with current config
            const configToSave = {
                ...formData,
                watch_folders: this.currentConfig.watch_folders,
                target_folders: this.currentConfig.target_folders
            };

            console.log('Saving configuration:', configToSave);

            // Use global API if available
            const api = window.api || new APIManager();
            const response = await api.updateConfig(configToSave);

            if (response.success) {
                this.showMessage('Configuration saved successfully', 'success');
                // Reload configuration to get updated data
                await this.loadConfig();
            } else {
                throw new Error(response.error || 'Failed to save configuration');
            }

        } catch (error) {
            console.error('Error saving configuration:', error);
            this.showMessage('Failed to save configuration: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    collectFormData() {
        const formData = {
            settings: {
                min_file_size_mb: this.getInputValue('min-file-size', 10),
                download_stability_seconds: this.getInputValue('download-stability', 30),
                enable_notifications: this.getCheckboxValue('enable-notifications'),
                auto_extract_archives: this.getCheckboxValue('auto-extract-archives'),
                delete_archives_after_extract: this.getCheckboxValue('delete-archives-after-extract'),
                auto_cleanup_extracted_archives: this.getCheckboxValue('auto-cleanup-extracted-archives'),
                cleanup_extracted_archives_on_startup: this.getCheckboxValue('cleanup-archives-on-startup')
            },
            video_extensions: this.collectExtensions('video-extensions'),
            archive_extensions: this.collectExtensions('archive-extensions')
        };

        return formData;
    }

    collectExtensions(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return [];

        const tags = container.querySelectorAll('.extension-tag');
        const extensions = [];

        tags.forEach(tag => {
            const text = tag.textContent.trim();
            if (text && text !== '×') {
                extensions.push(text.replace('×', '').trim());
            }
        });

        return extensions;
    }

    async addWatchFolder() {
        try {
            const path = this.getInputValue('watch-folder-path');
            const name = this.getInputValue('watch-folder-name') || path.split('/').pop() || path.split('\\').pop();

            if (!path) {
                this.showMessage('Please enter a folder path', 'warning');
                return;
            }

            const folderData = {
                path: path.trim(),
                name: name.trim(),
                watch_videos: this.getCheckboxValue('watch-folder-videos', true),
                watch_archives: this.getCheckboxValue('watch-folder-archives', true),
                recursive: this.getCheckboxValue('watch-folder-recursive', true),
                video_search_depth: this.getInputValue('watch-folder-depth', 1),
                enabled: true
            };

            console.log('Adding watch folder:', folderData);

            const api = window.api || new APIManager();
            const response = await api.addWatchFolder(folderData);

            if (response.success) {
                this.showMessage('Watch folder added successfully', 'success');
                
                // Clear form
                this.clearWatchFolderForm();
                
                // Reload configuration
                await this.loadConfig();
            } else {
                throw new Error(response.error || 'Failed to add watch folder');
            }

        } catch (error) {
            console.error('Error adding watch folder:', error);
            this.showMessage('Failed to add watch folder: ' + error.message, 'error');
        }
    }

    async addTargetFolder() {
        try {
            const path = this.getInputValue('target-folder-path');
            const name = this.getInputValue('target-folder-name') || path.split('/').pop() || path.split('\\').pop();

            if (!path) {
                this.showMessage('Please enter a folder path', 'warning');
                return;
            }

            const folderData = {
                path: path.trim(),
                name: name.trim(),
                priority: this.getInputValue('target-folder-priority', 0),
                enabled: true
            };

            console.log('Adding target folder:', folderData);

            const api = window.api || new APIManager();
            const response = await api.addTargetFolder(folderData);

            if (response.success) {
                this.showMessage('Target folder added successfully', 'success');
                
                // Clear form
                this.clearTargetFolderForm();
                
                // Reload configuration
                await this.loadConfig();
            } else {
                throw new Error(response.error || 'Failed to add target folder');
            }

        } catch (error) {
            console.error('Error adding target folder:', error);
            this.showMessage('Failed to add target folder: ' + error.message, 'error');
        }
    }

    // FIX: Ordner-Entfernung implementiert
    async removeWatchFolder(folderPath) {
        if (!confirm(`Are you sure you want to remove this watch folder?\n\nPath: ${folderPath}`)) {
            return;
        }

        try {
            console.log('Removing watch folder:', folderPath);

            const api = window.api || new APIManager();
            const response = await api.request(`/config/folders/watch/${encodeURIComponent(folderPath)}`, {
                method: 'DELETE'
            });

            if (response.success) {
                this.showMessage('Watch folder removed successfully', 'success');
                
                // Reload configuration
                await this.loadConfig();
            } else {
                throw new Error(response.error || 'Failed to remove watch folder');
            }

        } catch (error) {
            console.error('Error removing watch folder:', error);
            this.showMessage('Failed to remove watch folder: ' + error.message, 'error');
        }
    }

    async removeTargetFolder(folderPath) {
        if (!confirm(`Are you sure you want to remove this target folder?\n\nPath: ${folderPath}`)) {
            return;
        }

        try {
            console.log('Removing target folder:', folderPath);

            const api = window.api || new APIManager();
            const response = await api.request(`/config/folders/target/${encodeURIComponent(folderPath)}`, {
                method: 'DELETE'
            });

            if (response.success) {
                this.showMessage('Target folder removed successfully', 'success');
                
                // Reload configuration
                await this.loadConfig();
            } else {
                throw new Error(response.error || 'Failed to remove target folder');
            }

        } catch (error) {
            console.error('Error removing target folder:', error);
            this.showMessage('Failed to remove target folder: ' + error.message, 'error');
        }
    }

    clearWatchFolderForm() {
        this.setInputValue('watch-folder-path', '');
        this.setInputValue('watch-folder-name', '');
        this.setCheckboxValue('watch-folder-videos', true);
        this.setCheckboxValue('watch-folder-archives', true);
        this.setCheckboxValue('watch-folder-recursive', true);
        this.setInputValue('watch-folder-depth', 1);
    }

    clearTargetFolderForm() {
        this.setInputValue('target-folder-path', '');
        this.setInputValue('target-folder-name', '');
        this.setInputValue('target-folder-priority', 0);
    }

    startPeriodicUpdates() {
        // Update folder lists every 30 seconds to show any external changes
        this.folderListUpdateInterval = setInterval(async () => {
            try {
                await this.loadConfig();
            } catch (error) {
                console.error('Error during periodic update:', error);
            }
        }, 30000);
    }

    stopPeriodicUpdates() {
        if (this.folderListUpdateInterval) {
            clearInterval(this.folderListUpdateInterval);
            this.folderListUpdateInterval = null;
        }
    }

    // Utility methods
    setInputValue(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.value = value;
        }
    }

    getInputValue(id, defaultValue = '') {
        const element = document.getElementById(id);
        if (element) {
            return element.type === 'number' ? parseInt(element.value) || defaultValue : element.value;
        }
        return defaultValue;
    }

    setCheckboxValue(id, checked) {
        const element = document.getElementById(id);
        if (element) {
            element.checked = checked;
        }
    }

    getCheckboxValue(id, defaultValue = false) {
        const element = document.getElementById(id);
        if (element) {
            return element.checked;
        }
        return defaultValue;
    }

    validatePath(input) {
        const path = input.value.trim();
        
        if (!path) {
            this.setInputError(input, 'Path is required');
            return false;
        }

        // Basic path validation
        const invalidChars = /[<>"|?*]/;
        if (invalidChars.test(path)) {
            this.setInputError(input, 'Path contains invalid characters');
            return false;
        }

        this.clearInputError(input);
        return true;
    }

    validateNumericInput(input) {
        const value = parseInt(input.value);
        const min = parseInt(input.min) || 0;
        const max = parseInt(input.max) || Number.MAX_SAFE_INTEGER;

        if (isNaN(value) || value < min || value > max) {
            this.setInputError(input, `Value must be between ${min} and ${max}`);
            return false;
        }

        this.clearInputError(input);
        return true;
    }

    setInputError(input, message) {
        input.classList.add('error');
        
        // Remove existing error message
        const existingError = input.parentNode.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }

        // Add new error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        input.parentNode.appendChild(errorDiv);
    }

    clearInputError(input) {
        input.classList.remove('error');
        
        const errorMessage = input.parentNode.querySelector('.error-message');
        if (errorMessage) {
            errorMessage.remove();
        }
    }

    showLoading(show) {
        const loadingElements = document.querySelectorAll('.loading');
        const saveButton = document.getElementById('save-settings');
        
        loadingElements.forEach(el => {
            el.style.display = show ? 'block' : 'none';
        });

        if (saveButton) {
            saveButton.disabled = show;
            saveButton.textContent = show ? 'Saving...' : 'Save Settings';
        }
    }

    showMessage(message, type = 'info') {
        // Create or update message element
        let messageEl = document.getElementById('settings-message');
        
        if (!messageEl) {
            messageEl = document.createElement('div');
            messageEl.id = 'settings-message';
            messageEl.className = 'message';
            
            // Insert at top of settings container
            const container = document.querySelector('.settings-container');
            if (container) {
                container.insertBefore(messageEl, container.firstChild);
            }
        }

        messageEl.className = `message ${type}`;
        messageEl.textContent = message;
        messageEl.style.display = 'block';

        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (messageEl) {
                messageEl.style.display = 'none';
            }
        }, 5000);

        console.log(`Settings message (${type}): ${message}`);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Extension management
    addExtension(containerId, extension) {
        if (!extension || !extension.trim()) return;

        const container = document.getElementById(containerId);
        if (!container) return;

        // Check if extension already exists
        const existing = container.querySelector(`[data-extension="${extension}"]`);
        if (existing) {
            this.showMessage('Extension already exists', 'warning');
            return;
        }

        // Ensure extension starts with dot
        const normalizedExt = extension.startsWith('.') ? extension : '.' + extension;

        const extensionTag = document.createElement('span');
        extensionTag.className = 'extension-tag';
        extensionTag.innerHTML = `
            ${normalizedExt}
            <button type="button" class="remove-extension" data-extension="${normalizedExt}">×</button>
        `;

        // Add remove functionality
        const removeBtn = extensionTag.querySelector('.remove-extension');
        removeBtn.addEventListener('click', () => {
            extensionTag.remove();
        });

        container.appendChild(extensionTag);
    }

    // Public API for external access
    refresh() {
        this.loadConfig();
    }

    destroy() {
        this.stopPeriodicUpdates();
        this.initialized = false;
        console.log('Settings Manager destroyed');
    }
}

// Auto-initialize when script loads
document.addEventListener('DOMContentLoaded', () => {
    window.settingsManager = new SettingsManager();
});

// Extension input handlers (setup after DOM loads)
document.addEventListener('DOMContentLoaded', () => {
    // Video extension input
    const videoExtInput = document.getElementById('add-video-extension');
    const addVideoExtBtn = document.getElementById('add-video-extension-btn');
    
    if (videoExtInput && addVideoExtBtn) {
        const addVideoExt = () => {
            const ext = videoExtInput.value.trim();
            if (ext && window.settingsManager) {
                window.settingsManager.addExtension('video-extensions', ext);
                videoExtInput.value = '';
            }
        };

        addVideoExtBtn.addEventListener('click', addVideoExt);
        videoExtInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addVideoExt();
            }
        });
    }

    // Archive extension input
    const archiveExtInput = document.getElementById('add-archive-extension');
    const addArchiveExtBtn = document.getElementById('add-archive-extension-btn');
    
    if (archiveExtInput && addArchiveExtBtn) {
        const addArchiveExt = () => {
            const ext = archiveExtInput.value.trim();
            if (ext && window.settingsManager) {
                window.settingsManager.addExtension('archive-extensions', ext);
                archiveExtInput.value = '';
            }
        };

        addArchiveExtBtn.addEventListener('click', addArchiveExt);
        archiveExtInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addArchiveExt();
            }
        });
    }
});

console.log('Settings Manager (Fixed Version) loaded');