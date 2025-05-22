// coding-platform/static/js/ui.js

// Make switchTab globally available if needed by main.js
var switchTab = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log("Initializing UI components...");

    // --- Sliding Panel Logic ---
    const bottomPanel = document.getElementById('bottom-panel');
    const panelHandle = document.getElementById('panel-handle');
    const panelContent = bottomPanel ? bottomPanel.querySelector('.panel-content') : null;
    const tabContentWrapper = bottomPanel ? bottomPanel.querySelector('.tab-content-wrapper') : null;

    if (panelHandle && bottomPanel && panelContent) {
        panelHandle.addEventListener('click', () => {
            bottomPanel.classList.toggle('open');
            // Optional: Focus logic when opening/closing (consider accessibility)
            // if (bottomPanel.classList.contains('open')) {
            //     const activeTabContent = panelContent.querySelector('.tab-content.active');
            //     const firstFocusable = activeTabContent?.querySelector('textarea, input:not([type=hidden]), button, [tabindex]:not([tabindex="-1"])');
            //     if (firstFocusable) {
            //         setTimeout(() => firstFocusable.focus({ preventScroll: true }), 100); // Delay slightly
            //     }
            // }
        });
         console.log("Sliding panel handler attached.");
    } else {
        console.error("Sliding panel elements (panel, handle, or content wrapper) not found!");
    }


    // --- Tab Logic ---
    const tabsContainer = bottomPanel ? bottomPanel.querySelector('.tabs') : null;
    const tabButtons = tabsContainer ? Array.from(tabsContainer.querySelectorAll('.tab-button')) : [];
    const tabContents = tabContentWrapper ? Array.from(tabContentWrapper.querySelectorAll('.tab-content')) : [];

    switchTab = function(targetTabId) { // Assign to the globally declared variable
        if (!targetTabId || !tabsContainer || !tabContentWrapper) {
            console.error("Cannot switch tab - missing elements or target ID.");
            return false;
        }

        let foundTarget = false;
        // Deactivate all tabs and content
        tabButtons.forEach(button => button.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));

        // Activate the target tab and content
        const targetButton = tabsContainer.querySelector(`.tab-button[data-tab="${targetTabId}"]`);
        const targetContent = tabContentWrapper.querySelector(`#${targetTabId}`);

        if (targetButton && targetContent) {
            targetButton.classList.add('active');
            targetContent.classList.add('active');
            // Scroll the wrapper to the top when switching tabs
            if(tabContentWrapper) tabContentWrapper.scrollTop = 0;
            console.log(`UI: Switched to tab: ${targetTabId}`);
            foundTarget = true;
        } else {
            console.error(`UI: Tab button or content not found for ID: ${targetTabId}`);
        }
        return foundTarget;
    }


    if (tabButtons.length > 0 && tabContents.length > 0) {
         console.log(`Found ${tabButtons.length} tab buttons and ${tabContents.length} tab contents.`);
        tabButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                const targetTabId = event.currentTarget.getAttribute('data-tab');
                switchTab(targetTabId);
            });
        });

        // Initialize by activating the tab marked 'active' in HTML, or default to the first.
        const initiallyActiveButton = tabsContainer.querySelector('.tab-button.active');
        let initialTabId = null;

        if (initiallyActiveButton) {
             initialTabId = initiallyActiveButton.getAttribute('data-tab');
             console.log(`Found initially active tab button for: ${initialTabId}`);
        } else if (tabButtons.length > 0) {
            initialTabId = tabButtons[0].getAttribute('data-tab'); // Default to first tab
            console.log(`No initially active tab found, defaulting to first: ${initialTabId}`);
        }

        if (initialTabId) {
           const success = switchTab(initialTabId);
           if (!success && tabButtons.length > 0) {
               // Fallback if initial active failed (e.g., mismatch between button and content)
               console.warn(`Initial tab switch failed for ${initialTabId}, falling back to first available.`);
               switchTab(tabButtons[0].getAttribute('data-tab'));
           }
        } else {
            console.warn("UI: No tab buttons found to set initial active tab.");
        }

    } else {
        console.error("UI: Tab buttons or tab contents elements not found! Tab functionality disabled.");
    }

}); // End DOMContentLoaded