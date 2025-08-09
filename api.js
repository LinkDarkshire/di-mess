// api.js - Backend API Communication

class APIManager {
    constructor() {
        this.baseURL = 'http://localhost:8080/api';
        this.cache = new Map();
        this.cacheTimeout = 30000; // 30 seconds
        
        // Initialize with Electron API config if available
        this.initializeConfig();
    }

    async initializeConfig() {
        if (window.electronAPI) {
            try {
                const config = await window.electronAPI.getApiConfig();
                this.baseURL = config.API_BASE;
            } catch (error) {
                console.warn('Could not get API config from Electron:', error);
            }
        }
    }

    // Cache management
    getCacheKey(url, params = {}) {
        return `${url}?${JSON.stringify(params)}`;
    }

    getFromCache(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            return cached.data;
        }
        return null;
    }

    setCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    clearCache() {
        this.cache.clear();
    }

    // HTTP Request wrapper
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const cacheKey = this.getCacheKey(url, options.params);

        // Check cache for GET requests
        if (!options.method || options.method === 'GET') {
            const cached = this.getFromCache(cacheKey);
            if (cached) {
                return cached;
            }
        }

        try {
            const config = {
                method: options.method || 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            };

            if (options.body) {
                config.body = JSON.stringify(options.body);
            }

            const response = await fetch(url, config);
            const data = await response.json();

            // Cache successful GET requests
            if (response.ok && (!options.method || options.method === 'GET')) {
                this.setCache(cacheKey, data);
            }

            return data;

        } catch (error) {
            console.error(`API Request failed: ${endpoint}`, error);
            return {
                success: false,
                error: error.message || 'Network error'
            };
        }
    }

    // System APIs
    async getStatus() {
        return this.request('/status');
    }

    async getStatistics() {
        return this.request('/statistics');
    }

    // Configuration APIs
    async getConfig() {
        return this.request('/config');
    }

    async updateConfig(config) {
        this.clearCache(); // Clear cache when config changes
        return this.request('/config', {
            method: 'POST',
            body: config
        });
    }

    async addWatchFolder(folderData) {
        this.clearCache();
        return this.request('/config/folders/watch', {
            method: 'POST',
            body: folderData
        });
    }

    async addTargetFolder(folderData) {
        this.clearCache();
        return this.request('/config/folders/target', {
            method: 'POST',
            body: folderData
        });
    }

    // Video APIs
    async getPendingVideos() {
        return this.request('/videos/pending');
    }

    async getProcessingVideos() {
        return this.request('/videos/processing');
    }

    async getCompletedVideos() {
        return this.request('/videos/completed');
    }

    async getSeriesOverview() {
        return this.request('/videos/series');
    }

    async approveVideo(filepath, targetFolder = null) {
        return this.request(`/videos/${encodeURIComponent(filepath)}/approve`, {
            method: 'POST',
            body: { target_folder: targetFolder }
        });
    }

    async rejectVideo(filepath) {
        return this.request(`/videos/${encodeURIComponent(filepath)}/reject`, {
            method: 'POST'
        });
    }

    async updateVideoMetadata(filepath, metadata) {
        return this.request(`/videos/${encodeURIComponent(filepath)}/update`, {
            method: 'POST',
            body: metadata
        });
    }

    async moveVideoCustom(filepath, targetFolder, customFilename = null) {
        return this.request(`/videos/${encodeURIComponent(filepath)}/move-custom`, {
            method: 'POST',
            body: {
                target_folder: targetFolder,
                custom_filename: customFilename
            }
        });
    }

    async approveAllVideos() {
        return this.request('/videos/approve-all', {
            method: 'POST'
        });
    }

    async processSeriesBatch(seriesName, targetFolder) {
        return this.request(`/videos/series/${encodeURIComponent(seriesName)}/batch`, {
            method: 'POST',
            body: { target_folder: targetFolder }
        });
    }

    // Archive APIs
    async getPendingArchives() {
        return this.request('/archives/pending');
    }

    async getProcessingArchives() {
        return this.request('/archives/processing');
    }

    async getCompletedArchives() {
        return this.request('/archives/completed');
    }

    async approveArchive(filepath) {
        return this.request(`/archives/${encodeURIComponent(filepath)}/approve`, {
            method: 'POST'
        });
    }

    async rejectArchive(filepath) {
        return this.request(`/archives/${encodeURIComponent(filepath)}/reject`, {
            method: 'POST'
        });
    }

    // Cleanup APIs
    async getStartupCleanupStatus() {
        return this.request('/archives/startup-cleanup/status');
    }

    async getStartupCleanupCandidates() {
        return this.request('/archives/startup-cleanup/candidates');
    }

    async approveCleanupCandidate(filepath, action) {
        return this.request(`/archives/startup-cleanup/${encodeURIComponent(filepath)}/approve`, {
            method: 'POST',
            body: { action }
        });
    }

    async approveAllCleanupCandidates(action) {
        return this.request('/archives/startup-cleanup/approve-all', {
            method: 'POST',
            body: { action }
        });
    }

    // System Control APIs
    async startMonitoring() {
        return this.request('/system/start', {
            method: 'POST'
        });
    }

    async stopMonitoring() {
        return this.request('/system/stop', {
            method: 'POST'
        });
    }

    async cleanupOldEntries(maxAgeHours = 24) {
        return this.request('/system/cleanup', {
            method: 'POST',
            body: { max_age_hours: maxAgeHours }
        });
    }
}

// Create global API instance
window.api = new APIManager();

console.log('API Manager initialized');