# coding-platform/dockerfiles/python/Dockerfile

# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Create a non-root user and group
RUN groupadd --gid 1001 pythonuser && \
    useradd --uid 1001 --gid 1001 --create-home --shell /bin/bash pythonuser

# Optional: Install common libraries if needed for most user code
# RUN pip install --no-cache-dir numpy pandas requests

# Switch to the non-root user
USER pythonuser

# Default command (can be overridden by docker run command)
# We don't set a default CMD or ENTRYPOINT here because
# the runner.py will specify the command (e.g., "python /app/script.py")
# CMD ["python"]