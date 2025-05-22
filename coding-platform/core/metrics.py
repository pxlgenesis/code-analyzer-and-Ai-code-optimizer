import docker
import threading
import time
import logging

logger = logging.getLogger(__name__)

# Note: Real-time stats polling is complex and not directly used by the current runner.
# The runner gets final stats after completion. This function is for demonstration.
def get_realtime_stats(container_id, stats_dict, stop_event, interval=1):
    client = None
    try:
        client = docker.from_env()
        container = client.containers.get(container_id)
        logger.info(f"[Metrics Thread {container_id[:8]}]: Starting stats collection.")

        max_mem = 0
        # More complex CPU calculation needed here comparing readings over time

        while not stop_event.is_set():
            try:
                stats = container.stats(stream=False) # Get a single snapshot

                # Memory Usage (Peak)
                mem_usage = stats.get('memory_stats', {}).get('usage', 0)
                if mem_usage > max_mem:
                    max_mem = mem_usage
                stats_dict['peak_memory_bytes'] = max_mem

            except docker.errors.NotFound:
                logger.info(f"[Metrics Thread {container_id[:8]}]: Container not found, stopping.")
                break
            except Exception as e:
                logger.error(f"[Metrics Thread {container_id[:8]}]: Error getting stats: {e}")
                # Consider breaking or continuing based on error type
            time.sleep(interval)
        logger.info(f"[Metrics Thread {container_id[:8]}]: Stopping stats collection.")
    except docker.errors.NotFound:
         logger.warning(f"[Metrics Thread {container_id[:8]}]: Container gone before stats started.")
    except Exception as e:
        logger.error(f"[Metrics Thread {container_id[:8]}]: Initial connection error: {e}")

def format_bytes(byte_val):
    # This function isn't currently used as runner formats directly
    if byte_val is None or not isinstance(byte_val, (int, float)) or byte_val < 0:
        return "N/A"
    if byte_val == 0:
        return "0 B"
    mib = byte_val / (1024 * 1024)
    return f"{mib:.2f} MiB"

def estimate_complexity(code: str, language: str):
    # Placeholder: True automatic complexity analysis is extremely difficult.
    return {"time": "N/A (Manual)", "space": "N/A (Manual)"}