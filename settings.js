<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Manager Settings</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="styles/main.css" rel="stylesheet">
    <style>
        body {
            background: var(--bg-primary);
            padding: var(--spacing-lg);
        }

        .settings-container {
            max-width: 800px;
            margin: 0 auto;
        }

        .settings-section {
            background: var(--bg-primary);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-lg);
            margin-bottom: var(--spacing-lg);
            overflow: hidden;
        }

        .settings-header {
            background: var(--bg-secondary);
            padding: var(--spacing-md) var(--spacing-lg);
            border-bottom: 1px solid var(--border-light);
        }

        .settings-header h2 {
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--text-primary);
            margin: 0;
        }

        .settings-body {
            padding: var(--spacing-lg);
        }

        .folder-list {
            space-y: var(--spacing-md);
        }

        .folder-item {
            display: flex;
            align-items: center;
            gap: var(--spacing-md);
            padding: var(--spacing-md);
            background: var(--bg-secondary);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-md);
            margin-bottom: var(--spacing-sm);
        }

        .folder-info {
            flex: 1;
            min-width: 0;
        }

        .folder-name {
            font-weight: 500;
            color: var(--text-primary);
            margin-bottom: var(--spacing-xs);
        }

        .folder-path {
            font-size: 0.75rem;
            color: var(--text-secondary);
            font-family: 'Courier New', monospace;
            word-break: break-all;
        }

        .folder-actions {
            display: flex;
            gap: var(--spacing-sm);
        }

        .add-folder-form {
            display: none;
            padding: var(--spacing-md);
            background: var(--bg-tertiary);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-md);
            margin-top: var(--spacing-md);
        }

        .add-folder-form.active {
            display: block;
        }

        .settings-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: var(--spacing-lg);
            border-top: 1px solid var(--border-light);
            background: var(--bg-secondary);
        }

        .depth-selector {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            margin-top: var(--spacing-sm);
        }

        .depth-badge {
            background: var(--primary-color);
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: var(--radius-sm);
            font-size: 0.75rem;
        }
    </style>
