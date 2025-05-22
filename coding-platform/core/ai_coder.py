import google.generativeai as genai
import os
import traceback
import logging

logger = logging.getLogger(__name__)

# Common safety settings
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Common generation config (optional)
GENERATION_CONFIG = genai.types.GenerationConfig(
    # temperature=0.7, # Example: Control randomness
    # max_output_tokens=1024, # Limit output length
)


def _call_gemini(prompt: str, api_key: str) -> str:
    """Internal function to handle the Gemini API call and error parsing."""
    try:
        genai.configure(api_key=api_key)
        # Use a capable model, e.g., 1.5 flash or pro
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            safety_settings=SAFETY_SETTINGS,
            generation_config=GENERATION_CONFIG
            )

        logger.info(f"Sending prompt to Gemini (first 80 chars): {prompt[:80]}...")
        response = model.generate_content(prompt)

        # Enhanced response checking
        if not response.candidates:
             block_reason = "Unknown reason"
             try:
                 if response.prompt_feedback and response.prompt_feedback.block_reason:
                     block_reason = response.prompt_feedback.block_reason.name
             except Exception: pass # Ignore errors checking block reason
             logger.warning(f"Gemini response blocked or empty. Reason: {block_reason}")
             return f"Error: Code generation failed. The response was blocked (Reason: {block_reason}). Please modify your prompt or code."

        # Extract text safely
        try:
            generated_text = response.text
            # Basic cleaning: remove markdown code fences if present
            if generated_text.strip().startswith("```") and generated_text.strip().endswith("```"):
                 lines = generated_text.strip().splitlines()
                 if len(lines) > 1:
                    # Check if first line is language hint (e.g., ```python)
                    if lines[0].strip() == f"```{lines[0].strip().split('```')[1]}":
                         generated_text = "\n".join(lines[1:-1])
                    else:
                          generated_text = "\n".join(lines[1:-1]) # Assume simple fences
                 else: # Only fences, return empty
                      generated_text = ""

            logger.info("Successfully received response from Gemini.")
            return generated_text.strip()

        except ValueError as ve: # Often indicates blocked content in response parts
            block_reason = "Content filtering or generation issue"
            try:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason = response.prompt_feedback.block_reason.name
            except Exception: pass
            logger.warning(f"ValueError extracting Gemini text. Block reason: {block_reason}. Full response parts likely blocked.")
            return f"Error: Failed to extract generated text. Response may have been blocked (Reason: {block_reason})."
        except Exception as text_extract_err:
             logger.error(f"Error extracting text from Gemini response: {text_extract_err}", exc_info=True)
             return f"Error: Could not process the response from the AI model. Details: {text_extract_err}"

    except Exception as e:
        logger.error(f"Gemini API Error: {e}", exc_info=True)
        error_message = f"Error: Failed to communicate with the AI model. Details: {type(e).__name__}"
        # More specific error messages
        err_str = str(e).lower()
        if "api key not valid" in err_str or "permission_denied" in err_str:
            error_message = "Error: Invalid or missing Gemini API Key configured on the server."
        elif "quota" in err_str or "resource_exhausted" in err_str:
             error_message = "Error: API quota exceeded for the AI model."
        elif "deadlineexceeded" in err_str:
             error_message = "Error: Request to AI model timed out."
        elif "invalid argument" in err_str:
             error_message = f"Error: Invalid argument sent to AI model (check prompt/config). Details: {e}"

        return error_message


def generate_via_gemini(prompt: str, language: str, api_key: str) -> str:
    """Generates code based on a natural language prompt."""
    if not api_key:
        logger.warning("generate_via_gemini called without API key.")
        return "Error: Gemini API key is not configured on the server."
    if not prompt:
        return "Error: Prompt cannot be empty."

    full_prompt = f"Generate a code snippet in {language.capitalize()} for the following task. Provide only the raw code, without any introduction, explanation, or markdown formatting unless the code itself requires comments.\n\nTask: {prompt}"

    return _call_gemini(full_prompt, api_key)


def optimize_via_gemini(code: str, language: str, api_key: str) -> str:
    """Attempts to optimize the given code using Gemini."""
    if not api_key:
        logger.warning("optimize_via_gemini called without API key.")
        return "Error: Gemini API key is not configured on the server."
    if not code:
        return "Error: Cannot optimize empty code."

    full_prompt = f"""Analyze the following {language.capitalize()} code and provide an optimized version. Focus on improving performance (speed) and potentially memory efficiency where applicable, without changing the core functionality or output for standard inputs.

Provide *only* the optimized code, without any introduction, explanation of changes, or markdown formatting. If the code is already reasonably optimized or cannot be significantly improved without changing functionality, return the original code.
{code}
"""
    return _call_gemini(full_prompt, api_key)