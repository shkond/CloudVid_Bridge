/**
 * CloudVid Bridge - API Module
 * API-related functions for communicating with the backend
 */

import { showToast } from './ui.js';

/**
 * Fetch files from a Google Drive folder
 * @param {string} folderId - Folder ID to fetch files from
 * @returns {Promise<Array>} List of files
 */
export async function fetchFiles(folderId = 'root') {
    try {
        const response = await fetch(`/drive/files?folder_id=${folderId}&video_only=true`);
        if (!response.ok) throw new Error('Failed to fetch files');
        return await response.json();
    } catch (error) {
        showToast('ファイル取得に失敗しました', 'error');
        return [];
    }
}

/**
 * Scan a folder for video files
 * @param {string} folderId - Folder ID to scan
 * @param {boolean} recursive - Whether to scan subfolders
 * @returns {Promise<Object|null>} Scan result or null on error
 */
export async function scanFolder(folderId, recursive = false) {
    try {
        const response = await fetch('/drive/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                folder_id: folderId,
                recursive: recursive,
                video_only: true,
            }),
        });
        if (!response.ok) throw new Error('Failed to scan folder');
        return await response.json();
    } catch (error) {
        showToast('フォルダスキャンに失敗しました', 'error');
        return null;
    }
}

/**
 * Upload a folder to the queue
 * @param {string} folderId - Folder ID to upload
 * @param {Object} settings - Upload settings
 * @returns {Promise<Object|null>} Upload result or null on error
 */
export async function uploadFolder(folderId, settings) {
    try {
        const response = await fetch('/drive/folder/upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                folder_id: folderId,
                recursive: settings.recursive,
                max_files: 100,
                skip_duplicates: settings.skipDuplicates,
                settings: {
                    title_template: settings.titleTemplate,
                    description_template: settings.descriptionTemplate,
                    include_md5_hash: settings.includeMd5,
                    default_privacy: settings.privacy,
                },
            }),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        return await response.json();
    } catch (error) {
        showToast(`アップロード失敗: ${error.message}`, 'error');
        return null;
    }
}

/**
 * Get the current queue status
 * @returns {Promise<Object>} Queue status with jobs array
 */
export async function getQueueStatus() {
    try {
        const response = await fetch('/queue/jobs');
        if (!response.ok) throw new Error('Failed to get queue');
        return await response.json();
    } catch (error) {
        return { jobs: [], status: { total_jobs: 0 } };
    }
}

/**
 * Cancel a queue job
 * @param {string} jobId - Job ID to cancel
 * @returns {Promise<boolean>} Success status
 */
export async function cancelJobApi(jobId) {
    const response = await fetch(`/queue/jobs/${jobId}/cancel`, { method: 'POST' });
    if (!response.ok) {
        const contentType = response.headers.get('content-type');
        let errorMessage = 'Failed to cancel job';
        if (contentType && contentType.includes('application/json')) {
            const error = await response.json();
            errorMessage = error.detail || errorMessage;
        } else {
            const text = await response.text();
            errorMessage = text || `HTTP ${response.status}`;
        }
        throw new Error(errorMessage);
    }
    return true;
}

/**
 * Delete a queue job
 * @param {string} jobId - Job ID to delete
 * @returns {Promise<boolean>} Success status
 */
export async function deleteJobApi(jobId) {
    const response = await fetch(`/queue/jobs/${jobId}`, { method: 'DELETE' });
    if (!response.ok) {
        const contentType = response.headers.get('content-type');
        let errorMessage = 'Failed to delete job';
        if (contentType && contentType.includes('application/json')) {
            const error = await response.json();
            errorMessage = error.detail || errorMessage;
        } else {
            const text = await response.text();
            errorMessage = text || `HTTP ${response.status}`;
        }
        throw new Error(errorMessage);
    }
    return true;
}

/**
 * Get YouTube quota status
 * @returns {Promise<Object|null>} Quota data or null on error
 */
export async function getQuotaStatus() {
    try {
        const response = await fetch('/youtube/quota');
        if (!response.ok) return null;
        return await response.json();
    } catch (error) {
        console.error('Failed to get quota:', error);
        return null;
    }
}

/**
 * Load schedule settings from the server
 * @returns {Promise<Object|null>} Schedule settings or null
 */
export async function loadScheduleSettingsApi() {
    try {
        const response = await fetch('/settings/schedule');
        if (!response.ok) return null;
        return await response.json();
    } catch (error) {
        console.error('Failed to load schedule settings:', error);
        return null;
    }
}

/**
 * Save schedule settings to the server
 * @param {Object} settings - Schedule settings to save
 * @returns {Promise<boolean>} Success status
 */
export async function saveScheduleSettingsApi(settings) {
    const response = await fetch('/settings/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save settings');
    }
    return true;
}

/**
 * Delete schedule settings from the server
 * @returns {Promise<boolean>} Success status
 */
export async function deleteScheduleSettingsApi() {
    const response = await fetch('/settings/schedule', { method: 'DELETE' });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete settings');
    }
    return true;
}

/**
 * Validate a folder URL
 * @param {string} folderUrl - Folder URL to validate
 * @returns {Promise<Object>} Validation result
 */
export async function validateFolderUrlApi(folderUrl) {
    const response = await fetch('/settings/schedule/validate-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_url: folderUrl }),
    });
    return await response.json();
}
