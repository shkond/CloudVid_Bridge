/**
 * CloudVid Bridge - Schedule Module
 * Schedule settings management functions
 */

import {
    loadScheduleSettingsApi,
    saveScheduleSettingsApi,
    deleteScheduleSettingsApi,
    validateFolderUrlApi,
    getQuotaStatus
} from './api.js';
import { elements, showToast, updateScheduleStatusDisplay, buildFolderUrl } from './ui.js';

/**
 * Load schedule settings from the server and populate the form
 * @returns {Promise<Object|null>} Settings or null
 */
export async function loadScheduleSettings() {
    const settings = await loadScheduleSettingsApi();
    return settings;
}

/**
 * Populate the schedule form with saved settings
 * @param {Object} settings - Settings object from the server
 */
export function populateScheduleForm(settings) {
    if (!settings) return;

    // Populate unified settings fields
    if (elements.scheduleMaxFiles) elements.scheduleMaxFiles.value = settings.max_files_per_run || 50;
    if (elements.titleTemplate) elements.titleTemplate.value = settings.title_template || '{filename}';
    if (elements.descriptionTemplate) elements.descriptionTemplate.value = settings.description_template || '';
    if (elements.privacyStatus) elements.privacyStatus.value = settings.default_privacy || 'private';
    if (elements.recursiveCheck) elements.recursiveCheck.checked = settings.recursive ?? true;
    if (elements.skipDuplicatesCheck) elements.skipDuplicatesCheck.checked = settings.skip_duplicates ?? true;
    if (elements.includeMd5Check) elements.includeMd5Check.checked = settings.include_md5_hash ?? true;
    if (elements.scheduleEnabled) elements.scheduleEnabled.checked = settings.is_enabled ?? false;
    updateScheduleStatusDisplay(settings.is_enabled);
    if (elements.deleteScheduleBtn) elements.deleteScheduleBtn.style.display = 'inline-block';

    // Set folder from saved settings if available
    if (settings.folder_id && settings.folder_url) {
        if (elements.folderId) elements.folderId.value = settings.folder_id;
        if (elements.folderPath) elements.folderPath.value = settings.folder_name || settings.folder_id;
        if (elements.uploadSettings) elements.uploadSettings.style.display = 'block';
        if (elements.videoPreview) elements.videoPreview.style.display = 'block';
    }
}

/**
 * Save schedule settings to the server
 * @returns {Promise<boolean>} Success status
 */
export async function saveScheduleSettings() {
    const folderUrl = buildFolderUrl();
    if (!folderUrl) {
        showToast('フォルダを選択してください', 'error');
        return false;
    }

    const settings = {
        folder_url: buildFolderUrl(),
        max_files_per_run: parseInt(elements.scheduleMaxFiles?.value || '50', 10),
        title_template: elements.titleTemplate?.value || '{filename}',
        description_template: elements.descriptionTemplate?.value || '',
        default_privacy: elements.privacyStatus?.value || 'private',
        recursive: elements.recursiveCheck?.checked ?? true,
        skip_duplicates: elements.skipDuplicatesCheck?.checked ?? true,
        include_md5_hash: elements.includeMd5Check?.checked ?? true,
        is_enabled: elements.scheduleEnabled?.checked ?? false,
    };

    try {
        await saveScheduleSettingsApi(settings);
        showToast('スケジュール設定を保存しました', 'success');
        if (elements.deleteScheduleBtn) elements.deleteScheduleBtn.style.display = 'inline-block';
        return true;
    } catch (error) {
        showToast(`保存失敗: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Delete schedule settings from the server
 * @returns {Promise<boolean>} Success status
 */
export async function deleteScheduleSettings() {
    if (!confirm('スケジュール設定を削除してもよろしいですか？')) return false;

    try {
        await deleteScheduleSettingsApi();
        showToast('スケジュール設定を削除しました', 'success');
        // Reset form
        if (elements.scheduleFolderUrl) elements.scheduleFolderUrl.value = '';
        if (elements.scheduleEnabled) elements.scheduleEnabled.checked = false;
        updateScheduleStatusDisplay(false);
        if (elements.deleteScheduleBtn) elements.deleteScheduleBtn.style.display = 'none';
        return true;
    } catch (error) {
        showToast(`削除失敗: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Validate a folder URL
 */
export async function validateFolderUrl() {
    const folderUrl = elements.scheduleFolderUrl?.value?.trim();
    if (!folderUrl) {
        showToast('フォルダURLを入力してください', 'error');
        return;
    }

    if (elements.folderValidationStatus) {
        elements.folderValidationStatus.textContent = '検証中...';
        elements.folderValidationStatus.className = 'validation-status validating';
    }

    try {
        const result = await validateFolderUrlApi(folderUrl);

        if (result.valid) {
            if (elements.folderValidationStatus) {
                elements.folderValidationStatus.textContent = `✓ ${result.folder_name}`;
                elements.folderValidationStatus.className = 'validation-status valid';
            }
            showToast(`フォルダ「${result.folder_name}」にアクセスできます`, 'success');
        } else {
            if (elements.folderValidationStatus) {
                elements.folderValidationStatus.textContent = `✗ ${result.error}`;
                elements.folderValidationStatus.className = 'validation-status invalid';
            }
            showToast(result.error || '無効なフォルダURL', 'error');
        }
    } catch (error) {
        if (elements.folderValidationStatus) {
            elements.folderValidationStatus.textContent = '✗ 検証エラー';
            elements.folderValidationStatus.className = 'validation-status invalid';
        }
        showToast('フォルダ検証に失敗しました', 'error');
    }
}

/**
 * Update the quota status display
 */
export async function updateQuotaStatus() {
    if (!elements.quotaStatus) return;

    const data = await getQuotaStatus();
    if (!data) return;

    const percent = data.usage_percentage;
    const remaining = data.remaining;

    elements.quotaStatus.style.display = 'flex';
    const quotaText = elements.quotaStatus.querySelector('.quota-text');

    if (percent >= 100) {
        quotaText.textContent = '100% (上限到達)';
        elements.quotaStatus.classList.add('error');
    } else {
        quotaText.textContent = `${percent}% (残: ${remaining})`;
        elements.quotaStatus.classList.remove('error');
        if (percent > 80) {
            elements.quotaStatus.classList.add('warning');
        } else {
            elements.quotaStatus.classList.remove('warning');
        }
    }
}
