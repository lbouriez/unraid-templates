# Extends the official Hermes Agent image with faster-whisper for local STT
FROM nousresearch/hermes-agent:latest

USER root

# Activate the hermes venv for all subsequent RUN steps, interactive shells,
# and docker exec sessions — no need to run `source .venv/bin/activate` manually.
ENV VIRTUAL_ENV=/opt/hermes/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install faster-whisper into the existing hermes venv.
# The base image uses uv (not plain pip) — we target the venv via VIRTUAL_ENV.
# nvidia-cudnn-cu12 and nvidia-cublas-cu12 provide GPU-accelerated inference
# on NVIDIA cards via CTranslate2 (no separate CUDA toolkit required on the host).
# Remove the nvidia-* packages if you only need CPU inference.
RUN uv pip install --no-cache-dir \
    faster-whisper \
    nvidia-cudnn-cu12 \
    nvidia-cublas-cu12 && \
    chown -R hermes:hermes /opt/hermes/.venv

COPY dashboard-run /etc/s6-overlay/s6-rc.d/dashboard/run
RUN chmod 755 /etc/s6-overlay/s6-rc.d/dashboard/run

# Bundle the Spotify/Tailscale auth patch script (see spotify-tailscale-auth.md).
# Placed outside volume-mount paths so it is always present after container start.
COPY fix_spotify_auth.py /opt/fix_spotify_auth.py

# Bundle the OpenMemory memory provider plugin.
# Allows Hermes to connect to the mem0-aio / OpenMemory server.
# Copied to /opt/hermes-builtin/ (NOT under /opt/hermes/ which is a Docker volume)
# because volumes shadow image files. An s6 oneshot service copies it into
# the volume at container startup.
COPY plugins/openmemory/ /opt/hermes-builtin/plugins/memory/openmemory/
RUN chown -R hermes:hermes /opt/hermes-builtin/plugins/memory/openmemory/ && \
    chmod -R 755 /opt/hermes-builtin/plugins/memory/openmemory/

# S6 oneshot: copies bundled plugins into the volume-mounted /opt/hermes/plugins/ at startup.
COPY s6-rc.d/copy-openmemory-plugins/ /etc/s6-overlay/s6-rc.d/copy-openmemory-plugins/
RUN chmod -R 755 /etc/s6-overlay/s6-rc.d/copy-openmemory-plugins/ && \
    chmod 644 /etc/s6-overlay/s6-rc.d/copy-openmemory-plugins/type

# Register as a dependency of main-hermes so it runs before Hermes starts
RUN mkdir -p /etc/s6-overlay/s6-rc.d/main-hermes/dependencies.d && \
    ln -sf /etc/s6-overlay/s6-rc.d/copy-openmemory-plugins /etc/s6-overlay/s6-rc.d/main-hermes/dependencies.d/copy-openmemory-plugins && \
    chmod 755 /etc/s6-overlay/s6-rc.d/main-hermes/dependencies.d/copy-openmemory-plugins
