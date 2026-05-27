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

# Bundle the Spotify/Tailscale auth patch script (see spotify-tailscale-auth.md).
# Placed outside volume-mount paths so it is always present after container start.
COPY fix_spotify_auth.py /opt/fix_spotify_auth.py