// renderer.js - Frontend Application Logic (Renderer Process)

// Main Application Controller
class FileManagerApp {
    constructor() {
        this.initialized = false;
        this.connectionRetryCount = 0;
        this.maxRetryCount = 5;
        this.retryInterval = 5000; // 5 seconds
        this.API_BASE = 'http://localhost:8080/api';

        this.init();
    }

    async init() {
        if (this.initialized) return;

        console.log('Initializing File Manager Frontend...');

        try {
            // Get API configuration from main process
            if (window.electronAPI) {
                const config = await window.electronAPI.getApiConfig();
                this.API_BASE = config.API_BASE;
            }

            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.init());
                return;
            }

            // Initialize components (they're already initialized globally)
            // api, ui, and fileHandlers are already available

            // Setup initial connection
            await this.establishConnection();

            // Load initial data
            await this.loadInitialData();

            // Setup event listeners
            this.setupEventListeners();

            // Start auto-refresh
            if (window.fileHandlers) {
                window.fileHandlers.startAutoRefresh();
            }

            // Start connection monitoring
            this.startConnectionMonitoring();

            // Setup Electron event listeners
            this.setupElectronEvents();

            this.initialized = true;
            console.log('File Manager Frontend initialized successfully');

            // Show welcome message
            if (window.ui) {
                window.ui.showToast('Welcome', 'File Manager is ready', 'success');
            }

        } catch (error) {
            console.error('Failed to initialize application:', error);
            if (window.ui) {
                window.ui.showToast('Error', 'Failed to initialize application', 'error');
                window.ui.updateConnectionStatus(false);
            }
        }
    }

    async establishConnection() {
        console.log('Establishing backend connection...');
        
        try {
            const response = await window.api.getStatus();
            
            if (response.success) {
                window.ui.updateConnectionStatus(true, response.data);
                this.connectionRetryCount = 0;
                console.log('Connected to backend:', response.data);
                
                // Update tray with connection status
                this.updateTray({
                    backendHealthy: true,
                    pendingCount: this.getPendingCount()
                });
                
                return true;
            } else {
                throw new Error(response.error || 'Unknown connection error');
            }

        } catch (error) {
            console.error('Connection failed:', error);
            window.ui.updateConnectionStatus(false);
            
            // Update tray with connection status
            this.updateTray({
                backendHealthy: false,
                pendingCount: 0
            });
            
            // Retry connection
            if (this.connectionRetryCount < this.maxRetryCount) {
                this.connectionRetryCount++;
                console.log(`Retrying connection... (${this.connectionRetryCount}/${this.maxRetryCount})`);
                
                setTimeout(() => {
                    this.establishConnection();
                }, this.retryInterval);
            } else {
                window.ui.showToast('Connection Failed', 'Could not connect to backend. Please check if the backend is running.', 'error');
            }
            
            return false;
        }
    }

    async loadInitialData() {
        console.log('Loading initial data...');

        try {
            // Load configuration first
            await window.fileHandlers.loadTargetFolders();

            // Load default tab data (pending)
            await window.fileHandlers.loadPendingItems();

            // Check for cleanup candidates
            await this.checkCleanupCandidates();

            // Update tray with pending count
            this.updateTray({
                backendHealthy: true,
                pendingCount: this.getPendingCount()
            });

        } catch (error) {
            console.error('Failed to load initial data:', error);
            window.ui.showToast('Warning', 'Some data could not be loaded', 'warning');
        }
    }

    async checkCleanupCandidates() {
        try {
            const response = await window.api.getStartupCleanupStatus();
            
            if (response.success && response.data.data.has_candidates) {
                const count = response.data.data.candidate_count;
                
                // Show notification about cleanup candidates
                window.ui.showToast(
                    'Cleanup Required', 
                    `${count} already extracted archive${count > 1 ? 's' : ''} found. Check the Cleanup tab.`, 
                    'warning'
                );

                // Update cleanup badge
                window.ui.updateBadges({
                    cleanup: count
                });
            }

        } catch (error) {
            console.error('Failed to check cleanup candidates:', error);
        }
    }

    setupEventListeners() {
        // Handle keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });

        // Handle window focus/blur for auto-refresh
        window.addEventListener('focus', () => {
            console.log('Window focused, refreshing data...');
            this.refreshCurrentTab();
        });

        // Handle online/offline status
        window.addEventListener('online', () => {
            console.log('Connection restored');
            this.establishConnection();
        });

        window.addEventListener('offline', () => {
            console.log('Connection lost');
            window.ui.updateConnectionStatus(false);
            this.updateTray({ backendHealthy: false });
        });

        // Handle unload to cleanup
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    setupElectronEvents() {
        if (!window.electronAPI) return;

        // Listen for refresh requests from main process
        window.electronAPI.onRefreshData(() => {
            console.log('Refresh requested from main process');
            this.refreshCurrentTab();
        });

        // Listen for settings requests from main process
        window.electronAPI.onOpenSettings(() => {
            console.log('Settings requested from main process');
            window.ui.openSettingsWindow();
        });
    }

    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + R: Refresh
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            this.refreshCurrentTab();
        }

        // Ctrl/Cmd + ,: Settings
        if ((e.ctrlKey || e.metaKey) && e.key === ',') {
            e.preventDefault();
            window.ui.openSettingsWindow();
        }

        // Tab numbers: Switch tabs
        if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '4') {
            e.preventDefault();
            const tabIndex = parseInt(e.key) - 1;
            const tabs = ['pending', 'processing', 'completed', 'cleanup'];
            if (tabs[tabIndex]) {
                window.ui.switchTab(tabs[tabIndex]);
            }
        }

        // Escape: Close modals
        if (e.key === 'Escape') {
            const activeModal = document.querySelector('.modal.active');
            if (activeModal) {
                window.ui.closeModal(activeModal.id);
            }
        }

        // Ctrl/Cmd + W: Minimize to tray (Electron only)
        if ((e.ctrlKey || e.metaKey) && e.key === 'w' && window.electronAPI) {
            e.preventDefault();
            window.electronAPI.minimizeToTray();
        }
    }

    refreshCurrentTab() {
        window.api.clearCache();
        window.ui.refreshCurrentTab();
        
        // Update tray after refresh
        setTimeout(() => {
            this.updateTray({
                backendHealthy: true,
                pendingCount: this.getPendingCount()
            });
        }, 1000);
    }

    startConnectionMonitoring() {
        // Monitor connection every 30 seconds
        setInterval(async () => {
            try {
                const response = await window.api.getStatus();
                
                if (response.success) {
                    if (!window.ui.connectionStatus || window.ui.connectionStatus !== 'connected') {
                        window.ui.updateConnectionStatus(true, response.data);
                        window.ui.showToast('Reconnected', 'Connection restored', 'success');
                        this.connectionRetryCount = 0;
                    }
                    
                    this.updateTray({
                        backendHealthy: true,
                        pendingCount: this.getPendingCount()
                    });
                } else {
                    window.ui.updateConnectionStatus(false);
                    this.updateTray({ backendHealthy: false });
                }

            } catch (error) {
                window.ui.updateConnectionStatus(false);
                this.updateTray({ backendHealthy: false });
                console.error('Connection monitoring failed:', error);
            }
        }, 30000);
    }

    // ===== UTILITY METHODS =====

    getPendingCount() {
        if (!window.fileHandlers || !window.fileHandlers.currentData) return 0;
        
        const pendingVideos = window.fileHandlers.currentData.pendingVideos?.length || 0;
        const pendingArchives = window.fileHandlers.currentData.pendingArchives?.length || 0;
        
        return pendingVideos + pendingArchives;
    }

    updateTray(data) {
        if (window.electronAPI) {
            window.electronAPI.updateTray(data);
        }
    }

    async getSystemStatus() {
        try {
            const response = await window.api.getStatus();
            if (response.success) {
                return response.data;
            }
        } catch (error) {
            console.error('Failed to get system status:', error);
        }
        return null;
    }

    async getStatistics() {
        try {
            const response = await window.api.getStatistics();
            if (response.success) {
                return response.data;
            }
        } catch (error) {
            console.error('Failed to get statistics:', error);
        }
        return null;
    }

    // ===== DEBUG METHODS =====

    debug() {
        return {
            app: this,
            api: window.api,
            ui: window.ui,
            fileHandlers: window.fileHandlers,
            currentData: window.fileHandlers?.currentData,
            status: this.getSystemStatus(),
            statistics: this.getStatistics()
        };
    }

    async runDiagnostics() {
        console.log('Running File Manager diagnostics...');
        
        const diagnostics = {
            timestamp: new Date().toISOString(),
            environment: window.electronAPI ? 'electron' : 'browser',
            frontend: {
                initialized: this.initialized,
                currentTab: window.ui?.currentTab,
                connectionRetryCount: this.connectionRetryCount,
                loadingStates: window.ui ? Array.from(window.ui.loadingStates) : [],
                modalStates: document.querySelectorAll('.modal.active').length
            },
            backend: null,
            data: {
                pendingVideos: window.fileHandlers?.currentData?.pendingVideos?.length || 0,
                pendingArchives: window.fileHandlers?.currentData?.pendingArchives?.length || 0,
                processingItems: window.fileHandlers?.currentData?.processingItems?.length || 0,
                completedItems: window.fileHandlers?.currentData?.completedItems?.length || 0,
                cleanupCandidates: window.fileHandlers?.currentData?.cleanupCandidates?.length || 0,
                targetFolders: window.fileHandlers?.currentData?.targetFolders?.length || 0
            },
            errors: []
        };

        try {
            diagnostics.backend = await this.getSystemStatus();
        } catch (error) {
            diagnostics.errors.push(`Backend connection: ${error.message}`);
        }

        console.log('Diagnostics results:', diagnostics);
        return diagnostics;
    }

    cleanup() {
        console.log('Cleaning up File Manager...');
        
        // Clear any intervals/timeouts
        // Clear cache
        if (window.api) {
            window.api.clearCache();
        }
        
        // Remove Electron event listeners
        if (window.electronAPI) {
            window.electronAPI.removeAllListeners('refresh-data');
            window.electronAPI.removeAllListeners('open-settings');
        }
        
        console.log('Cleanup completed');
    }

    // ===== ERROR HANDLING =====

    handleError(error, context = 'Unknown') {
        console.error(`Error in ${context}:`, error);
        
        const errorMessage = error.message || 'An unexpected error occurred';
        if (window.ui) {
            window.ui.showToast('Error', `${context}: ${errorMessage}`, 'error');
        }
        
        // Send error to main process if in Electron
        if (window.electronAPI) {
            window.electronAPI.reportError({
                context,
                error: errorMessage,
                timestamp: Date.now()
            });
        }
    }
}

// Global error handling
window.addEventListener('error', (e) => {
    console.error('Uncaught error:', e.error);
    if (window.app) {
        window.app.handleError(e.error, 'Uncaught Exception');
    }
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
    if (window.app) {
        window.app.handleError(e.reason, 'Unhandled Promise');
    }
});

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new FileManagerApp();
});

// Make app available globally for debugging
window.FileManagerApp = FileManagerApp;

console.log('File Manager Frontend (Renderer Process) loaded');