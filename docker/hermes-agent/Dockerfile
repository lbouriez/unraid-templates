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

# Override the upstream s6 dashboard run script to honour HERMES_DASHBOARD_INSECURE=1
# by passing --insecure to the hermes dashboard CLI. The upstream env-var was gutted
# in the June 2026 hardening but the CLI flag still works. The bundled auth-provider
# plugins (dashboard_auth/nous, dashboard_auth/basic) are not yet shipped in the
# upstream wheel, so this override is the only way to start the dashboard on a
# non-loopback bind until upstream fixes the missing plugins.
COPY dashboard-run /etc/s6-overlay/s6-rc.d/dashboard/run
RUN chmod 755 /etc/s6-overlay/s6-rc.d/dashboard/run

# Bundle the Spotify/Tailscale auth patch script (see spotify-tailscale-auth.md).
# Placed outside volume-mount paths so it is always present after container start.
COPY fix_spotify_auth.py /opt/fix_spotify_auth.py