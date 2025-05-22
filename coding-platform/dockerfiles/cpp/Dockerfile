# coding-platform/dockerfiles/cpp/Dockerfile

# Use an official GCC image (choose a specific version for consistency)
FROM gcc:11.3

# Set the working directory
WORKDIR /app

# Create a non-root user and group
RUN groupadd --gid 1002 cppuser && \
    useradd --uid 1002 --gid 1002 --create-home --shell /bin/bash cppuser

# Create the app directory and set permissions BEFORE switching user
# This ensures the user can write the compiled output ('a.out') here
RUN mkdir -p /app && chown cppuser:cppuser /app

# Optional: Install common C++ libraries (e.g., Boost) if needed
# RUN apt-get update && apt-get install -y --no-install-recommends libboost-all-dev && rm -rf /var/lib/apt/lists/*

# Switch to the non-root user
USER cppuser

# No default CMD or ENTRYPOINT needed here.
# The runner.py script provides the compile and execution command.