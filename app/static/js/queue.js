/**
 * CloudVid Bridge - Queue Module
 * Queue management and display functions
 */

import { getQueueStatus, cancelJobApi, deleteJobApi, uploadFolder } from './api.js';
import { elements, showToast, flattenVideos, renderVideoList } from './ui.js';
import { scanFolder } from './api.js';
import { currentFolderId } from './folder-browser.js';

// Store scanned videos for queue addition
let scannedVideos = [];

/**
 * Get the currently scanned videos
 */
export function getScannedVideos() {
    return scannedVideos;
}

/**
 * Refresh the queue list display
 */
export async function refreshQueueList() {
    const data = await getQueueStatus();

    if (elements.queueCount) {
        elements.queueCount.textContent = data.status?.total_jobs || data.jobs?.length || 0;
    }

    if (!elements.queueList) return;

    if (!data.jobs || data.jobs.length === 0) {
        elements.queueList.innerHTML = '<p class="empty-state">アップロード待ちの動画はありません</p>';
        return;
    }

    elements.queueList.innerHTML = '';

    data.jobs.forEach(job => {
        // Skip completed jobs - they're automatically in upload_history
        if (job.status === 'completed') return;

        const item = document.createElement('div');
        item.className = `queue-item status-${job.status}`;

        const progressBar = job.progress > 0
            ? `<div class="progress-bar"><div class="progress-fill" style="width: ${job.progress}%"></div></div>`
            : '';

        let actionBtn = '';
        if (job.status === 'pending' || job.status === 'downloading') {
            actionBtn = `<button class="btn-icon btn-cancel" data-action="cancel" data-job-id="${job.id}" title="キャンセル">⛔</button>`;
        } else if (job.status !== 'uploading') {
            actionBtn = `<button class="btn-icon btn-delete" data-action="delete" data-job-id="${job.id}" title="削除">🗑️</button>`;
        }

        item.innerHTML = `
            <div class="job-info">
                <span class="job-name">${job.drive_file_name}</span>
                <span class="job-status">${job.status} ${job.message ? '- ' + job.message : ''}</span>
            </div>
            ${progressBar}
            ${actionBtn}
        `;

        elements.queueList.appendChild(item);
    });

    // Add event delegation for action buttons
    elements.queueList.addEventListener('click', handleQueueAction);

    // Update progress section
    const activeJobs = data.jobs.filter(j =>
        j.status === 'downloading' || j.status === 'uploading'
    );

    if (elements.progressInfo) {
        if (activeJobs.length === 0) {
            elements.progressInfo.innerHTML =
                '<p class="empty-state">アップロード中の動画はありません</p>';
        } else {
            elements.progressInfo.innerHTML = '';
            activeJobs.forEach(job => {
                const progressItem = document.createElement('div');
                progressItem.className = 'progress-item';

                const statusText = job.status === 'downloading'
                    ? 'ダウンロード中'
                    : 'アップロード中';

                progressItem.innerHTML = `
                    <div class="progress-header">
                        <span class="progress-filename">${job.drive_file_name}</span>
                        <span class="progress-percentage">${Math.round(job.progress)}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${job.progress}%"></div>
                    </div>
                    <div class="progress-status">${statusText}: ${job.message}</div>
                `;

                elements.progressInfo.appendChild(progressItem);
            });
        }
    }
}

/**
 * Handle queue action button clicks via event delegation
 */
async function handleQueueAction(event) {
    const button = event.target.closest('[data-action]');
    if (!button) return;

    const action = button.dataset.action;
    const jobId = button.dataset.jobId;

    if (action === 'cancel') {
        await cancelJob(jobId);
    } else if (action === 'delete') {
        await deleteJob(jobId);
    }
}

/**
 * Cancel a queue job
 * @param {string} jobId - Job ID to cancel
 */
export async function cancelJob(jobId) {
    if (!confirm('このジョブをキャンセルしてもよろしいですか？')) return;

    try {
        await cancelJobApi(jobId);
        showToast('ジョブをキャンセルしました', 'success');
        refreshQueueList();
    } catch (error) {
        showToast(`キャンセル失敗: ${error.message}`, 'error');
    }
}

/**
 * Delete a queue job
 * @param {string} jobId - Job ID to delete
 */
export async function deleteJob(jobId) {
    if (!confirm('このジョブを削除してもよろしいですか？\n\n注意: アップロード履歴からも完全に削除されます。')) return;

    try {
        await deleteJobApi(jobId);
        showToast('ジョブを削除しました', 'success');
        refreshQueueList();
    } catch (error) {
        showToast(`削除失敗: ${error.message}`, 'error');
    }
}

/**
 * Perform a folder scan for videos
 */
export async function performScan() {
    if (!currentFolderId || currentFolderId === 'root') {
        showToast('フォルダを選択してください', 'warning');
        return;
    }

    const recursive = elements.recursiveCheck?.checked ?? true;

    if (elements.videoList) elements.videoList.innerHTML = '<p class="loading">スキャン中...</p>';
    if (elements.scanBtn) elements.scanBtn.disabled = true;

    const result = await scanFolder(currentFolderId, recursive);

    if (elements.scanBtn) elements.scanBtn.disabled = false;

    if (!result) {
        if (elements.videoList) elements.videoList.innerHTML = '<p class="empty-state">スキャンに失敗しました</p>';
        return;
    }

    scannedVideos = flattenVideos(result.folder);

    if (elements.videoCount) elements.videoCount.textContent = scannedVideos.length;

    if (scannedVideos.length === 0) {
        if (elements.videoList) elements.videoList.innerHTML = '<p class="empty-state">動画が見つかりませんでした</p>';
        if (elements.addToQueueBtn) elements.addToQueueBtn.disabled = true;
        return;
    }

    renderVideoList(scannedVideos);
    if (elements.addToQueueBtn) elements.addToQueueBtn.disabled = false;
}

/**
 * Add scanned videos to the upload queue
 */
export async function addToQueue() {
    if (!currentFolderId) return;

    const settings = {
        titleTemplate: elements.titleTemplate?.value || '{filename}',
        descriptionTemplate: elements.descriptionTemplate?.value || '',
        privacy: elements.privacyStatus?.value || 'private',
        recursive: elements.recursiveCheck?.checked ?? true,
        skipDuplicates: elements.skipDuplicatesCheck?.checked ?? true,
        includeMd5: elements.includeMd5Check?.checked ?? true,
    };

    if (elements.addToQueueBtn) elements.addToQueueBtn.disabled = true;
    showToast('キューに追加中...', 'info');

    const result = await uploadFolder(currentFolderId, settings);

    if (elements.addToQueueBtn) elements.addToQueueBtn.disabled = false;

    if (result) {
        showToast(`${result.added_count}件をキューに追加しました`, 'success');
        if (result.skipped_count > 0) {
            showToast(`${result.skipped_count}件をスキップしました`, 'warning');
        }
        refreshQueueList();
    }
}

// Make functions available globally for inline onclick handlers (legacy support)
window.cancelJob = cancelJob;
window.deleteJob = deleteJob;
