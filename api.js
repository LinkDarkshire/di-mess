// api.js - API Communication Layer
const { ipcRenderer } = require('electron');

class FileManagerAPI {
    constructor() {
        this.isElectron = typeof require !== 'undefined';
        this.cache = new Map();
        this.cacheTimeout = 30000; // 30 seconds
    }

    /**
     * Make API call through Electron IPC or direct HTTP
     */
    async apiCall(method, endpoint, data = null, useCache = false) {
        const cacheKey = `${method}:${endpoint}:${JSON.stringify(data)}`;
        
        // Check cache for GET requests
        if (useCache && method === 'GET' && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
        }

        try {
            let response;

            if (this.isElectron) {
                // Use Electron IPC
                response = await ipcRenderer.invoke('api-call', method, endpoint, data);
            } else {
                // Direct HTTP call (fallback for development)
                const config = {
                    method: method.toLowerCase(),
                    headers: {
                        'Content-Type': 'application/json'
                    }
                };

                if (data) {
                    if (method === 'GET') {
                        const params = new URLSearchParams(data);
                        endpoint += `?${params}`;
                    } else {
                        config.body = JSON.stringify(data);
                    }
                }

                const fetchResponse = await fetch(`http://localhost:8080/api${endpoint}`, config);
                const responseData = await fetchResponse.json();
                
                response = {
                    success: fetchResponse.ok,
                    data: responseData
                };
            }

            // Cache successful GET responses
            if (useCache && method === 'GET' && response.success) {
                this.cache.set(cacheKey, {
                    data: response,
                    timestamp: Date.now()
                });
            }

            return response;

        } catch (error) {
            console.error(`API call failed: ${method} ${endpoint}`, error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Clear API cache
     */
    clearCache() {
        this.cache.clear();
    }

    // ===== SYSTEM ENDPOINTS =====

    async getStatus() {
        return this.apiCall('GET', '/status', null, true);
    }

    async getStatistics() {
        return this.apiCall('GET', '/statistics', null, true);
    }

    async startMonitoring() {
        return this.apiCall('POST', '/system/start');
    }

    async stopMonitoring() {
        return this.apiCall('POST', '/system/stop');
    }

    // ===== CONFIG ENDPOINTS =====

    async getConfig() {
        return this.apiCall('GET', '/config', null, true);
    }

    async updateConfig(settings) {
        this.clearCache(); // Clear cache after config changes
        return this.apiCall('POST', '/config', { settings });
    }

    async addWatchFolder(folderData) {
        this.clearCache();
        return this.apiCall('POST', '/config/folders/watch', folderData);
    }

    async addTargetFolder(folderData) {
        this.clearCache();
        return this.apiCall('POST', '/config/folders/target', folderData);
    }

    // ===== VIDEO ENDPOINTS =====

    async getPendingVideos() {
        return this.apiCall('GET', '/videos/pending', null, true);
    }

    async getProcessingVideos() {
        return this.apiCall('GET', '/videos/processing', null, true);
    }

    async getCompletedVideos() {
        return this.apiCall('GET', '/videos/completed', null, true);
    }

    async getSeriesOverview() {
        return this.apiCall('GET', '/videos/series', null, true);
    }

    async approveVideo(filepath, targetFolder = null) {
        this.clearCache();
        const data = targetFolder ? { target_folder: targetFolder } : null;
        return this.apiCall('POST', `/videos/${encodeURIComponent(filepath)}/approve`, data);
    }

    async rejectVideo(filepath) {
        this.clearCache();
        return this.apiCall('POST', `/videos/${encodeURIComponent(filepath)}/reject`);
    }

    async updateVideoMetadata(filepath, seriesName, episodeNumber, seasonNumber) {
        this.clearCache();
        return this.apiCall('POST', `/videos/${encodeURIComponent(filepath)}/update`, {
            series_name: seriesName,
            episode_number: episodeNumber,
            season_number: seasonNumber
        });
    }

    async moveVideoCustom(filepath, targetFolder, customFilename = null) {
        this.clearCache();
        return this.apiCall('POST', `/videos/${encodeURIComponent(filepath)}/move-custom`, {
            target_folder: targetFolder,
            custom_filename: customFilename
        });
    }

    async approveAllVideos() {
        this.clearCache();
        return this.apiCall('POST', '/videos/approve-all');
    }

    async processSeriesBatch(seriesName, targetFolder) {
        this.clearCache();
        return this.apiCall('POST', `/videos/series/${encodeURIComponent(seriesName)}/batch`, {
            target_folder: targetFolder
        });
    }

    // ===== ARCHIVE ENDPOINTS =====

    async getPendingArchives() {
        return this.apiCall('GET', '/archives/pending', null, true);
    }

    async getProcessingArchives() {
        return this.apiCall('GET', '/archives/processing', null, true);
    }

    async getCompletedArchives() {
        return this.apiCall('GET', '/archives/completed', null, true);
    }

    async approveArchive(filepath) {
        this.clearCache();
        return this.apiCall('POST', `/archives/${encodeURIComponent(filepath)}/approve`);
    }

    async rejectArchive(filepath) {
        this.clearCache();
        return this.apiCall('POST', `/archives/${encodeURIComponent(filepath)}/reject`);
    }

    // ===== CLEANUP ENDPOINTS =====

    async getStartupCleanupStatus() {
        return this.apiCall('GET', '/archives/startup-cleanup/status', null, true);
    }

    async getStartupCleanupCandidates() {
        return this.apiCall('GET', '/archives/startup-cleanup/candidates', null, true);
    }

    async approveCleanupCandidate(filepath, action) {
        this.clearCache();
        return this.apiCall('POST', `/archives/startup-cleanup/${encodeURIComponent(filepath)}/approve`, {
            action: action // 'delete' or 'extract'
        });
    }

    async approveAllCleanupCandidates(action) {
        this.clearCache();
        return this.apiCall('POST', '/archives/startup-cleanup/approve-all', {
            action: action
        });
    }

    // ===== UTILITY METHODS =====

    /**
     * Format file size in human readable format
     */
    formatFileSize(bytes) {
        if (!bytes) return '0 B';
        
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Format confidence score
     */
    formatConfidence(confidence) {
        if (confidence === undefined || confidence === null) return 'Unknown';
        
        const percentage = Math.round(confidence * 100);
        
        if (percentage >= 80) return { level: 'high', text: `${percentage}%` };
        if (percentage >= 50) return { level: 'medium', text: `${percentage}%` };
        return { level: 'low', text: `${percentage}%` };
    }

    /**
     * Format timestamp
     */
    formatTime(timestamp) {
        if (!timestamp) return 'Unknown';
        
        const date = new Date(timestamp * 1000);
        return date.toLocaleString();
    }

    /**
     * Get file extension
     */
    getFileExtension(filename) {
        return filename.split('.').pop().toLowerCase();
    }

    /**
     * Get file type icon
     */
    getFileTypeIcon(filename, type) {
        if (type === 'video') {
            return 'fas fa-play-circle';
        } else if (type === 'archive') {
            return 'fas fa-file-archive';
        } else {
            const ext = this.getFileExtension(filename);
            
            // Video extensions
            if (['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', 'mpg', 'mpeg'].includes(ext)) {
                return 'fas fa-play-circle';
            }
            
            // Archive extensions  
            if (['zip', 'rar', '7z', 'tar', 'gz', 'bz2'].includes(ext)) {
                return 'fas fa-file-archive';
            }
            
            return 'fas fa-file';
        }
    }

    /**
     * Validate episode number
     */
    validateEpisode(episode) {
        if (!episode) return false;
        const num = parseInt(episode);
        return !isNaN(num) && num > 0 && num <= 9999;
    }

    /**
     * Validate season number
     */
    validateSeason(season) {
        if (!season) return true; // Season is optional
        const num = parseInt(season);
        return !isNaN(num) && num > 0 && num <= 99;
    }

    /**
     * Clean series name
     */
    cleanSeriesName(name) {
        if (!name) return '';
        
        return name
            .trim()
            .replace(/[<>:"/\\|?*]/g, ' ') // Replace invalid filename chars
            .replace(/\s+/g, ' ') // Replace multiple spaces
            .trim();
    }

    /**
     * Generate suggested filename
     */
    generateFilename(seriesName, episodeNumber, seasonNumber = 1, extension = 'mkv') {
        const cleanSeries = this.cleanSeriesName(seriesName);
        const season = seasonNumber.toString().padStart(2, '0');
        const episode = episodeNumber.toString().padStart(2, '0');
        
        return `${cleanSeries} - S${season}E${episode}.${extension}`;
    }

    /**
     * Get status color class
     */
    getStatusClass(status) {
        const statusColors = {
            'pending': 'warning',
            'approved': 'info', 
            'processing': 'warning',
            'completed': 'success',
            'error': 'danger',
            'rejected': 'secondary'
        };
        
        return statusColors[status] || 'secondary';
    }

    /**
     * Debounce function for search/filter inputs
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Check if path is valid
     */
    isValidPath(path) {
        if (!path || typeof path !== 'string') return false;
        
        // Basic path validation
        const invalidChars = /[<>:"|?*]/;
        return !invalidChars.test(path) && path.length > 0;
    }

    /**
     * Extract series name from filename
     */
    extractSeriesFromFilename(filename) {
        if (!filename) return '';
        
        // Remove extension
        const nameWithoutExt = filename.replace(/\.[^/.]+$/, '');
        
        // Remove common patterns
        let seriesName = nameWithoutExt
            .replace(/[_\-\.]/g, ' ') // Replace separators with spaces
            .replace(/\b\d{1,4}[px]\b/gi, '') // Remove resolution (720p, 1080p, etc)
            .replace(/\b(bluray|webrip|webdl|hdtv|dvdrip)\b/gi, '') // Remove source
            .replace(/\b\d{1,4}\b/g, '') // Remove standalone numbers
            .replace(/\s+/g, ' ') // Normalize spaces
            .trim();
        
        return seriesName;
    }
}

// Create global API instance
const api = new FileManagerAPI();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
}