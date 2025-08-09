// main.js - Electron Main Process
const { app, BrowserWindow, Tray, Menu, ipcMain, dialog, shell, nativeImage } = require('electron');
const path = require('path');
const axios = require('axios');

// Backend API Configuration
const API_BASE = 'http://localhost:8080/api';

class FileManagerElectronApp {
    constructor() {
        this.mainWindow = null;
        this.tray = null;
        this.backendHealthy = false;
        this.pendingCount = 0;
        this.isQuiting = false;
        
        this.init();
    }

    init() {
        // App event handlers
        app.whenReady().then(() => {
            this.createWindow();
            this.createTray();
            this.setupIPC();
            this.startBackendHealthCheck();
        });

        app.on('window-all-closed', () => {
            // Don't quit on macOS when all windows are closed
            if (process.platform !== 'darwin') {
                app.quit();
            }
        });

        app.on('activate', () => {
            if (BrowserWindow.getAllWindows().length === 0) {
                this.createWindow();
            }
        });

        app.on('before-quit', () => {
            this.isQuiting = true;
        });
    }

    createWindow() {
        // Create the browser window
        this.mainWindow = new BrowserWindow({
            width: 1200,
            height: 800,
            minWidth: 900,
            minHeight: 600,
            icon: path.join(__dirname, 'assets', 'icon.png'), // Add your icon
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                enableRemoteModule: false,
                preload: path.join(__dirname, 'preload.js')
            },
            titleBarStyle: 'default',
            show: false // Don't show until ready
        });

        // Load the app
        this.mainWindow.loadFile('index.html');

        // Show window when ready
        this.mainWindow.once('ready-to-show', () => {
            this.mainWindow.show();
        });

        // Handle window closed
        this.mainWindow.on('closed', () => {
            this.mainWindow = null;
        });

        // Handle minimize to tray
        this.mainWindow.on('minimize', (event) => {
            if (this.tray) {
                event.preventDefault();
                this.mainWindow.hide();
            }
        });

        // Handle close to tray
        this.mainWindow.on('close', (event) => {
            if (!this.isQuiting && this.tray) {
                event.preventDefault();
                this.mainWindow.hide();
            }
        });