</head>
<body>
    <div class="settings-container">
        <header style="margin-bottom: var(--spacing-xl);">
            <h1><i class="fas fa-cog"></i> Settings</h1>
            <p style="color: var(--text-secondary); margin-top: var(--spacing-xs);">
                Configure watched folders, target directories, and behavior settings
            </p>
        </header>

        <!-- Watch Folders Section -->
        <div class="settings-section">
            <div class="settings-header">
                <h2><i class="fas fa-eye"></i> Watch Folders (Max: 5)</h2>
            </div>
            <div class="settings-body">
                <p style="color: var(--text-secondary); margin-bottom: var(--spacing-md);">
                    Folders to monitor for new video files and archives
                </p>
                
                <div id="watchFoldersList" class="folder-list">
                    <!-- Watch folders will be loaded here -->
                </div>

                <button class="btn btn-primary" id="addWatchFolderBtn">
                    <i class="fas fa-plus"></i> Add Watch Folder
                </button>

                <!-- Add Watch Folder Form -->
                <div id="addWatchFolderForm" class="add-folder-form">
                    <form id="watchFolderForm">
                        <div class="form-row">
                            <div class="form-group">
                                <label for="watchFolderName">Folder Name:</label>
                                <input type="text" id="watchFolderName" class="input" required>
                            </div>
                            <div class="form-group">
                                <label for="watchFolderPath">Folder Path:</label>
                                <div class="input-group">
                                    <input type="text" id="watchFolderPath" class="input" required>
                                    <button type="button" class="btn btn-secondary" id="browseWatchFolderBtn">
                                        <i class="fas fa-folder-open"></i>
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="watchVideos" checked> Watch Videos
                                </label>
                            </div>
                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="watchArchives" checked> Watch Archives
                                </label>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="videoSearchDepth">Video Search Depth:</label>
                            <div class="depth-selector">
                                <input type="range" id="videoSearchDepth" min="0" max="3" value="1" class="range-input">
                                <span class="depth-badge" id="depthDisplay">1 Level Deep</span>
                            </div>
                            <small class="form-help">
                                0 = Only main folder, 1 = One subfolder deep, 2+ = Deeper nesting
                            </small>
                        </div>

                        <div style="display: flex; gap: var(--spacing-md); margin-top: var(--spacing-md);">
                            <button type="submit" class="btn btn-success">
                                <i class="fas fa-save"></i> Save
                            </button>
                            <button type="button" class="btn btn-secondary" id="cancelWatchFolderBtn">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>

        <!-- Target Folders Section -->
        <div class="settings-section">
            <div class="settings-header">
                <h2><i class="fas fa-bullseye"></i> Target Folders (Max: 3)</h2>
            </div>
            <div class="settings-body">
                <p style="color: var(--text-secondary); margin-bottom: var(--spacing-md);">
                    Destination folders where organized videos will be moved
                </p>
                
                <div id="targetFoldersList" class="folder-list">
                    <!-- Target folders will be loaded here -->
                </div>

                <button class="btn btn-primary" id="addTargetFolderBtn">
                    <i class="fas fa-plus"></i> Add Target Folder
                </button>

                <!-- Add Target Folder Form -->
                <div id="addTargetFolderForm" class="add-folder-form">
                    <form id="targetFolderForm">
                        <div class="form-row">
                            <div class="form-group">
                                <label for="targetFolderName">Folder Name:</label>
                                <input type="text" id="targetFolderName" class="input" required>
                            </div>
                            <div class="form-group">
                                <label for="targetFolderPath">Folder Path:</label>
                                <div class="input-group">
                                    <input type="text" id="targetFolderPath" class="input" required>
                                    <button type="button" class="btn btn-secondary" id="browseTargetFolderBtn">
                                        <i class="fas fa-folder-open"></i>
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="folderPriority">Priority:</label>
                            <select id="folderPriority" class="select">
                                <option value="1">Low Priority</option>
                                <option value="5" selected>Normal Priority</option>
                                <option value="10">High Priority</option>
                            </select>
                            <small class="form-help">Higher priority folders are suggested first</small>
                        </div>

                        <div style="display: flex; gap: var(--spacing-md); margin-top: var(--spacing-md);">
                            <button type="submit" class="btn btn-success">
                                <i class="fas fa-save"></i> Save
                            </button>
                            <button type="button" class="btn btn-secondary" id="cancelTargetFolderBtn">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>

        <!-- Behavior Settings Section -->
        <div class="settings-section">
            <div class="settings-header">
                <h2><i class="fas fa-sliders-h"></i> Behavior Settings</h2>
            </div>
            <div class="settings-body">
                <div class="form-group">
                    <label for="minFileSize">Minimum File Size (MB):</label>
                    <input type="number" id="minFileSize" class="input" min="1" max="10000" value="10">
                    <small class="form-help">Ignore video files smaller than this size</small>
                </div>

                <div class="form-group">
                    <label for="downloadStability">Download Stability Time (seconds):</label>
                    <input type="number" id="downloadStability" class="input" min="5" max="300" value="30">
                    <small class="form-help">Wait time to ensure file download is complete</small>
                </div>

                <div class="form-group">
                    <label>
                        <input type="checkbox" id="enableNotifications" checked>
                        Enable System Notifications
                    </label>
                </div>

                <div class="form-group">
                    <label>
                        <input type="checkbox" id="autoExtractArchives" checked>
                        Automatically Extract Archives
                    </label>
                </div>

                <div class="form-group">
                    <label>
                        <input type="checkbox" id="deleteArchivesAfterExtract" checked>
                        Delete Archives After Extraction
                    </label>
                </div>

                <div class="form-group">
                    <label>
                        <input type="checkbox" id="cleanupExtractedArchivesOnStartup" checked>
                        Check for Already Extracted Archives on Startup
                    </label>
                </div>

                <div class="form-group">
                    <label>
                        <input type="checkbox" id="autoCleanupExtractedArchives">
                        Automatically Clean Up Extracted Archives (No Confirmation)
                    </label>
                    <small class="form-help">When disabled, you'll be asked to confirm cleanup actions</small>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="settings-footer">
            <div>
                <button class="btn btn-secondary" id="resetToDefaultsBtn">
                    <i class="fas fa-undo"></i> Reset to Defaults
                </button>
            </div>
            <div style="display: flex; gap: var(--spacing-md);">
                <button class="btn btn-secondary" id="cancelBtn">Cancel</button>
                <button class="btn btn-success" id="saveAllBtn">
                    <i class="fas fa-save"></i> Save All Settings
                </button>
            </div>
        </div>
    </div>

    <!-- Loading Overlay -->
    <div class="loading-overlay hidden" id="loadingOverlay">
        <div class="loading-spinner">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Saving settings...</p>
        </div>
    </div>

    <!-- Scripts -->
    <script src="js/api.js"></script>
    <script src="js/settings.js"></script>
</body>
</html>