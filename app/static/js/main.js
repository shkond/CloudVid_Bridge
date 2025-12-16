/**
 * CloudVid Bridge - Main Module
 * Event listeners and initialization
 */

import { elements, openModal, closeModalFn, updateScheduleStatusDisplay } from './ui.js';
import {
    loadFolderContents,
    navigateToFolder,
    selectFolder,
    selectCurrentFolder,
    resetBreadcrumb
} from './folder-browser.js';
import { refreshQueueList, performScan, addToQueue } from './queue.js';
import {
    loadScheduleSettings,
    populateScheduleForm,
    saveScheduleSettings,
    deleteScheduleSettings,
    validateFolderUrl,
    updateQuotaStatus
} from './schedule.js';

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Browse folders button
    if (elements.browseBtn) {
        elements.browseBtn.addEventListener('click', () => {
            openModal();
            loadFolderContents('root');
            // Reset select current folder button text
            if (elements.selectCurrentFolderBtn) {
                elements.selectCurrentFolderBtn.textContent = 'このフォルダを選択';
                elements.selectCurrentFolderBtn.disabled = false;
            }
        });
    }

    // Modal controls
    if (elements.closeModal) {
        elements.closeModal.addEventListener('click', closeModalFn);
    }
    if (elements.cancelSelectBtn) {
        elements.cancelSelectBtn.addEventListener('click', closeModalFn);
    }
    if (elements.selectFolderBtn) {
        elements.selectFolderBtn.addEventListener('click', selectFolder);
    }

    // Breadcrumb root click
    if (elements.breadcrumb) {
        const root = elements.breadcrumb.querySelector('.breadcrumb-item');
        if (root) {
            root.addEventListener('click', () => {
                // Clear breadcrumb except root
                while (root.nextSibling) {
                    root.nextSibling.remove();
                }
                loadFolderContents('root');
            });
        }
    }

    // Scan button
    if (elements.scanBtn) {
        elements.scanBtn.addEventListener('click', performScan);
    }

    // Add to queue button
    if (elements.addToQueueBtn) {
        elements.addToQueueBtn.addEventListener('click', addToQueue);
    }

    // Schedule Settings
    if (elements.saveScheduleBtn) {
        elements.saveScheduleBtn.addEventListener('click', saveScheduleSettings);
    }
    if (elements.deleteScheduleBtn) {
        elements.deleteScheduleBtn.addEventListener('click', deleteScheduleSettings);
    }
    if (elements.validateFolderBtn) {
        elements.validateFolderBtn.addEventListener('click', validateFolderUrl);
    }
    if (elements.scheduleEnabled) {
        elements.scheduleEnabled.addEventListener('change', (e) => {
            updateScheduleStatusDisplay(e.target.checked);
        });
    }

    // Close modal on outside click
    if (elements.modal) {
        elements.modal.addEventListener('click', (e) => {
            if (e.target === elements.modal) {
                closeModalFn();
            }
        });
    }

    // Select Current Folder button
    if (elements.selectCurrentFolderBtn) {
        elements.selectCurrentFolderBtn.addEventListener('click', selectCurrentFolder);
    }

    // Initial data load
    refreshQueueList();
    updateQuotaStatus();

    // Load schedule settings
    loadScheduleSettings().then(settings => {
        if (settings) populateScheduleForm(settings);
    });

    // Periodic queue refresh
    setInterval(() => {
        refreshQueueList();
        updateQuotaStatus();
    }, 5000);
});