        // Open external links in browser
        this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
            shell.openExternal(url);
            return { action: 'deny' };
        });
    }

    createTray() {
        // Create tray icon
        let iconPath;
        if (process.platform === 'win32') {
            iconPath = path.join(__dirname, 'assets', 'tray-icon.ico');
        } else if (process.platform === 'darwin') {
            iconPath = path.join(__dirname, 'assets', 'tray-iconTemplate.png');
        } else {
            iconPath = path.join(__dirname, 'assets', 'tray-icon.png');
        }

        // Fallback if icon doesn't exist
        try {
            this.tray = new Tray(iconPath);
        } catch (error) {
            console.warn('Could not load tray icon, using default');
            this.tray = new Tray(nativeImage.createEmpty());
        }

        this.updateTrayMenu();

        // Handle tray click
        this.tray.on('click', () => {
            this.toggleWindow();
        });

        this.tray.on('double-click', () => {
            this.showWindow();
        });
    }

    updateTrayMenu() {
        if (!this.tray) return;

        const contextMenu = Menu.buildFromTemplate([
            {
                label: 'File Manager',
                type: 'normal',
                enabled: false
            },
            {
                type: 'separator'
            },
            {
                label: `Pending: ${this.pendingCount}`,
                type: 'normal',
                enabled: false
            },
            {
                label: `Backend: ${this.backendHealthy ? 'Connected' : 'Disconnected'}`,
                type: 'normal',
                enabled: false
            },
            {
                type: 'separator'
            },
            {
                label: 'Show Window',
                type: 'normal',
                click: () => this.showWindow()
            },
            {
                label: 'Hide Window',
                type: 'normal',
                click: () => this.hideWindow()
            },
            {
                type: 'separator'
            },
            {
                label: 'Refresh',
                type: 'normal',
                click: () => this.refreshData()
            },
            {
                label: 'Settings',
                type: 'normal',
                click: () => this.openSettings()
            },
            {
                type: 'separator'
            },
            {
                label: 'Quit',
                type: 'normal',
                click: () => {
                    this.isQuiting = true;
                    app.quit();
                }
            }
        ]);

        this.tray.setContextMenu(contextMenu);
        
        // Update tooltip
        let tooltip = `File Manager\nPending: ${this.pendingCount}\nBackend: ${this.backendHealthy ? 'Connected' : 'Disconnected'}`;
        this.tray.setToolTip(tooltip);
    }

    setupIPC() {
        // Handle renderer messages
        ipcMain.handle('get-api-config', () => {
            return { API_BASE };
        });

        ipcMain.handle('update-tray', (event, data) => {
            this.pendingCount = data.pendingCount || 0;
            this.backendHealthy = data.backendHealthy || false;
            this.updateTrayMenu();
        });

        ipcMain.handle('show-message-box', async (event, options) => {
            const result = await dialog.showMessageBox(this.mainWindow, options);
            return result;
        });

        ipcMain.handle('show-open-dialog', async (event, options) => {
            const result = await dialog.showOpenDialog(this.mainWindow, options);
            return result;
        });

        ipcMain.handle('show-save-dialog', async (event, options) => {
            const result = await dialog.showSaveDialog(this.mainWindow, options);
            return result;
        });

        ipcMain.handle('open-external', (event, url) => {
            shell.openExternal(url);
        });

        ipcMain.on('renderer-error', (event, error) => {
            console.error('Renderer error:', error);
        });

        ipcMain.handle('minimize-to-tray', () => {
            this.hideWindow();
        });

        ipcMain.handle('quit-app', () => {
            this.isQuiting = true;
            app.quit();
        });
    }

    async startBackendHealthCheck() {
        // Check backend health every 30 seconds
        const checkHealth = async () => {
            try {
                const response = await axios.get(`${API_BASE}/status`, { timeout: 5000 });
                this.backendHealthy = response.status === 200;
            } catch (error) {
                this.backendHealthy = false;
            }
            this.updateTrayMenu();
        };

        // Initial check
        await checkHealth();
        
        // Periodic checks
        setInterval(checkHealth, 30000);
    }

    // Window management methods
    showWindow() {
        if (this.mainWindow) {
            if (this.mainWindow.isMinimized()) {
                this.mainWindow.restore();
            }
            this.mainWindow.show();
            this.mainWindow.focus();
        }
    }

    hideWindow() {
        if (this.mainWindow) {
            this.mainWindow.hide();
        }
    }

    toggleWindow() {
        if (this.mainWindow) {
            if (this.mainWindow.isVisible()) {
                this.hideWindow();
            } else {
                this.showWindow();
            }
        }
    }

    refreshData() {
        if (this.mainWindow && this.mainWindow.webContents) {
            this.mainWindow.webContents.send('refresh-data');
        }
    }

    openSettings() {
        if (this.mainWindow && this.mainWindow.webContents) {
            this.mainWindow.webContents.send('open-settings');
        }
    }
}

// Create app instance
const fileManagerApp = new FileManagerElectronApp();

// Handle protocol for deep linking (optional)
if (process.defaultApp) {
    if (process.argv.length >= 2) {
        app.setAsDefaultProtocolClient('filemanager', process.execPath, [path.resolve(process.argv[1])]);
    }
} else {
    app.setAsDefaultProtocolClient('filemanager');
}

// Single instance lock
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', (event, commandLine, workingDirectory) => {
        // Someone tried to run a second instance, focus our window instead
        if (fileManagerApp.mainWindow) {
            fileManagerApp.showWindow();
        }
    });
}

console.log('File Manager Electron Main Process started');