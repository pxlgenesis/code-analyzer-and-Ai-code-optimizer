import os
from dotenv import load_dotenv

# Ensure paths are absolute, relative to this config file's directory
basedir = os.path.abspath(os.path.dirname(__file__))
# Correct path assumes .env is in the parent directory of 'core' (project root)
project_root = os.path.abspath(os.path.join(basedir, '..'))
dotenv_path = os.path.join(project_root, '.env')

if os.path.exists(dotenv_path):
    print(f"Loading environment variables from: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)
else:
    # Fallback to checking CWD if not found relative to script
    dotenv_path_cwd = os.path.join(os.getcwd(), '.env')
    if os.path.exists(dotenv_path_cwd):
         print(f"Loading environment variables from current working directory: {dotenv_path_cwd}")
         load_dotenv(dotenv_path=dotenv_path_cwd)
    else:
        print(f"Warning: .env file not found at {dotenv_path} or in CWD.")


class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'a_default_secret_key_if_env_is_missing')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    DOCKER_PYTHON_IMAGE = os.getenv('DOCKER_PYTHON_IMAGE', "python:3.10-slim")
    DOCKER_CPP_IMAGE = os.getenv('DOCKER_CPP_IMAGE', "gcc:11")
    DOCKER_TIMEOUT_SECONDS = int(os.getenv('DOCKER_TIMEOUT_SECONDS', 10))
    DOCKER_MEM_LIMIT = os.getenv('DOCKER_MEM_LIMIT', "128m")
    DOCKER_CPUS = float(os.getenv('DOCKER_CPUS', 0.5))
    # Ensure TEMP_CODE_DIR is absolute path within the project structure
    TEMP_CODE_DIR = os.path.join(project_root, 'temp_code') # Relative to project root

    @staticmethod
    def validate():
        print("--- Configuration ---")
        print(f"FLASK_DEBUG: {Config.FLASK_DEBUG}")
        print(f"TEMP_CODE_DIR: {Config.TEMP_CODE_DIR}")
        print(f"DOCKER_PYTHON_IMAGE: {Config.DOCKER_PYTHON_IMAGE}")
        print(f"DOCKER_CPP_IMAGE: {Config.DOCKER_CPP_IMAGE}")
        if not Config.GEMINI_API_KEY:
            print("Warning: GEMINI_API_KEY is not set.")
        else:
            print("GEMINI_API_KEY: Set (length > 0)")
        if Config.SECRET_KEY == 'a_default_secret_key_if_env_is_missing':
             print("Warning: FLASK_SECRET_KEY is not set or using the default.")
        else:
             print("FLASK_SECRET_KEY: Set (length > 0)")
        print("---------------------")
        # Create temp dir if it doesn't exist during validation
        try:
            os.makedirs(Config.TEMP_CODE_DIR, exist_ok=True)
            print(f"Ensured temporary code directory exists: {Config.TEMP_CODE_DIR}")
        except OSError as e:
            print(f"Error creating temporary code directory {Config.TEMP_CODE_DIR}: {e}")
            raise # Reraise the error as this directory is critical