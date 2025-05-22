// coding-platform/static/js/main.js

// Ensure editor object is accessible, defined in editor.js
// Ensure ui functions like switchTab are accessible, defined in ui.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("[main.js] DOM fully loaded and parsed.");

    // --- Global Elements Cache ---
    const runButton = document.getElementById('run-button');
    const optimizeButton = document.getElementById('optimize-button');
    const languageSelect = document.getElementById('language-select');
    const outputArea = document.getElementById('output-area');
    const geminiGenerateButton = document.getElementById('gemini-generate-button');
    const geminiPrompt = document.getElementById('gemini-prompt');
    const geminiOutputArea = document.getElementById('gemini-output-area');
    const panelHandle = document.getElementById('panel-handle');

    // Metrics elements
    const metricRuntime = document.getElementById('metric-runtime');
    const metricCpu = document.getElementById('metric-cpu');
    const metricMem = document.getElementById('metric-mem');
    const metricTimeComp = document.getElementById('metric-time-comp');
    const metricSpaceComp = document.getElementById('metric-space-comp');

    // --- State ---
    let isBusy = false; // General flag for backend operations (run, generate, optimize)

    // --- Check essential elements ---
    if (!runButton) console.error("[main.js] Run button not found!");
    if (!optimizeButton) console.error("[main.js] Optimize button not found!");
    if (!languageSelect) console.error("[main.js] Language select not found!");
    if (!outputArea) console.error("[main.js] Output area not found!");
    if (!geminiGenerateButton) console.error("[main.js] Gemini generate button not found!");
    if (!geminiPrompt) console.error("[main.js] Gemini prompt textarea not found!");
    if (!geminiOutputArea) console.error("[main.js] Gemini output area not found!");
    // Editor existence is checked within checkEditor() before use


    // --- Event Listeners ---
    if (runButton) {
        runButton.addEventListener('click', handleRunCode);
    }
    if (optimizeButton) {
        optimizeButton.addEventListener('click', handleOptimizeCode);
    }
    if (geminiGenerateButton) {
        geminiGenerateButton.addEventListener('click', handleGenerateCode);
    }
    if (languageSelect) {
        languageSelect.addEventListener('change', handleLanguageChange);
        // Initial mode setting is now triggered from editor.js after successful init
        // waitForEditorAndSetMode(); // -> Replaced by call from editor.js
    } else {
         console.warn("[main.js] Language select not found, cannot bind change handler.");
    }


    // --- Core Functions ---

    function checkEditor() {
        // Checks if the global 'editor' variable (from editor.js) is defined and looks valid
        if (typeof editor === 'undefined' || editor === null) {
            console.error("[main.js] checkEditor: ACE editor instance ('editor') is not available.");
            alert("Error: Code editor is not ready. Please reload the page or check the console.");
            return false;
        }
        // Check if it has essential methods, indicating it's likely a real ACE instance
        if (typeof editor.getValue !== 'function' || typeof editor.setValue !== 'function') {
             console.error("[main.js] checkEditor: ACE editor instance exists but seems improperly initialized (missing methods).");
             alert("Error: Code editor initialization incomplete. Please reload the page or check the console.");
             return false;
        }
        // console.log("[main.js] checkEditor: Editor instance appears valid.");
        return true; // Indicate success
    }

    // This function is now primarily called from editor.js upon successful init
    window.handleLanguageChange = function(event) { // Make it global for editor.js call
         if (!checkEditor()) {
             console.warn("[main.js] handleLanguageChange: Editor not ready, cannot set mode.");
             return;
         }
         const lang = event.target.value;
         let mode = 'ace/mode/python';
         if (lang === 'cpp') {
             mode = 'ace/mode/c_cpp';
         }
         try {
            editor.session.setMode(mode);
            console.log(`[main.js] Editor mode changed to ${mode}`);
         } catch (e) {
             console.error(`[main.js] Error setting editor mode to ${mode}:`, e);
         }
    }

    function handleRunCode() {
        if (isBusy) {
             console.warn("[main.js] Run cancelled: Operation already in progress.");
             return;
        }
        if (!checkEditor()) return; // Stop if editor isn't ready

        const code = editor.getValue();
        const language = languageSelect.value;

        if (!code.trim()) {
            updateOutputArea("Error: Code editor is empty.", true);
            if (typeof switchTab === 'function') switchTab('output-tab');
            return;
        }

        setBusyState(true, runButton, 'Running...');
        updateOutputArea(`Running ${language} code...\nPlease wait...`, false, true);
        clearMetrics("Running...");
        if (typeof switchTab === 'function') switchTab('output-tab');

        fetch('/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ code: code, language: language }),
        })
        .then(handleFetchResponse)
        .then(data => {
            console.log("[main.js] Run Result:", data);
            processRunResult(data);
            if (typeof switchTab === 'function') switchTab('output-tab');
        })
        .catch(error => {
            console.error('[main.js] Error running code:', error);
            updateOutputArea(`Execution Error: ${error.message}\nCheck server logs for details.`, true);
            clearMetrics("Execution failed.");
            if (typeof switchTab === 'function') switchTab('output-tab');
        })
        .finally(() => {
            setBusyState(false, runButton, 'Run Code');
        });
    }

    function handleOptimizeCode() {
        if (isBusy) {
             console.warn("[main.js] Optimize cancelled: Operation already in progress.");
             return;
        }
        if (!checkEditor()) return; // Stop if editor isn't ready

        const code = editor.getValue();
        const language = languageSelect.value;

        if (!code.trim()) {
            showTemporaryMessage("Code editor is empty, nothing to optimize.", "warning");
            return;
        }

        setBusyState(true, optimizeButton, 'Optimizing...');
        showTemporaryMessage("Requesting AI code optimization...", "info");

        fetch('/optimize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ code: code, language: language }),
        })
        .then(handleFetchResponse)
        .then(data => {
            console.log("[main.js] Optimize Result:", data);
            if (data.optimized_code && !data.optimized_code.startsWith("Error:")) {
                 if (!checkEditor()) return; // Re-check editor before setting value
                const currentCursorPosition = editor.getCursorPosition();
                editor.setValue(data.optimized_code, -1); // Replace editor content, cursor to start
                // Try to restore cursor position (might not be perfect after code change)
                try { editor.moveCursorToPosition(currentCursorPosition); } catch(e) { console.warn("Couldn't restore cursor position after optimize."); }
                editor.clearSelection();
                showTemporaryMessage("Code optimized by AI and updated in editor.", "success");
            } else {
                 // Handle cases where AI returns an error string or empty data
                 const errorMessage = data.optimized_code || "Optimization failed: No optimized code returned by AI.";
                 showTemporaryMessage(errorMessage, "error");
            }
        })
        .catch(error => {
            console.error('[main.js] Error optimizing code:', error);
            showTemporaryMessage(`Optimization Request Error: ${error.message}`, "error");
        })
        .finally(() => {
            setBusyState(false, optimizeButton, 'Optimize Code (AI)');
        });
    }

    function handleGenerateCode() {
        if (isBusy) {
             console.warn("[main.js] Generate cancelled: Operation already in progress.");
             return;
        }

        const prompt = geminiPrompt.value;
        const language = languageSelect.value; // Use current language context

        if (!prompt.trim()) {
            updateGeminiOutput("// Error: Prompt cannot be empty.", true);
             if (typeof switchTab === 'function') switchTab('gemini-tab');
            geminiPrompt.focus();
            return;
        }

        setBusyState(true, geminiGenerateButton, 'Generating...');
        updateGeminiOutput("// Generating code with AI, please wait...", false, true);
        if (typeof switchTab === 'function') switchTab('gemini-tab');

        fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ prompt: prompt, language: language }),
        })
        .then(handleFetchResponse)
        .then(data => {
            console.log("[main.js] AI Generation Result:", data);
            if (data.generated_code && !data.generated_code.startsWith("Error:")) {
                 updateGeminiOutput(data.generated_code);
                 // Could add a "Copy to Editor" button here
            } else {
                 const errorMessage = data.generated_code || "// Failed to generate code. Empty response from AI.";
                 updateGeminiOutput(errorMessage, true);
            }
        })
        .catch(error => {
            console.error('[main.js] Error generating code:', error);
            updateGeminiOutput(`// AI Generation Error: ${error.message}`, true);
        })
        .finally(() => {
             setBusyState(false, geminiGenerateButton, 'Generate Code');
        });
    }


    // --- Helper Functions ---

    async function handleFetchResponse(response) {
        // Tries to parse JSON, throws detailed error on failure
        let data;
        try {
            data = await response.json();
        } catch (e) {
            // Handle cases where response is not valid JSON (e.g., server crash HTML)
            console.error("[main.js] Failed to parse JSON response:", e);
            throw new Error(`Server returned non-JSON response (Status: ${response.status} ${response.statusText})`);
        }

        if (!response.ok) {
            const errorMsg = data?.error || response.statusText || `HTTP error ${response.status}`;
            console.error(`[main.js] Fetch error ${response.status}: ${errorMsg}`);
            throw new Error(errorMsg);
        }
        return data;
    }

    function setBusyState(busy, buttonElement = null, busyText = 'Working...') {
        isBusy = busy;
        // Disable all major action buttons when busy
        const buttonsToToggle = [runButton, optimizeButton, geminiGenerateButton];
        buttonsToToggle.forEach(btn => {
            if (btn) btn.disabled = busy;
        });

        // Update text for the specific button that triggered the action
        if (buttonElement) {
            if (busy && !buttonElement.dataset.originalText) {
                buttonElement.dataset.originalText = buttonElement.textContent; // Store original text
            }
            buttonElement.textContent = busy ? busyText : (buttonElement.dataset.originalText || 'Submit'); // Restore or set busy text
        }
    }

    function processRunResult(data) {
        let outputContent = "";
        let hasError = false;

        // Prepend error if it exists
        if (data.error) {
            outputContent += "Error:\n------\n" + data.error;
            hasError = true;
        }
        // Append output if it exists
        if (data.output) {
            // Add separator if error also exists
            outputContent += (outputContent ? "\n\nOutput:\n-------\n" : "Output:\n-------\n") + data.output;
        }
        // Handle cases with no output and no error
        if (!outputContent) {
            outputContent = "Execution finished successfully with no output.";
        }

        updateOutputArea(outputContent, hasError);

        // Update metrics display
        if (data.metrics) {
            updateMetrics(data.metrics);
        } else {
            clearMetrics("N/A"); // Clear if no metrics received
        }
    }

    function updateOutputArea(text, isError = false, isLoading = false) {
        if (!outputArea) return;
        outputArea.textContent = text; // Use textContent for pre to preserve whitespace/newlines
        outputArea.classList.toggle('error', isError && !isLoading); // Don't show error style while loading
        outputArea.classList.toggle('loading', isLoading);
    }

    function updateGeminiOutput(text, isError = false, isLoading = false) {
        if (!geminiOutputArea) return;
        geminiOutputArea.textContent = text;
        geminiOutputArea.classList.toggle('error', isError && !isLoading);
        geminiOutputArea.classList.toggle('loading', isLoading);
    }

    function updateMetrics(metrics) {
        const formatMetric = (value, unit = '') => (value !== undefined && value !== null && value !== 'N/A' && value !== -1) ? `${value}${unit}` : 'N/A';
        const updateSpan = (span, value, isLoading = false) => {
            if(span) {
                span.textContent = value;
                span.classList.toggle('loading', isLoading);
            }
        };

        updateSpan(metricRuntime, formatMetric(metrics?.runtime_ms, ' ms'));
        updateSpan(metricCpu, formatMetric(metrics?.cpu_used)); // CPU polling not implemented
        updateSpan(metricMem, formatMetric(metrics?.mem_used)); // Should be peak mem from runner
        updateSpan(metricTimeComp, formatMetric(metrics?.time_complexity)); // Placeholder
        updateSpan(metricSpaceComp, formatMetric(metrics?.space_complexity)); // Placeholder
    }

    function clearMetrics(message = 'N/A') {
        const isLoading = message === "Running...";
        const spans = [metricRuntime, metricCpu, metricMem, metricTimeComp, metricSpaceComp];
        spans.forEach(span => {
            if(span) {
                span.textContent = message;
                span.classList.toggle('loading', isLoading);
            }
        });
    }

    function showTemporaryMessage(message, type = "info") {
         // Basic alert for now. Consider replacing with a dedicated notification element.
         console.log(`[${type.toUpperCase()}] ${message}`); // Log it regardless
         alert(`[${type.toUpperCase()}] ${message}`);
    }

}); // End DOMContentLoaded