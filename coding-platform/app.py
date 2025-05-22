import os
import logging
from flask import Flask, render_template, request, jsonify
from config import Config

# Import core modules AFTER config validation potentially happens
from core import runner, ai_coder # Assuming runner and ai_coder exist now

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

app = Flask(__name__)
app.config.from_object(Config)

# Validate config on startup and ensure temp dir exists
try:
    Config.validate()
except Exception as e:
     app.logger.error(f"Configuration error: {e}")
     # Optionally exit if config is invalid
     # exit(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run', methods=['POST'])
def run_code_route():
    try:
        data = request.get_json()
        if not data:
            app.logger.warning("Received empty/invalid JSON payload in /run")
            return jsonify({'error': 'Invalid JSON payload'}), 400

        code = data.get('code', '')
        language = data.get('language', 'python')

        if not code:
            return jsonify({'error': 'No code provided'}), 400
        if language not in ['python', 'cpp']:
            return jsonify({'error': 'Unsupported language'}), 400

        app.logger.info(f"Received request to run {language} (code length: {len(code)})")
        result = runner.execute_code(code, language, app.config)
        app.logger.info(f"Execution result for run_id {result.get('run_id')}: Status {'OK' if not result.get('error') else 'ERROR'}, Runtime: {result.get('metrics',{}).get('runtime_ms')}ms")

        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Error in /run endpoint: {e}", exc_info=True) # Log full traceback
        return jsonify({'error': 'An internal server error occurred during execution.'}), 500

@app.route('/generate', methods=['POST'])
def generate_code_route():
    try:
        data = request.get_json()
        if not data:
            app.logger.warning("Received empty/invalid JSON payload in /generate")
            return jsonify({'error': 'Invalid JSON payload'}), 400

        prompt = data.get('prompt', '')
        language = data.get('language', 'python') # Context for Gemini

        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400

        if not app.config['GEMINI_API_KEY']:
             app.logger.warning("Attempted /generate without GEMINI_API_KEY set.")
             return jsonify({'error': 'AI code generation is not configured on the server.'}), 501

        app.logger.info(f"Received request to generate code for prompt: {prompt[:50]}...")
        generated_code = ai_coder.generate_via_gemini(prompt, language, app.config['GEMINI_API_KEY'])
        app.logger.info(f"AI generation completed (output length: {len(generated_code)})")

        return jsonify({'generated_code': generated_code})

    except Exception as e:
        app.logger.error(f"Error in /generate endpoint: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred during AI generation.'}), 500

# --- New Route for Optimization ---
@app.route('/optimize', methods=['POST'])
def optimize_code_route():
    try:
        data = request.get_json()
        if not data:
            app.logger.warning("Received empty/invalid JSON payload in /optimize")
            return jsonify({'error': 'Invalid JSON payload'}), 400

        code = data.get('code', '')
        language = data.get('language', 'python')

        if not code:
            return jsonify({'error': 'No code provided for optimization'}), 400
        if language not in ['python', 'cpp']:
            return jsonify({'error': 'Unsupported language for optimization'}), 400

        if not app.config['GEMINI_API_KEY']:
             app.logger.warning("Attempted /optimize without GEMINI_API_KEY set.")
             return jsonify({'error': 'AI code optimization is not configured on the server.'}), 501

        app.logger.info(f"Received request to optimize {language} code (length: {len(code)})")
        optimized_code = ai_coder.optimize_via_gemini(code, language, app.config['GEMINI_API_KEY'])
        app.logger.info(f"AI optimization completed (output length: {len(optimized_code)})")

        # Check if optimization failed or returned an error message
        if optimized_code.startswith("Error:"):
             return jsonify({'error': optimized_code}), 500 # Return AI's error message

        return jsonify({'optimized_code': optimized_code})

    except Exception as e:
        app.logger.error(f"Error in /optimize endpoint: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred during AI optimization.'}), 500


if __name__ == '__main__':
    debug_mode = app.config['FLASK_DEBUG']
    app.logger.info(f"Starting Flask server (Debug mode: {debug_mode})...")
    # Use 0.0.0.0 to be accessible on network, change if needed
    # Use port 5000 by default, ensure it's not blocked
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)