import os
import uuid
import docker
import time
import threading
import traceback
import logging # Use Flask's logger if available, otherwise basic logger

logger = logging.getLogger(__name__)

def execute_code(code: str, language: str, config: object) -> dict:
    run_id = str(uuid.uuid4())
    logger.info(f"Starting execution run_id: {run_id} for language: {language}")
    result = {
        "output": "",
        "error": "",
        "metrics": {
            "runtime_ms": -1,
            "cpu_used": "N/A", # Requires complex polling not implemented here
            "mem_used": "N/A", # Peak memory from stats
            "time_complexity": "N/A",
            "space_complexity": "N/A"
        },
        "run_id": run_id
    }
    temp_dir = config.TEMP_CODE_DIR
    # No need for os.makedirs here if Config.validate() ensures it exists
    host_filepath = None
    container = None
    client = None

    try:
        # Define per-language settings
        if language == 'python':
            image_name = config.DOCKER_PYTHON_IMAGE
            filename = f"{run_id}_script.py"
            cmd = ["python", f"/app/{filename}"]
            mount_mode = 'ro'
        elif language == 'cpp':
            image_name = config.DOCKER_CPP_IMAGE
            filename = f"{run_id}_main.cpp"
            # Use -O2 optimization flag for C++ compilation
            cmd = ["sh", "-c", f"g++ /app/{filename} -std=c++17 -O2 -o /app/a.out && /app/a.out"]
            mount_mode = 'rw' # Need write access in /app for compilation output 'a.out'
        else:
            result["error"] = f"Unsupported language: {language}"
            logger.warning(f"Unsupported language request: {language} for run_id: {run_id}")
            return result

        host_filepath = os.path.join(temp_dir, filename)
        container_mount_path = "/app" # Hardcoded working dir inside container

        # Write code to temporary file
        try:
            with open(host_filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            logger.debug(f"Code written to temporary file: {host_filepath}")
        except IOError as e:
             result["error"] = f"Failed to write code to temporary file: {e}"
             logger.error(f"IOError writing {host_filepath}: {e}", exc_info=True)
             return result


        # Initialize Docker client
        try:
             client = docker.from_env(timeout=10) # Add timeout for client connection
             client.ping() # Verify connection
             logger.info("Docker client connected successfully.")
        except Exception as e:
             result["error"] = f"Failed to connect to Docker: {e}"
             logger.error(f"Docker connection error: {e}", exc_info=True)
             if host_filepath and os.path.exists(host_filepath): os.remove(host_filepath)
             return result


        # Check and pull image if necessary
        try:
            client.images.get(image_name)
            logger.debug(f"Docker image found locally: {image_name}")
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling Docker image: {image_name}")
            try:
                client.images.pull(image_name)
                logger.info(f"Successfully pulled image: {image_name}")
            except docker.errors.APIError as e:
                 result["error"] = f"Failed to pull Docker image '{image_name}': {e}"
                 logger.error(f"Error pulling image {image_name}: {e}", exc_info=True)
                 if host_filepath and os.path.exists(host_filepath): os.remove(host_filepath)
                 return result
        except Exception as e:
             result["error"] = f"Docker image check error for '{image_name}': {e}"
             logger.error(f"Error checking image {image_name}: {e}", exc_info=True)
             if host_filepath and os.path.exists(host_filepath): os.remove(host_filepath)
             return result

        # Define container configuration
        # Mount the single file for Python, or the whole dir for C++ to allow compilation output
        volumes_config = {}
        if language == 'python':
             volumes_config[host_filepath] = {'bind': f'{container_mount_path}/{filename}', 'mode': mount_mode}
        elif language == 'cpp':
             # Mount the directory containing the source file, allowing 'a.out' creation
             volumes_config[temp_dir] = {'bind': container_mount_path, 'mode': mount_mode}

        container_config = {
            "image": image_name,
            "command": cmd,
            "volumes": volumes_config,
            "working_dir": container_mount_path,
            "mem_limit": config.DOCKER_MEM_LIMIT,
            "memswap_limit": config.DOCKER_MEM_LIMIT, # Disables swap effectively
            "cpus": config.DOCKER_CPUS,
            "network_disabled": True,
            "log_config": {"type": "json-file", "config": {"max-size": "1m"}},
            "remove": False, # Remove manually after getting logs/stats
            "detach": True,
            "read_only": (language == 'python'), # Filesystem read-only for Python only
            "security_opt": ["no-new-privileges"],
            # Consider "user": "1001:1001" for python, "1002:1002" for cpp if UIDs match Dockerfile
        }

        # Run the container
        logger.info(f"Starting container for run_id: {run_id}")
        start_time = time.time()
        container = client.containers.run(**container_config)
        logger.debug(f"Container {container.short_id} started for run_id: {run_id}")


        # Wait for container completion and handle results/timeouts
        try:
            exit_info = container.wait(timeout=config.DOCKER_TIMEOUT_SECONDS)
            end_time = time.time()
            result["metrics"]["runtime_ms"] = round((end_time - start_time) * 1000)
            exit_code = exit_info.get("StatusCode", -1)
            logger.info(f"Container {container.short_id} finished. ExitCode: {exit_code}, Runtime: {result['metrics']['runtime_ms']}ms")

            # Retrieve logs (critical to do this *after* wait)
            stdout_logs = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace').strip()
            stderr_logs = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace').strip()

            result["output"] = stdout_logs
            result["error"] = stderr_logs

            if exit_code != 0:
                error_prefix = f"Execution failed with exit code {exit_code}."
                if result["error"]:
                    result["error"] = f"{error_prefix}\n{result['error']}"
                else:
                    result["error"] = error_prefix

                # Add specific error messages based on common exit codes
                if exit_code == 137: # Often OOM Killer or SIGKILL
                     if (end_time - start_time) >= config.DOCKER_TIMEOUT_SECONDS - 0.5: # Check if close to timeout
                          result["error"] += f" Process likely killed due to timeout ({config.DOCKER_TIMEOUT_SECONDS}s)."
                     else:
                          result["error"] += f" Process likely killed due to memory limit ({config.DOCKER_MEM_LIMIT})."
                elif exit_code == 139: # Segmentation Fault
                     result["error"] += " Process likely caused a Segmentation Fault."
                elif exit_code == 127: # Command not found
                     result["error"] += " Command not found within the container (check image/path)."


            # Attempt to get final stats for peak memory
            try:
                 stats = container.stats(stream=False)
                 mem_usage = stats.get('memory_stats', {}).get('max_usage') # Peak usage
                 if mem_usage is not None:
                      result["metrics"]["mem_used"] = f"{mem_usage / (1024*1024):.2f} MiB"
                 else:
                      # Fallback to final usage if max_usage not available
                      mem_usage = stats.get('memory_stats', {}).get('usage')
                      if mem_usage is not None:
                          result["metrics"]["mem_used"] = f"{mem_usage / (1024*1024):.2f} MiB (Final)"
                      else:
                           result["metrics"]["mem_used"] = "N/A"
                 logger.debug(f"Container {container.short_id} memory usage: {result['metrics']['mem_used']}")

            except Exception as stats_err:
                 logger.warning(f"Could not retrieve container stats for {container.short_id}: {stats_err}")
                 result["metrics"]["mem_used"] = "Error"


        except (docker.errors.ContainerError) as container_err:
             # Error during container execution reported by Docker daemon
             end_time = time.time()
             result["metrics"]["runtime_ms"] = round((end_time - start_time) * 1000)
             result["error"] = f"Container execution error: {str(container_err)}"
             logger.error(f"ContainerError for run_id {run_id}: {container_err}", exc_info=True)
             if container: # Try to get logs even if wait fails
                 try:
                     err_logs = container.logs(stderr=True, stdout=False).decode('utf-8', errors='replace').strip()
                     if err_logs: result["error"] += "\n--- Container Logs ---\n" + err_logs
                 except: pass # Ignore errors getting logs here

        except Exception as wait_err: # Catches timeout from container.wait() or other wait issues
             end_time = time.time()
             elapsed = end_time - start_time
             result["metrics"]["runtime_ms"] = round(elapsed * 1000)
             logger.warning(f"Exception during container wait for {container.short_id}: {wait_err}", exc_info=True)
             # Check if it was likely a timeout
             if elapsed >= config.DOCKER_TIMEOUT_SECONDS - 0.1: # Allow slight timing variation
                 result["error"] = f"Execution timed out after {config.DOCKER_TIMEOUT_SECONDS} seconds."
                 logger.warning(f"Execution timed out for run_id {run_id}")
                 if container:
                     try:
                         logger.info(f"Stopping timed-out container {container.short_id}")
                         container.stop(timeout=1)
                     except Exception as stop_err:
                         logger.error(f"Error stopping timed-out container {container.short_id}: {stop_err}")
             else:
                # Some other error during wait
                result["error"] = f"Error waiting for container results: {wait_err}"
                if container: # Try get logs
                     try:
                        err_logs = container.logs(stderr=True, stdout=False).decode('utf-8', errors='replace').strip()
                        if err_logs: result["error"] += "\n--- Container Logs ---\n" + err_logs
                     except: pass


    except docker.errors.APIError as e:
        result["error"] = f"Docker API error: {e}"
        logger.error(f"Docker API Error for run {run_id}: {e}", exc_info=True)
    except Exception as e:
        result["error"] = f"An unexpected error occurred during execution setup: {e}"
        logger.error(f"Unexpected Runner Error for run {run_id}: {e}", exc_info=True)

    finally:
        # --- Cleanup ---
        if container:
            try:
                container.remove(force=True)
                logger.debug(f"Container {container.short_id} removed for run_id: {run_id}")
            except docker.errors.NotFound:
                logger.debug(f"Container {container.short_id} already removed.")
            except Exception as final_remove_err:
                logger.warning(f"Warning: Error during final container removal {container.short_id}: {final_remove_err}")

        if host_filepath and os.path.exists(host_filepath):
            try:
                os.remove(host_filepath)
                logger.debug(f"Removed temporary source file: {host_filepath}")
                # Also remove compiled C++ executable if it exists
                if language == 'cpp':
                     cpp_executable_path = os.path.join(temp_dir, 'a.out')
                     if os.path.exists(cpp_executable_path):
                         os.remove(cpp_executable_path)
                         logger.debug(f"Removed temporary executable: {cpp_executable_path}")
            except OSError as e:
                logger.warning(f"Warning: Could not remove temporary file(s) for run_id {run_id}: {e}")

        logger.info(f"Finished execution run_id: {run_id}")

    return result