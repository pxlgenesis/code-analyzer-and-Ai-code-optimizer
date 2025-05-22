// coding-platform/static/js/editor.js

var editor = null; // Define editor globally but initialize as null

// --- Function to Initialize ACE ---
function initializeAceEditor() {
    console.log("[editor.js] Attempting to initialize ACE Editor...");
    const editorDiv = document.getElementById('editor');

    // 1. Check if the target div exists
    if (!editorDiv) {
        console.error("[editor.js] Error: Editor target element ('#editor') not found in the DOM!");
        // Optionally display an error message to the user on the page itself
        // document.body.insertAdjacentHTML('afterbegin', '<p style="color:red; background:yellow; padding: 10px;">Error: Code editor element not found!</p>');
        return; // Stop initialization
    }
     console.log("[editor.js] Found editor target element:", editorDiv);

    // 2. Check if the ACE library (ace object) is loaded
    if (typeof ace === 'undefined') {
        console.error("[editor.js] Error: ACE library (ace object) is not defined. Ensure ace.js is loaded before this script.");
        editorDiv.textContent = "Error: Code editor library (ace.js) failed to load. Check network connection or browser console.";
        editorDiv.style.color = 'red';
        editorDiv.style.whiteSpace = 'pre-wrap'; // Make error message readable
        return; // Stop initialization
    }
    console.log("[editor.js] ACE library seems loaded (ace object found).");

    // 3. Try to initialize the editor
    try {
        console.log("[editor.js] Calling ace.edit('editor')...");
        ace.require("ace/ext/language_tools"); // Enable autocompletion etc.
        editor = ace.edit(editorDiv); // Initialize editor on the div

        console.log("[editor.js] ace.edit() successful. Configuring editor...");

        // --- Editor Configuration ---
        editor.setTheme("ace/theme/chrome"); // Example: Light theme
        editor.session.setMode("ace/mode/python"); // Default mode
        editor.setShowPrintMargin(false);
        editor.session.setUseWrapMode(true);
        editor.session.setTabSize(4);
        editor.session.setUseSoftTabs(true);
        // Add options for better usability
        editor.setOptions({
            fontFamily: "Fira Code, Monaco, Menlo, Consolas, 'Courier New', monospace",
            fontSize: "14px",
            enableBasicAutocompletion: true,
            enableLiveAutocompletion: true,
            enableSnippets: true,
            highlightActiveLine: true,
            showGutter: true, // Show line numbers
            useWorker: true // Enable background syntax checking
        });

        // Set initial placeholder/content if editor is empty or has default text
        const initialContent = editorDiv.textContent.trim(); // Get content before ACE clears it
        if (initialContent === '// Start coding here...' || initialContent === '' || editor.getValue().trim() === '') {
             editor.setValue(`print("Hello, World!")\n`, -1); // Set default code, cursor to start
             console.log("[editor.js] Set default editor content.");
        } else {
             console.log("[editor.js] Editor already had content, preserving it.");
             // Ensure syntax highlighting is applied to existing content
             editor.session.setMode(editor.session.getMode());
        }

        // Make the editor focusable
        editor.renderer.getContainerElement().setAttribute('tabindex', 0);


        console.log("[editor.js] ACE Editor initialized and configured successfully.");

        // Optional: Alert main.js that the editor is ready (if needed beyond global var)
        // document.dispatchEvent(new CustomEvent('editorReady'));

    } catch (error) {
        console.error("[editor.js] Error during ace.edit() or configuration:", error);
        editorDiv.textContent = `Error initializing editor instance: ${error.message}. See browser console for details.`;
        editorDiv.style.color = 'red';
        editor = null; // Ensure editor variable is null if initialization failed
    }
}

// --- Initialization Trigger ---
// Use a reliable DOM ready event listener
// This ensures the HTML (including #editor div) is parsed before we try to find it
if (document.readyState === 'loading') {
    console.log("[editor.js] DOM not ready yet, adding DOMContentLoaded listener.");
    document.addEventListener('DOMContentLoaded', initializeAceEditor);
} else {
    // `DOMContentLoaded` has already fired, run immediately
    console.log("[editor.js] DOM already ready, running initialization directly.");
    initializeAceEditor();
}