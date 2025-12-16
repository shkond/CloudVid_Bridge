/**
 * CloudVid Bridge - UI Module
 * UI helper functions and DOM element references
 */

// DOM Elements - centralized references
export const elements = {
    folderPath: document.getElementById('folder-path'),
    folderId: document.getElementById('folder-id'),
    browseBtn: document.getElementById('browse-folders'),
    uploadSettings: document.getElementById('upload-settings'),
    videoPreview: document.getElementById('video-preview'),
    videoList: document.getElementById('video-list'),
    videoCount: document.getElementById('video-count'),
    scanBtn: document.getElementById('scan-folder'),
    addToQueueBtn: document.getElementById('add-to-queue'),
    queueList: document.getElementById('queue-list'),
    queueCount: document.getElementById('queue-count'),
    progressInfo: document.getElementById('progress-info'),
    // Modal
    modal: document.getElementById('folder-modal'),
    closeModal: document.getElementById('close-modal'),
    folderList: document.getElementById('folder-list'),
    breadcrumb: document.getElementById('folder-breadcrumb'),
    selectFolderBtn: document.getElementById('select-folder'),
    cancelSelectBtn: document.getElementById('cancel-select'),
    // Settings
    titleTemplate: document.getElementById('title-template'),
    descriptionTemplate: document.getElementById('description-template'),
    privacyStatus: document.getElementById('privacy-status'),
    recursiveCheck: document.getElementById('recursive'),
    skipDuplicatesCheck: document.getElementById('skip-duplicates'),
    includeMd5Check: document.getElementById('include-md5'),
    // Toast
    toastContainer: document.getElementById('toast-container'),
    // Quota
    quotaStatus: document.getElementById('quota-status'),
    // Updates
    selectCurrentFolderBtn: document.getElementById('select-current-folder'),
    // Schedule Settings
    scheduleFolderUrl: document.getElementById('schedule-folder-url'),
    scheduleMaxFiles: document.getElementById('schedule-max-files'),
    scheduleTitleTemplate: document.getElementById('schedule-title-template'),
    scheduleDescriptionTemplate: document.getElementById('schedule-description-template'),
    schedulePrivacy: document.getElementById('schedule-privacy'),
    scheduleRecursive: document.getElementById('schedule-recursive'),
    scheduleSkipDuplicates: document.getElementById('schedule-skip-duplicates'),
    scheduleIncludeMd5: document.getElementById('schedule-include-md5'),
    scheduleEnabled: document.getElementById('schedule-enabled'),
    scheduleStatus: document.getElementById('schedule-status'),
    saveScheduleBtn: document.getElementById('save-schedule'),
    deleteScheduleBtn: document.getElementById('delete-schedule'),
    validateFolderBtn: document.getElementById('validate-folder'),
    folderValidationStatus: document.getElementById('folder-validation-status'),
};

// File size limits (in bytes) - should match backend config
export const MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024; // 5GB
export const WARNING_FILE_SIZE = 4 * 1024 * 1024 * 1024; // 4GB

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Toast type: 'info', 'success', 'warning', 'error'
 */
export function showToast(message, type = 'info') {
    if (!elements.toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Open the folder browser modal
 */
export function openModal() {
    if (elements.modal) {
        elements.modal.style.display = 'flex';
    }
}

/**
 * Close the folder browser modal
 */
export function closeModalFn() {
    if (elements.modal) {
        elements.modal.style.display = 'none';
    }
}

/**
 * Format bytes to human-readable string
 * @param {number} bytes - Bytes to format
 * @returns {string} Formatted string (e.g., "1.5 GB")
 */
export function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Render a list of videos in the preview area
 * @param {Array} videos - Array of video objects
 * @returns {boolean} True if any oversized files were found
 */
export function renderVideoList(videos) {
    if (!elements.videoList) return false;

    elements.videoList.innerHTML = '';

    let hasOversizedFiles = false;

    videos.forEach(video => {
        const item = document.createElement('div');
        item.className = 'video-item';

        const sizeStr = video.size ? formatBytes(video.size) : 'N/A';

        // Determine file size status
        let sizeClass = '';
        let sizeIcon = '';
        let sizeTooltip = '';

        if (video.size && video.size > MAX_FILE_SIZE) {
            sizeClass = 'size-error';
            sizeIcon = '⚠️';
            sizeTooltip = ' (ファイルサイズ超過: 5GB以下にしてください)';
            hasOversizedFiles = true;
        } else if (video.size && video.size > WARNING_FILE_SIZE) {
            sizeClass = 'size-warning';
            sizeIcon = '⚡';
            sizeTooltip = ' (大きなファイル)';
        }

        item.innerHTML = `
            <div class="video-info">
                <span class="video-name">${video.name}</span>
                <span class="video-path">${video.path}</span>
            </div>
            <span class="video-size ${sizeClass}" title="${sizeStr}${sizeTooltip}">${sizeIcon} ${sizeStr}</span>
        `;

        elements.videoList.appendChild(item);
    });

    // Update add to queue button based on oversized files
    if (elements.addToQueueBtn) {
        if (hasOversizedFiles) {
            elements.addToQueueBtn.disabled = true;
            elements.addToQueueBtn.title = '5GBを超えるファイルがあります';
        } else {
            elements.addToQueueBtn.disabled = false;
            elements.addToQueueBtn.title = '';
        }
    }

    return hasOversizedFiles;
}

/**
 * Flatten nested folder structure into a flat video array
 * @param {Object} folder - Folder object with files and subfolders
 * @param {string} path - Current path prefix
 * @returns {Array} Flattened array of videos with paths
 */
export function flattenVideos(folder, path = '') {
    let videos = [];
    const currentPath = path ? `${path}/${folder.name}` : folder.name;

    folder.files.forEach(file => {
        videos.push({ ...file, path: currentPath });
    });

    folder.subfolders.forEach(subfolder => {
        videos = videos.concat(flattenVideos(subfolder, currentPath));
    });

    return videos;
}

/**
 * Update the schedule status display
 * @param {boolean} enabled - Whether schedule is enabled
 */
export function updateScheduleStatusDisplay(enabled) {
    if (elements.scheduleStatus) {
        elements.scheduleStatus.textContent = enabled ? '有効' : '無効';
        elements.scheduleStatus.className = enabled ? 'schedule-status enabled' : 'schedule-status disabled';
    }
}

/**
 * Build a Google Drive folder URL from the currently selected folder ID
 * @returns {string} Folder URL or empty string
 */
export function buildFolderUrl() {
    const folderId = elements.folderId?.value;
    if (!folderId || folderId === 'root') {
        return '';
    }
    return `https://drive.google.com/drive/folders/${folderId}`;
}
