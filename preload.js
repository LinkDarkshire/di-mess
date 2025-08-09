// preload.js - Electron Preload Script
const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
    // Configuration
    getApiConfig: () => ipcRenderer.invoke('get-api-config'),
    
    // Tray management
    updateTray: (data) => ipcRenderer.invoke('update-tray', data),
    
    // Dialog APIs
    showMessageBox: (options) => ipcRenderer.invoke('show-message-box', options),
    showOpenDialog: (options) => ipcRenderer.invoke('show-open-dialog', options),
    showSaveDialog: (options) => ipcRenderer.invoke('show-save-dialog', options),
    
    // External links
    openExternal: (url) => ipcRenderer.invoke('open-external', url),
    
    // Window management
    minimizeToTray: () => ipcRenderer.invoke('minimize-to-tray'),
    quitApp: () => ipcRenderer.invoke('quit-app'),
    
    // Error reporting
    reportError: (error) => ipcRenderer.send('renderer-error', error),
    
    // Event listeners
    onRefreshData: (callback) => ipcRenderer.on('refresh-data', callback),
    onOpenSettings: (callback) => ipcRenderer.on('open-settings', callback),
    
    // Remove listeners
    removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel)
});

console.log('Preload script loaded');