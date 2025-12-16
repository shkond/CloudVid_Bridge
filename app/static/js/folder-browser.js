/**
 * CloudVid Bridge - Folder Browser Module
 * Handles folder navigation and selection in the modal
 */

import { fetchFiles } from './api.js';
import { elements, showToast, closeModalFn } from './ui.js';

// State for folder browser
export let currentFolderId = 'root';
export let currentFolderName = 'My Drive';
export let selectedFolderId = null;
export let selectedFolderName = null;
export let isNavigating = false; // Debounce flag for folder navigation

/**
 * Set current folder state (used by other modules)
 */
export function setCurrentFolder(folderId, folderName) {
    currentFolderId = folderId;
    currentFolderName = folderName;
}

/**
 * Set selected folder state
 */
export function setSelectedFolder(folderId, folderName) {
    selectedFolderId = folderId;
    selectedFolderName = folderName;
}

/**
 * Load contents of a folder into the folder list
 * @param {string} folderId - Folder ID to load
 */
export async function loadFolderContents(folderId) {
    if (!elements.folderList) return;

    elements.folderList.innerHTML = '<p class="loading">読み込み中...</p>';
    selectedFolderId = null;
    if (elements.selectFolderBtn) elements.selectFolderBtn.disabled = true;

    const files = await fetchFiles(folderId);
    currentFolderId = folderId;

    if (files.length === 0) {
        elements.folderList.innerHTML = '<p class="empty-state">フォルダが空です</p>';
        return;
    }

    elements.folderList.innerHTML = '';

    files.forEach(file => {
        const item = document.createElement('div');
        item.className = `folder-item ${file.file_type}`;
        item.dataset.id = file.id;
        item.dataset.name = file.name;
        item.dataset.type = file.file_type;

        const icon = file.file_type === 'folder'
            ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" stroke="currentColor" stroke-width="2"/></svg>'
            : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M23 7l-7 5 7 5V7z" stroke="currentColor" stroke-width="2"/><rect x="1" y="5" width="15" height="14" rx="2" stroke="currentColor" stroke-width="2"/></svg>';

        item.innerHTML = `${icon}<span>${file.name}</span>`;

        item.addEventListener('click', (e) => {
            // Prevent double-click from firing twice
            if (isNavigating) {
                console.log('[FolderBrowser] Navigation in progress, ignoring click');
                return;
            }

            if (file.file_type === 'folder') {
                // Single-click to enter folder for easier navigation
                console.log(`[FolderBrowser] Navigating to folder: ${file.name} (${file.id})`);
                navigateToFolder(file.id, file.name);
                return;
            }
            // For non-folder items (videos), select them
            document.querySelectorAll('.folder-item.selected').forEach(el => el.classList.remove('selected'));
            item.classList.add('selected');
            selectedFolderId = file.id;
            selectedFolderName = file.name;
            if (elements.selectFolderBtn) elements.selectFolderBtn.disabled = false;
        });

        elements.folderList.appendChild(item);
    });
}

/**
 * Navigate to a folder and update breadcrumb
 * Includes debouncing to prevent rapid duplicate navigation (e.g., double-click)
 * @param {string} folderId - Folder ID to navigate to
 * @param {string} folderName - Folder name for display
 */
export function navigateToFolder(folderId, folderName) {
    // Debounce: prevent rapid navigation (e.g., double-click)
    if (isNavigating) {
        console.log(`[FolderBrowser] Ignoring duplicate navigation to: ${folderName}`);
        return;
    }
    isNavigating = true;

    // Validate folder ID
    if (!folderId || typeof folderId !== 'string') {
        console.error(`[FolderBrowser] Invalid folder ID: ${folderId}`);
        isNavigating = false;
        return;
    }

    console.log(`[FolderBrowser] Navigating to: ${folderName} (${folderId})`);

    // Update current folder tracking for "Select current folder" functionality
    currentFolderId = folderId;
    currentFolderName = folderName;

    // Update breadcrumb
    if (elements.breadcrumb) {
        const item = document.createElement('span');
        item.className = 'breadcrumb-item';
        item.dataset.id = folderId;
        item.textContent = ` / ${folderName}`;
        item.addEventListener('click', () => {
            // Remove all items after this one
            while (item.nextSibling) {
                item.nextSibling.remove();
            }
            currentFolderId = folderId;
            currentFolderName = folderName;
            loadFolderContents(folderId);
        });
        elements.breadcrumb.appendChild(item);
    }

    loadFolderContents(folderId).finally(() => {
        // Release debounce after navigation completes
        setTimeout(() => {
            isNavigating = false;
        }, 100);
    });
}

/**
 * Select the current folder (the one currently being viewed)
 */
export function selectCurrentFolder() {
    if (!currentFolderId) return;

    // Set variables as if selected from list
    selectedFolderId = currentFolderId;
    selectedFolderName = currentFolderName;

    selectFolder();
}

/**
 * Confirm folder selection and close modal
 */
export function selectFolder() {
    // If nothing selected but we're in a subfolder, select current folder
    if (!selectedFolderId && currentFolderId && currentFolderId !== 'root') {
        selectedFolderId = currentFolderId;
        selectedFolderName = currentFolderName;
    }

    if (!selectedFolderId) {
        showToast('フォルダを選択してください', 'warning');
        return;
    }

    // Validate folder URL format
    const folderUrl = `https://drive.google.com/drive/folders/${selectedFolderId}`;
    if (!/^[a-zA-Z0-9_-]+$/.test(selectedFolderId)) {
        console.error(`[FolderBrowser] Invalid folder ID format: ${selectedFolderId}`);
        showToast('不正なフォルダIDです', 'error');
        return;
    }
    console.log(`[FolderBrowser] Selected folder: ${selectedFolderName} (${selectedFolderId})`);
    console.log(`[FolderBrowser] Folder URL: ${folderUrl}`);

    if (elements.folderPath) elements.folderPath.value = selectedFolderName || 'Selected Folder';
    if (elements.folderId) elements.folderId.value = selectedFolderId;

    // Update current folder for schedule settings
    currentFolderId = selectedFolderId;
    currentFolderName = selectedFolderName;

    // Show upload settings and preview
    if (elements.uploadSettings) elements.uploadSettings.style.display = 'block';
    if (elements.videoPreview) elements.videoPreview.style.display = 'block';

    closeModalFn();
    showToast(`フォルダ "${selectedFolderName}" を選択しました`, 'success');
}

/**
 * Reset the folder browser state (for opening modal fresh)
 */
export function resetBreadcrumb() {
    if (elements.breadcrumb) {
        const root = elements.breadcrumb.querySelector('.breadcrumb-item');
        if (root) {
            while (root.nextSibling) {
                root.nextSibling.remove();
            }
        }
    }
    currentFolderId = 'root';
    currentFolderName = 'My Drive';
    selectedFolderId = null;
    selectedFolderName = null;
}
